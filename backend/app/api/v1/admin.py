"""用户管理 API 路由（管理员）."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import BusinessError
from app.core.security import hash_password
from app.api.deps import get_current_user, require_roles
from app.models.user import User, Role, Permission
from app.schemas.user import (
    AssignRolesRequest,
    PermissionResponse,
    ResetPasswordRequest,
    RoleCreate,
    RoleDetailResponse,
    RolePermissionUpdate,
    RoleResponse,
    RoleUpdate,
    UserCreate,
    UserListResponse,
    UserUpdate,
)

router = APIRouter(prefix="/admin", tags=["管理"])

RESTRICTED_PERMISSION_ROLE_NAMES = {"validation_admin"}
RESTRICTED_DELETE_ROLE_NAMES = {"validation_admin"}


async def _resolve_requested_roles(
    db: AsyncSession, role_codes: list[str]
) -> list[Role]:
    """解析请求中的角色编码，仅以 roles 表为系统角色来源。"""
    requested_codes = list(dict.fromkeys(role_codes))
    if not requested_codes:
        return []

    result = await db.execute(select(Role).where(Role.name.in_(requested_codes)))
    roles_by_name = {role.name: role for role in result.scalars().all()}
    missing_codes = [code for code in requested_codes if code not in roles_by_name]
    if missing_codes:
        raise BusinessError(
            f"角色不存在: {', '.join(missing_codes)}",
            status_code=400,
        )

    return [roles_by_name[code] for code in requested_codes]


async def _get_permissions_by_ids(
    db: AsyncSession,
    permission_ids: list[str],
) -> list[Permission]:
    """按 ID 获取权限并校验完整性。"""
    requested_ids = list(dict.fromkeys(permission_ids))
    if not requested_ids:
        return []

    result = await db.execute(
        select(Permission).where(Permission.id.in_(requested_ids))
    )
    permissions = list(result.scalars().all())
    permissions_by_id = {permission.id: permission for permission in permissions}

    unresolved_ids = [
        permission_id
        for permission_id in requested_ids
        if permission_id not in permissions_by_id
    ]
    if unresolved_ids:
        raise BusinessError(
            f"权限不存在: {', '.join(unresolved_ids)}",
            status_code=400,
        )

    return [permissions_by_id[permission_id] for permission_id in requested_ids]


async def _get_role_detail_or_404(db: AsyncSession, role_id: str) -> Role:
    """获取带权限关系的角色详情。"""
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise BusinessError("角色不存在", status_code=404)
    return role


# ========== 用户管理 ==========


@router.get("/users", response_model=list[UserListResponse])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_roles("admin", "validation_admin")),
):
    """获取用户列表."""
    offset = (page - 1) * page_size
    result = await db.execute(
        select(User).offset(offset).limit(page_size).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        UserListResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            full_name=u.full_name,
            is_active=u.is_active,
            is_locked=u.is_locked,
            roles=[RoleResponse.model_validate(r) for r in u.roles],
        )
        for u in users
    ]


@router.post("/users", response_model=UserListResponse)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_roles("admin")),
):
    """管理员创建用户."""
    # 检查用户名
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise BusinessError("用户名已存在")

    # 检查邮箱
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise BusinessError("邮箱已被注册")

    user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
    )

    # 分配角色（通过 code/name 查找）
    if data.role_codes:
        user.roles = await _resolve_requested_roles(db, data.role_codes)

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserListResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_locked=user.is_locked,
        roles=[RoleResponse.model_validate(r) for r in user.roles],
    )


@router.put("/users/{user_id}", response_model=UserListResponse)
async def update_user(
    user_id: str,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_roles("admin")),
):
    """更新用户信息."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise BusinessError("用户不存在", status_code=404)

    # 自保护：不允许禁用自己
    if data.is_active is False and user_id == current_user.id:
        raise BusinessError("不能禁用自己的账户")

    if data.email is not None:
        user.email = data.email
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.is_active is not None:
        user.is_active = data.is_active

    await db.commit()
    await db.refresh(user)

    return UserListResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_locked=user.is_locked,
        roles=[RoleResponse.model_validate(r) for r in user.roles],
    )


@router.post("/users/{user_id}/roles")
async def assign_roles(
    user_id: str,
    data: AssignRolesRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_roles("admin")),
):
    """为用户分配角色."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise BusinessError("用户不存在", status_code=404)

    user.roles = await _resolve_requested_roles(db, data.role_codes)

    await db.commit()
    return {"message": "角色分配成功"}


@router.post("/users/{user_id}/unlock")
async def unlock_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_roles("admin")),
):
    """解锁用户账户."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise BusinessError("用户不存在", status_code=404)

    user.is_locked = False
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()
    return {"message": "用户已解锁"}


@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: str,
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_roles("admin")),
):
    """管理员重置用户密码."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise BusinessError("用户不存在", status_code=404)

    user.password_hash = hash_password(data.new_password)
    await db.commit()
    return {"message": "密码已重置"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_roles("admin")),
):
    """删除用户."""
    if user_id == current_user.id:
        raise BusinessError("不能删除自己的账户")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise BusinessError("用户不存在", status_code=404)

    await db.delete(user)
    await db.commit()
    return {"message": "用户已删除"}


# ========== 角色管理 ==========


@router.get("/roles", response_model=list[RoleDetailResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_roles("admin", "validation_admin")),
):
    """获取角色列表."""
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).order_by(Role.name)
    )
    return result.scalars().all()


@router.post("/roles", response_model=RoleDetailResponse)
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_roles("admin")),
):
    """创建角色."""
    result = await db.execute(select(Role).where(Role.name == data.name))
    if result.scalar_one_or_none():
        raise BusinessError("角色名已存在")

    role = Role(
        name=data.name,
        display_name=data.display_name,
        description=data.description,
    )

    if data.permission_ids:
        role.permissions = await _get_permissions_by_ids(db, data.permission_ids)

    db.add(role)
    await db.commit()
    return await _get_role_detail_or_404(db, role.id)


@router.patch("/roles/{role_id}", response_model=RoleDetailResponse)
async def update_role(
    role_id: str,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_roles("admin", "validation_admin")),
):
    """更新角色展示信息。"""
    role = await _get_role_detail_or_404(db, role_id)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(role, key, value)

    await db.commit()
    return await _get_role_detail_or_404(db, role_id)


@router.put("/roles/{role_id}/permissions", response_model=RoleDetailResponse)
async def update_role_permissions(
    role_id: str,
    data: RolePermissionUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_roles("admin")),
):
    """更新角色权限分配。"""
    role = await _get_role_detail_or_404(db, role_id)
    if role.name in RESTRICTED_PERMISSION_ROLE_NAMES:
        raise BusinessError("该内置角色不允许修改权限", status_code=403)

    role.permissions = await _get_permissions_by_ids(db, data.permission_ids)
    await db.commit()
    return await _get_role_detail_or_404(db, role_id)


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_roles("admin")),
):
    """删除角色。"""
    role = await _get_role_detail_or_404(db, role_id)
    if role.name in RESTRICTED_DELETE_ROLE_NAMES:
        raise BusinessError("该内置角色不允许删除", status_code=403)

    await db.delete(role)
    await db.commit()
    return {"message": "角色已删除"}


# ========== 权限管理 ==========


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_roles("admin")),
):
    """获取权限列表."""
    result = await db.execute(select(Permission).order_by(Permission.resource_type))
    return result.scalars().all()

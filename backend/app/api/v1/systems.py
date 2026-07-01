"""被验证系统管理 API 路由."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BusinessError
from app.api.deps import get_current_user, require_roles
from app.models.user import User
from app.models.system import System
from app.models.project import Project
from app.schemas.system import (
    SystemCreate,
    SystemListResponse,
    SystemResponse,
    SystemUpdate,
)

router = APIRouter(prefix="/systems", tags=["系统管理"])


def _system_response(system: System) -> dict:
    """构建系统响应字典."""
    return {
        "id": system.id,
        "code": system.code,
        "name": system.name,
        "vendor": system.vendor,
        "version": system.version,
        "description": system.description,
        "gxp_category": system.gxp_category,
        "gamp5_category": system.gamp5_category,
        "owner_id": system.owner_id,
        "owner_name": system.owner.full_name if system.owner else None,
        "is_active": system.is_active,
        "created_at": system.created_at,
        "updated_at": system.updated_at,
    }


@router.get("", response_model=SystemListResponse)
async def list_systems(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", description="按名称或编号搜索"),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取系统列表（分页 + 搜索）."""
    stmt = select(System)
    count_stmt = select(func.count(System.id))

    if active_only:
        stmt = stmt.where(System.is_active == True)  # noqa: E712
        count_stmt = count_stmt.where(System.is_active == True)  # noqa: E712

    if search:
        like = f"%{search}%"
        condition = System.name.ilike(like) | System.code.ilike(like)
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(System.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    systems = list(result.scalars().all())

    return {
        "items": [_system_response(s) for s in systems],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{system_id}", response_model=SystemResponse)
async def get_system(
    system_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取系统详情."""
    result = await db.execute(select(System).where(System.id == system_id))
    system = result.scalar_one_or_none()
    if not system:
        raise BusinessError("系统不存在")
    return _system_response(system)


@router.post("", response_model=SystemResponse)
async def create_system(
    data: SystemCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    """创建被验证系统."""
    existing = await db.execute(select(System).where(System.code == data.code))
    if existing.scalar_one_or_none():
        raise BusinessError("系统编号已存在")

    system = System(**data.model_dump())
    db.add(system)
    await db.commit()
    await db.refresh(system)
    return _system_response(system)


@router.patch("/{system_id}", response_model=SystemResponse)
async def update_system(
    system_id: str,
    data: SystemUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    """更新被验证系统."""
    result = await db.execute(select(System).where(System.id == system_id))
    system = result.scalar_one_or_none()
    if not system:
        raise BusinessError("系统不存在")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(system, key, value)
    await db.commit()
    await db.refresh(system)
    return _system_response(system)


@router.delete("/{system_id}")
async def delete_system(
    system_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    """删除被验证系统（有关联项目时禁止）."""
    result = await db.execute(select(System).where(System.id == system_id))
    system = result.scalar_one_or_none()
    if not system:
        raise BusinessError("系统不存在")

    # 检查是否有项目关联
    project_count = (
        await db.execute(
            select(func.count(Project.id)).where(Project.system_id == system_id)
        )
    ).scalar() or 0
    if project_count > 0:
        raise BusinessError(f"该系统关联了 {project_count} 个验证项目，无法删除")

    await db.delete(system)
    await db.commit()
    return {"detail": "已删除"}

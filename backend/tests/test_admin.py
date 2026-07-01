"""管理员用户管理 API 测试."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.dictionary import DictCategory, DictItem
from app.models.user import User, Role, Permission
from app.core.security import hash_password


async def _create_admin(db: AsyncSession) -> tuple[str, str]:
    """创建管理员用户并返回 (user_id, token)."""
    role_result = await db.execute(select(Role).where(Role.name == "admin"))
    role = role_result.scalar_one_or_none()
    if role is None:
        role = Role(name="admin", display_name="管理员")
        db.add(role)
        await db.flush()

    user = User(
        username="admin",
        email="admin@example.com",
        full_name="Admin",
        password_hash=hash_password("Admin@1234"),
    )
    user.roles = [role]
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user.id, None  # token will be obtained via login


async def _login(client: AsyncClient, username: str, password: str) -> str:
    """登录并返回 access_token."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _setup_admin(client: AsyncClient, db: AsyncSession) -> str:
    """创建管理员并登录，返回 token."""
    await _create_admin(db)
    return await _login(client, "admin", "Admin@1234")


async def _create_validation_admin(db: AsyncSession) -> None:
    """创建验证管理员用户。"""
    role_result = await db.execute(
        select(Role).where(Role.name == "validation_admin")
    )
    role = role_result.scalar_one_or_none()
    if role is None:
        role = Role(name="validation_admin", display_name="验证管理员")
        db.add(role)
        await db.flush()

    user = User(
        username="validation-admin",
        email="validation-admin@example.com",
        full_name="Validation Admin",
        password_hash=hash_password("Admin@1234"),
    )
    user.roles = [role]
    db.add(user)
    await db.commit()


async def _create_normal_user(client: AsyncClient, token: str, username: str = "normaluser") -> str:
    """通过 API 创建普通用户，返回用户 ID."""
    resp = await client.post(
        "/api/v1/admin/users",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "full_name": f"{username} Full",
            "password": "User@1234",
            "role_codes": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _seed_system_role_dict(db: AsyncSession) -> None:
    """写入系统角色字典，模拟前端角色下拉来源。"""
    category = DictCategory(
        code="system_role",
        name="系统角色",
        description="系统级别的用户角色",
        is_system=True,
    )
    db.add(category)
    await db.flush()

    db.add_all(
        [
            DictItem(
                category_id=category.id,
                code="admin",
                label="系统管理员",
                sort_order=1,
            ),
            DictItem(
                category_id=category.id,
                code="validation_admin",
                label="验证管理员",
                sort_order=2,
            ),
            DictItem(
                category_id=category.id,
                code="user",
                label="普通用户",
                sort_order=3,
            ),
        ]
    )
    await db.commit()


async def _seed_roles_table(db: AsyncSession) -> None:
    """写入系统角色实体，作为系统角色唯一来源。"""
    existing = await db.execute(select(Role).where(Role.name.in_(["admin", "validation_admin", "user"])))
    existing_names = {role.name for role in existing.scalars().all()}

    role_rows = []
    if "admin" not in existing_names:
        role_rows.append(Role(name="admin", display_name="系统管理员", is_system=True))
    if "validation_admin" not in existing_names:
        role_rows.append(Role(name="validation_admin", display_name="验证管理员", is_system=True))
    if "user" not in existing_names:
        role_rows.append(Role(name="user", display_name="普通用户", is_system=True))

    if role_rows:
        db.add_all(role_rows)
        await db.commit()


# ========== 重置密码 ==========


@pytest.mark.asyncio
async def test_create_user_with_system_role_visible_in_user_list(
    client: AsyncClient, db_session: AsyncSession
):
    """创建用户时选择系统角色后，列表应返回可显示的角色信息。"""
    await _seed_system_role_dict(db_session)
    await _seed_roles_table(db_session)
    token = await _setup_admin(client, db_session)

    resp = await client.post(
        "/api/v1/admin/users",
        json={
            "username": "validator",
            "email": "validator@example.com",
            "full_name": "Validator",
            "password": "User@1234",
            "role_codes": ["validation_admin"],
        },
        headers=_auth_header(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["roles"] == [
        {
            "id": resp.json()["roles"][0]["id"],
            "name": "validation_admin",
            "display_name": "验证管理员",
            "description": None,
        }
    ]

    role_result = await db_session.execute(
        select(Role).where(Role.name == "validation_admin")
    )
    role = role_result.scalar_one_or_none()
    assert role is not None
    assert role.display_name == "验证管理员"

    list_resp = await client.get(
        "/api/v1/admin/users",
        headers=_auth_header(token),
    )
    assert list_resp.status_code == 200, list_resp.text
    created_user = next(
        user for user in list_resp.json() if user["username"] == "validator"
    )
    assert created_user["roles"] == [
        {
            "id": role.id,
            "name": "validation_admin",
            "display_name": "验证管理员",
            "description": None,
        }
    ]


@pytest.mark.asyncio
async def test_assign_roles_with_system_role_visible_in_user_list(
    client: AsyncClient, db_session: AsyncSession
):
    """分配系统角色后，用户列表应返回对应角色显示名。"""
    await _seed_system_role_dict(db_session)
    await _seed_roles_table(db_session)
    token = await _setup_admin(client, db_session)
    user_id = await _create_normal_user(client, token, username="assigned-user")

    resp = await client.post(
        f"/api/v1/admin/users/{user_id}/roles",
        json={"role_codes": ["user"]},
        headers=_auth_header(token),
    )
    assert resp.status_code == 200, resp.text

    role_result = await db_session.execute(select(Role).where(Role.name == "user"))
    role = role_result.scalar_one_or_none()
    assert role is not None
    assert role.display_name == "普通用户"

    list_resp = await client.get(
        "/api/v1/admin/users",
        headers=_auth_header(token),
    )
    assert list_resp.status_code == 200, list_resp.text
    assigned_user = next(
        user for user in list_resp.json() if user["id"] == user_id
    )
    assert assigned_user["roles"] == [
        {
            "id": role.id,
            "name": "user",
            "display_name": "普通用户",
            "description": None,
        }
    ]


@pytest.mark.asyncio
async def test_seed_rbac_creates_permissions_and_assigns_default_system_roles(
    db_session: AsyncSession,
):
    """RBAC 种子应创建权限目录，并为内置系统角色分配默认权限。"""
    from app.scripts.seed_rbac import seed_rbac

    db_session.add_all(
        [
            Role(name="admin", display_name="系统管理员", is_system=True),
            Role(
                name="validation_admin",
                display_name="验证管理员",
                is_system=True,
            ),
            Role(name="user", display_name="普通用户", is_system=True),
        ]
    )
    await db_session.commit()

    await seed_rbac(db_session)

    permission_result = await db_session.execute(
        select(Permission).where(
            Permission.code.in_(
                [
                    "system.admin.users.menu",
                    "system.admin.users.view",
                    "system.admin.users.manage",
                    "system.admin.dict.menu",
                    "project.documents.menu",
                    "project.members.manage",
                ]
            )
        )
    )
    seeded_permissions = {perm.code for perm in permission_result.scalars().all()}
    assert seeded_permissions == {
        "system.admin.users.menu",
        "system.admin.users.view",
        "system.admin.users.manage",
        "system.admin.dict.menu",
        "project.documents.menu",
        "project.members.manage",
    }

    role_result = await db_session.execute(
        select(Role).where(Role.name.in_(["admin", "validation_admin", "user"]))
    )
    roles_by_name = {role.name: role for role in role_result.scalars().all()}

    assert "system.admin.users.manage" in {
        permission.code for permission in roles_by_name["admin"].permissions
    }
    assert "system.admin.users.manage" not in {
        permission.code for permission in roles_by_name["validation_admin"].permissions
    }
    assert {permission.code for permission in roles_by_name["user"].permissions} == set()


@pytest.mark.asyncio
async def test_create_user_rejects_role_missing_from_roles_table_even_if_dict_exists(
    client: AsyncClient, db_session: AsyncSession
):
    """系统角色若只存在字典、不存在 roles 表，则创建用户时应被拒绝。"""
    await _seed_system_role_dict(db_session)
    token = await _setup_admin(client, db_session)

    resp = await client.post(
        "/api/v1/admin/users",
        json={
            "username": "dict-only-role-user",
            "email": "dict-only-role-user@example.com",
            "full_name": "Dict Only Role User",
            "password": "User@1234",
            "role_codes": ["validation_admin"],
        },
        headers=_auth_header(token),
    )
    assert resp.status_code == 400, resp.text
    assert "角色不存在" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_assign_roles_rejects_role_missing_from_roles_table_even_if_dict_exists(
    client: AsyncClient, db_session: AsyncSession
):
    """系统角色若只存在字典、不存在 roles 表，则分配角色时应被拒绝。"""
    await _seed_system_role_dict(db_session)
    token = await _setup_admin(client, db_session)
    user_id = await _create_normal_user(client, token, username="dict-only-assign-user")

    resp = await client.post(
        f"/api/v1/admin/users/{user_id}/roles",
        json={"role_codes": ["validation_admin"]},
        headers=_auth_header(token),
    )
    assert resp.status_code == 400, resp.text
    assert "角色不存在" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_reset_password_success(client: AsyncClient, db_session: AsyncSession):
    """管理员可以重置其他用户密码."""
    token = await _setup_admin(client, db_session)
    user_id = await _create_normal_user(client, token)

    resp = await client.post(
        f"/api/v1/admin/users/{user_id}/reset-password",
        json={"new_password": "NewPass@999"},
        headers=_auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "密码已重置"

    # 验证新密码可以登录
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "normaluser", "password": "NewPass@999"},
    )
    assert login_resp.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_user_not_found(client: AsyncClient, db_session: AsyncSession):
    """重置不存在用户的密码返回 404."""
    token = await _setup_admin(client, db_session)

    resp = await client.post(
        "/api/v1/admin/users/nonexistent-id/reset-password",
        json={"new_password": "NewPass@999"},
        headers=_auth_header(token),
    )
    assert resp.status_code == 404


# ========== 删除用户 ==========


@pytest.mark.asyncio
async def test_delete_user_success(client: AsyncClient, db_session: AsyncSession):
    """管理员可以删除其他用户."""
    token = await _setup_admin(client, db_session)
    user_id = await _create_normal_user(client, token)

    resp = await client.delete(
        f"/api/v1/admin/users/{user_id}",
        headers=_auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "用户已删除"

    # 验证用户已不存在
    list_resp = await client.get(
        "/api/v1/admin/users",
        headers=_auth_header(token),
    )
    user_ids = [u["id"] for u in list_resp.json()]
    assert user_id not in user_ids


@pytest.mark.asyncio
async def test_delete_self_forbidden(client: AsyncClient, db_session: AsyncSession):
    """管理员不能删除自己."""
    admin_id, _ = await _create_admin(db_session)
    token = await _login(client, "admin", "Admin@1234")

    resp = await client.delete(
        f"/api/v1/admin/users/{admin_id}",
        headers=_auth_header(token),
    )
    assert resp.status_code == 400
    assert "不能删除自己" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_delete_user_not_found(client: AsyncClient, db_session: AsyncSession):
    """删除不存在的用户返回 404."""
    token = await _setup_admin(client, db_session)

    resp = await client.delete(
        "/api/v1/admin/users/nonexistent-id",
        headers=_auth_header(token),
    )
    assert resp.status_code == 404


# ========== 自保护：禁用自己 ==========


@pytest.mark.asyncio
async def test_disable_self_forbidden(client: AsyncClient, db_session: AsyncSession):
    """管理员不能禁用自己."""
    admin_id, _ = await _create_admin(db_session)
    token = await _login(client, "admin", "Admin@1234")

    resp = await client.put(
        f"/api/v1/admin/users/{admin_id}",
        json={"is_active": False},
        headers=_auth_header(token),
    )
    assert resp.status_code == 400
    assert "不能禁用自己" in resp.json()["detail"]


# ========== 角色管理 ===========


@pytest.mark.asyncio
async def test_admin_can_update_role_permissions_and_delete_custom_role(
    client: AsyncClient, db_session: AsyncSession
):
    """admin 可以更新角色展示信息、分配权限并删除普通角色。"""
    from app.scripts.seed_rbac import seed_rbac

    token = await _setup_admin(client, db_session)
    await seed_rbac(db_session)

    permission_resp = await client.get(
        "/api/v1/admin/permissions",
        headers=_auth_header(token),
    )
    assert permission_resp.status_code == 200, permission_resp.text
    permission_ids = {
        permission["code"]: permission["id"]
        for permission in permission_resp.json()
    }

    create_resp = await client.post(
        "/api/v1/admin/roles",
        json={
            "name": "document_controller",
            "display_name": "文档管理员",
            "description": "负责文档配置",
            "permission_ids": [],
        },
        headers=_auth_header(token),
    )
    assert create_resp.status_code == 200, create_resp.text
    role_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/admin/roles/{role_id}",
        json={"display_name": "文档控制员", "description": "更新后的说明"},
        headers=_auth_header(token),
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["display_name"] == "文档控制员"
    assert update_resp.json()["description"] == "更新后的说明"

    assign_resp = await client.put(
        f"/api/v1/admin/roles/{role_id}/permissions",
        json={
            "permission_ids": [
                permission_ids["system.admin.users.view"],
                permission_ids["system.admin.dict.view"],
            ]
        },
        headers=_auth_header(token),
    )
    assert assign_resp.status_code == 200, assign_resp.text
    assert {permission["code"] for permission in assign_resp.json()["permissions"]} == {
        "system.admin.users.view",
        "system.admin.dict.view",
    }

    delete_resp = await client.delete(
        f"/api/v1/admin/roles/{role_id}",
        headers=_auth_header(token),
    )
    assert delete_resp.status_code == 200, delete_resp.text


@pytest.mark.asyncio
async def test_validation_admin_can_only_edit_role_metadata(
    client: AsyncClient, db_session: AsyncSession
):
    """validation_admin 只能编辑角色展示信息，不能分配权限或删除角色。"""
    from app.scripts.seed_rbac import seed_rbac

    await _create_validation_admin(db_session)
    await seed_rbac(db_session)
    token = await _login(client, "validation-admin", "Admin@1234")

    role_result = await db_session.execute(
        select(Role).where(Role.name == "validation_admin")
    )
    validation_role = role_result.scalar_one()

    update_resp = await client.patch(
        f"/api/v1/admin/roles/{validation_role.id}",
        json={"display_name": "验证管理员-已更新", "description": "允许修改展示信息"},
        headers=_auth_header(token),
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["display_name"] == "验证管理员-已更新"

    permission_resp = await client.get(
        "/api/v1/admin/permissions",
        headers={"Authorization": "Bearer invalid"},
    )
    assert permission_resp.status_code in {401, 403}

    list_permission_resp = await client.get(
        "/api/v1/admin/permissions",
        headers=_auth_header(token),
    )
    assert list_permission_resp.status_code == 403

    permission_id = None
    admin_token = await _setup_admin(client, db_session)
    admin_permission_resp = await client.get(
        "/api/v1/admin/permissions",
        headers=_auth_header(admin_token),
    )
    assert admin_permission_resp.status_code == 200, admin_permission_resp.text
    permission_id = next(
        permission["id"]
        for permission in admin_permission_resp.json()
        if permission["code"] == "system.admin.users.manage"
    )

    assign_resp = await client.put(
        f"/api/v1/admin/roles/{validation_role.id}/permissions",
        json={"permission_ids": [permission_id]},
        headers=_auth_header(token),
    )
    assert assign_resp.status_code == 403

    delete_resp = await client.delete(
        f"/api/v1/admin/roles/{validation_role.id}",
        headers=_auth_header(token),
    )
    assert delete_resp.status_code == 403

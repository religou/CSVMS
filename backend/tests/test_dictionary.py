"""字典管理 API 测试."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import Role, User
from app.core.security import hash_password


async def _create_admin(db: AsyncSession) -> None:
    """创建管理员用户用于字典管理测试."""
    role = Role(name="admin", display_name="管理员")
    db.add(role)
    await db.flush()

    user = User(
        username="dict-admin",
        email="dict-admin@example.com",
        full_name="Dict Admin",
        password_hash=hash_password("Admin@1234"),
    )
    user.roles = [role]
    db.add(user)
    await db.commit()


async def _login(client: AsyncClient, username: str, password: str) -> str:
    """登录并返回 access token."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_project_role_item_supports_permission_profile(
    client: AsyncClient, db_session: AsyncSession
):
    """项目角色字典项应支持权限档位字段的创建、读取和更新。"""
    await _create_admin(db_session)
    token = await _login(client, "dict-admin", "Admin@1234")

    category_resp = await client.post(
        "/api/v1/dict/categories",
        json={
            "code": "project_role",
            "name": "项目角色",
            "description": "项目角色字典",
        },
        headers=_auth_header(token),
    )
    assert category_resp.status_code == 200, category_resp.text
    category_id = category_resp.json()["id"]

    create_resp = await client.post(
        f"/api/v1/dict/categories/{category_id}/items",
        json={
            "code": "coordinator",
            "label": "协调人",
            "sort_order": 5,
            "extra": "cyan",
            "permission_profile": "manager",
        },
        headers=_auth_header(token),
    )
    assert create_resp.status_code == 200, create_resp.text
    assert create_resp.json()["permission_profile"] == "manager"

    list_resp = await client.get(
        "/api/v1/dict/categories/project_role/items",
        headers=_auth_header(token),
    )
    assert list_resp.status_code == 200, list_resp.text
    created_item = next(item for item in list_resp.json() if item["code"] == "coordinator")
    assert created_item["permission_profile"] == "manager"

    update_resp = await client.patch(
        f"/api/v1/dict/items/{create_resp.json()['id']}",
        json={"permission_profile": "viewer"},
        headers=_auth_header(token),
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["permission_profile"] == "viewer"


@pytest.mark.asyncio
async def test_project_role_item_supports_permission_codes(
    client: AsyncClient, db_session: AsyncSession
):
    """项目角色字典项应支持独立的权限编码映射字段。"""
    await _create_admin(db_session)
    token = await _login(client, "dict-admin", "Admin@1234")

    category_resp = await client.post(
        "/api/v1/dict/categories",
        json={
            "code": "project_role",
            "name": "项目角色",
            "description": "项目角色字典",
        },
        headers=_auth_header(token),
    )
    assert category_resp.status_code == 200, category_resp.text
    category_id = category_resp.json()["id"]

    create_resp = await client.post(
        f"/api/v1/dict/categories/{category_id}/items",
        json={
            "code": "coordinator",
            "label": "协调人",
            "sort_order": 5,
            "permission_profile": "manager",
            "permission_codes": [
                "project.dashboard.menu",
                "project.documents.menu",
                "project.members.manage",
            ],
        },
        headers=_auth_header(token),
    )
    assert create_resp.status_code == 200, create_resp.text
    assert create_resp.json()["permission_codes"] == [
        "project.dashboard.menu",
        "project.documents.menu",
        "project.members.manage",
    ]

    update_resp = await client.patch(
        f"/api/v1/dict/items/{create_resp.json()['id']}",
        json={"permission_codes": ["project.audit_log.view"]},
        headers=_auth_header(token),
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["permission_codes"] == ["project.audit_log.view"]

    list_resp = await client.get(
        "/api/v1/dict/categories/project_role/items",
        headers=_auth_header(token),
    )
    assert list_resp.status_code == 200, list_resp.text
    created_item = next(item for item in list_resp.json() if item["code"] == "coordinator")
    assert created_item["permission_codes"] == ["project.audit_log.view"]

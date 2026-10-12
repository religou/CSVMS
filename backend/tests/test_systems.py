"""被验证系统 API 测试."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import Role, User


async def _create_admin(db: AsyncSession) -> None:
    """创建管理员用户用于系统管理测试."""
    role = Role(name="admin", display_name="管理员")
    db.add(role)
    await db.flush()

    user = User(
        username="sys-admin",
        email="sys-admin@example.com",
        full_name="System Admin",
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
async def test_create_system_with_regulations_round_trip(
    client: AsyncClient, db_session: AsyncSession
):
    """创建系统时提交的符合法规列表应在详情与列表中原样返回。"""
    await _create_admin(db_session)
    headers = _auth_header(await _login(client, "sys-admin", "Admin@1234"))
    regulations = ["fda_21cfr_part11", "eu_gmp_annex11"]

    create_resp = await client.post(
        "/api/v1/systems",
        json={"code": "SYS-REG-1", "name": "法规系统", "regulations": regulations},
        headers=headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    system_id = create_resp.json()["id"]
    assert create_resp.json()["regulations"] == regulations

    get_resp = await client.get(f"/api/v1/systems/{system_id}", headers=headers)
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["regulations"] == regulations

    list_resp = await client.get("/api/v1/systems", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    listed = next(item for item in list_resp.json()["items"] if item["id"] == system_id)
    assert listed["regulations"] == regulations


@pytest.mark.asyncio
async def test_update_system_regulations(client: AsyncClient, db_session: AsyncSession):
    """更新系统时可设置、清空符合法规；未提交该字段时保持不变。"""
    await _create_admin(db_session)
    headers = _auth_header(await _login(client, "sys-admin", "Admin@1234"))

    create_resp = await client.post(
        "/api/v1/systems",
        json={"code": "SYS-REG-2", "name": "无法规系统"},
        headers=headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    system_id = create_resp.json()["id"]
    assert create_resp.json()["regulations"] == []

    patch_resp = await client.patch(
        f"/api/v1/systems/{system_id}",
        json={"regulations": ["ich_q9_r1"]},
        headers=headers,
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["regulations"] == ["ich_q9_r1"]

    get_resp = await client.get(f"/api/v1/systems/{system_id}", headers=headers)
    assert get_resp.json()["regulations"] == ["ich_q9_r1"]

    rename_resp = await client.patch(
        f"/api/v1/systems/{system_id}",
        json={"name": "改名后的系统"},
        headers=headers,
    )
    assert rename_resp.status_code == 200, rename_resp.text
    assert rename_resp.json()["regulations"] == ["ich_q9_r1"]

    clear_resp = await client.patch(
        f"/api/v1/systems/{system_id}",
        json={"regulations": []},
        headers=headers,
    )
    assert clear_resp.status_code == 200, clear_resp.text
    assert clear_resp.json()["regulations"] == []

    get_resp = await client.get(f"/api/v1/systems/{system_id}", headers=headers)
    assert get_resp.json()["regulations"] == []

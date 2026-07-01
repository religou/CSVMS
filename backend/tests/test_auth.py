"""认证 API 测试."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Role, User


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """测试用户注册成功."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "Test@1234",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient):
    """测试重复用户名注册失败."""
    payload = {
        "username": "testuser",
        "email": "test1@example.com",
        "full_name": "Test User",
        "password": "Test@1234",
    }
    await client.post("/api/v1/auth/register", json=payload)
    payload["email"] = "test2@example.com"
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "用户名已存在" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """测试弱密码注册失败."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "weak",
        },
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """测试登录成功."""
    # 先注册
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "Test@1234",
        },
    )
    # 再登录
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "Test@1234"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """测试密码错误登录失败."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "Test@1234",
        },
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "WrongPass@1"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """测试不存在的用户登录失败."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "Test@1234"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient):
    """测试已认证用户获取自身信息."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "Test@1234",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "Test@1234"},
    )
    token = login_resp.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"


@pytest.mark.asyncio
async def test_get_me_returns_system_permissions(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """/auth/me 应返回当前用户的系统权限集合。"""
    from app.scripts.seed_rbac import seed_rbac

    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "permissionuser",
            "email": "permission@example.com",
            "full_name": "Permission User",
            "password": "Test@1234",
        },
    )

    await seed_rbac(db_session)

    role_result = await db_session.execute(select(Role).where(Role.name == "admin"))
    user_result = await db_session.execute(select(User).where(User.username == "permissionuser"))
    user = user_result.scalar_one()
    user.roles = [role_result.scalar_one()]
    await db_session.commit()

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "permissionuser", "password": "Test@1234"},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    assert "system.admin.users.view" in response.json()["permissions"]


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    """测试未认证用户获取信息失败."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403 or response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    """测试 token 刷新."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "Test@1234",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "Test@1234"},
    )
    refresh = login_resp.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_account_lockout(client: AsyncClient):
    """测试多次失败登录后账户锁定."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "Test@1234",
        },
    )
    # 连续5次失败登录
    for _ in range(5):
        await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "Wrong@1234"},
        )

    # 第6次即使密码正确也应该被锁定
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "Test@1234"},
    )
    assert response.status_code == 401
    assert "锁定" in response.json()["detail"]

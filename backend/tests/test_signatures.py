"""电子签名 + 审计追踪 API 测试."""

import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient) -> tuple[str, str]:
    """注册登录并创建文档, 返回 (token, doc_id)."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "siguser",
            "email": "sig@example.com",
            "full_name": "Sig User",
            "password": "Test@1234",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "siguser", "password": "Test@1234"},
    )
    token = resp.json()["access_token"]

    doc_resp = await client.post(
        "/api/v1/documents",
        json={"title": "签名测试文档", "doc_type": "URS", "content": "文档正文内容"},
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = doc_resp.json()["id"]
    return token, doc_id


# ---------- 电子签名测试 ----------


@pytest.mark.asyncio
async def test_sign_document(client: AsyncClient):
    """测试电子签名."""
    token, doc_id = await _setup(client)

    resp = await client.post(
        "/api/v1/signatures",
        json={
            "username": "siguser",
            "password": "Test@1234",
            "document_id": doc_id,
            "meaning": "我已审核此文档",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_id"] == doc_id
    assert data["meaning"] == "我已审核此文档"
    assert data["is_valid"] is True
    assert len(data["content_hash"]) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_sign_wrong_password(client: AsyncClient):
    """测试签名时密码错误."""
    token, doc_id = await _setup(client)

    resp = await client.post(
        "/api/v1/signatures",
        json={
            "username": "siguser",
            "password": "WrongPass@1",
            "document_id": doc_id,
            "meaning": "审核",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "密码错误" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_sign_wrong_username(client: AsyncClient):
    """测试签名时用户名不匹配."""
    token, doc_id = await _setup(client)

    resp = await client.post(
        "/api/v1/signatures",
        json={
            "username": "otheruser",
            "password": "Test@1234",
            "document_id": doc_id,
            "meaning": "审核",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "用户名不匹配" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_document_signatures(client: AsyncClient):
    """测试获取文档签名列表."""
    token, doc_id = await _setup(client)

    # 签两次
    await client.post(
        "/api/v1/signatures",
        json={"username": "siguser", "password": "Test@1234", "document_id": doc_id, "meaning": "起草"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        "/api/v1/signatures",
        json={"username": "siguser", "password": "Test@1234", "document_id": doc_id, "meaning": "审核"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/v1/signatures/document/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_verify_signature(client: AsyncClient):
    """测试验证签名."""
    token, doc_id = await _setup(client)

    sig_resp = await client.post(
        "/api/v1/signatures",
        json={"username": "siguser", "password": "Test@1234", "document_id": doc_id, "meaning": "批准"},
        headers={"Authorization": f"Bearer {token}"},
    )
    sig_id = sig_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/signatures/{sig_id}/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_valid"] is True
    assert resp.json()["meaning"] == "批准"


# ---------- 审计追踪测试 ----------


@pytest.mark.asyncio
async def test_audit_log_created_on_sign(client: AsyncClient):
    """测试签名操作生成审计日志."""
    token, doc_id = await _setup(client)

    await client.post(
        "/api/v1/signatures",
        json={"username": "siguser", "password": "Test@1234", "document_id": doc_id, "meaning": "审核"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/v1/audit-logs",
        params={"resource_type": "document", "resource_id": doc_id, "action": "SIGN"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["items"][0]["action"] == "SIGN"


@pytest.mark.asyncio
async def test_audit_log_list(client: AsyncClient):
    """测试审计日志查询."""
    token, doc_id = await _setup(client)

    # 产生一些审计日志
    await client.post(
        "/api/v1/signatures",
        json={"username": "siguser", "password": "Test@1234", "document_id": doc_id, "meaning": "起草"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_audit_log_resource_trail(client: AsyncClient):
    """测试资源审计追踪."""
    token, doc_id = await _setup(client)

    await client.post(
        "/api/v1/signatures",
        json={"username": "siguser", "password": "Test@1234", "document_id": doc_id, "meaning": "批准"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/v1/audit-logs/resource/document/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

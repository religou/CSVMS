"""追溯矩阵 + 仪表板 API 测试."""

import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient) -> tuple[str, str, str]:
    """注册登录并创建两个文档, 返回 (token, urs_id, fs_id)."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "traceuser",
            "email": "trace@example.com",
            "full_name": "Trace User",
            "password": "Test@1234",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "traceuser", "password": "Test@1234"},
    )
    token = resp.json()["access_token"]

    urs_resp = await client.post(
        "/api/v1/documents",
        json={"title": "URS-001", "doc_type": "URS", "system_name": "TestSys"},
        headers={"Authorization": f"Bearer {token}"},
    )
    fs_resp = await client.post(
        "/api/v1/documents",
        json={"title": "FS-001", "doc_type": "FS", "system_name": "TestSys"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token, urs_resp.json()["id"], fs_resp.json()["id"]


# ---------- 追溯矩阵测试 ----------


@pytest.mark.asyncio
async def test_create_trace_link(client: AsyncClient):
    """测试创建追溯关系."""
    token, urs_id, fs_id = await _setup(client)

    resp = await client.post(
        "/api/v1/traceability/links",
        json={
            "source_document_id": urs_id,
            "target_document_id": fs_id,
            "link_type": "traces_to",
            "description": "URS需求追溯到FS",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_document_id"] == urs_id
    assert data["target_document_id"] == fs_id
    assert data["source_doc_type"] == "URS"
    assert data["target_doc_type"] == "FS"


@pytest.mark.asyncio
async def test_duplicate_link_fails(client: AsyncClient):
    """测试重复创建追溯关系失败."""
    token, urs_id, fs_id = await _setup(client)

    await client.post(
        "/api/v1/traceability/links",
        json={"source_document_id": urs_id, "target_document_id": fs_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.post(
        "/api/v1/traceability/links",
        json={"source_document_id": urs_id, "target_document_id": fs_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_self_link_fails(client: AsyncClient):
    """测试自身追溯关系失败."""
    token, urs_id, _ = await _setup(client)

    resp = await client.post(
        "/api/v1/traceability/links",
        json={"source_document_id": urs_id, "target_document_id": urs_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_document_traces(client: AsyncClient):
    """测试获取文档追溯关系."""
    token, urs_id, fs_id = await _setup(client)

    await client.post(
        "/api/v1/traceability/links",
        json={"source_document_id": urs_id, "target_document_id": fs_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/v1/traceability/document/{urs_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["downstream"]) == 1
    assert len(data["upstream"]) == 0

    # FS的上游
    resp2 = await client.get(
        f"/api/v1/traceability/document/{fs_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(resp2.json()["upstream"]) == 1


@pytest.mark.asyncio
async def test_delete_trace_link(client: AsyncClient):
    """测试删除追溯关系."""
    token, urs_id, fs_id = await _setup(client)

    create_resp = await client.post(
        "/api/v1/traceability/links",
        json={"source_document_id": urs_id, "target_document_id": fs_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    link_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/traceability/links/{link_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_trace_matrix(client: AsyncClient):
    """测试获取追溯矩阵."""
    token, urs_id, fs_id = await _setup(client)

    await client.post(
        "/api/v1/traceability/links",
        json={"source_document_id": urs_id, "target_document_id": fs_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/v1/traceability/matrix?system_name=TestSys",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "coverage" in data
    assert "gaps" in data
    assert "links" in data
    # URS has a link so coverage should show it
    assert data["coverage"]["URS"]["covered"] == 1


# ---------- 仪表板测试 ----------


@pytest.mark.asyncio
async def test_dashboard(client: AsyncClient):
    """测试仪表板统计."""
    token, _, _ = await _setup(client)

    resp = await client.get(
        "/api/v1/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_documents"] >= 2
    assert "status_distribution" in data
    assert "type_distribution" in data
    assert "workflow_stats" in data
    assert "my_drafts" in data

"""文档管理 API 测试."""

import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient) -> str:
    """注册并登录，返回 access_token."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "docuser",
            "email": "doc@example.com",
            "full_name": "Doc User",
            "password": "Test@1234",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "docuser", "password": "Test@1234"},
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_create_document(client: AsyncClient):
    """测试创建文档."""
    token = await _register_and_login(client)
    response = await client.post(
        "/api/v1/documents",
        json={
            "title": "测试URS文档",
            "doc_type": "URS",
            "system_name": "TestSystem",
            "summary": "用户需求规格说明",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "测试URS文档"
    assert data["doc_type"] == "URS"
    assert data["status"] == "draft"
    assert "URS-" in data["doc_number"]


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient):
    """测试文档列表."""
    token = await _register_and_login(client)
    # 创建两个文档
    await client.post(
        "/api/v1/documents",
        json={"title": "URS-1", "doc_type": "URS"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        "/api/v1/documents",
        json={"title": "FS-1", "doc_type": "FS"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # 列表 - 全部
    resp = await client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 2

    # 按类型筛选
    resp = await client.get(
        "/api/v1/documents?doc_type=URS",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["doc_type"] == "URS"


@pytest.mark.asyncio
async def test_update_document(client: AsyncClient):
    """测试更新文档."""
    token = await _register_and_login(client)
    create_resp = await client.post(
        "/api/v1/documents",
        json={"title": "原始标题", "doc_type": "URS"},
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/documents/{doc_id}",
        json={"title": "修改后标题", "content": "文档内容"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "修改后标题"


@pytest.mark.asyncio
async def test_get_document_detail(client: AsyncClient):
    """测试获取文档详情."""
    token = await _register_and_login(client)
    create_resp = await client.post(
        "/api/v1/documents",
        json={"title": "详情测试", "doc_type": "FS", "content": "测试内容"},
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "测试内容"
    assert "versions" in data


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient):
    """测试删除文档."""
    token = await _register_and_login(client)
    create_resp = await client.post(
        "/api/v1/documents",
        json={"title": "待删除", "doc_type": "URS"},
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # 确认已删除
    resp = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """测试未认证访问文档."""
    resp = await client.get("/api/v1/documents")
    assert resp.status_code in [401, 403]


@pytest.mark.asyncio
async def test_update_document_creates_audit_log(client: AsyncClient):
    """测试文档更新后写入审计日志."""
    token = await _register_and_login(client)
    create_resp = await client.post(
        "/api/v1/documents",
        json={"title": "审计测试", "doc_type": "URS", "content": "原始内容"},
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = create_resp.json()["id"]

    # 更新 title 和 content
    resp = await client.put(
        f"/api/v1/documents/{doc_id}",
        json={"title": "修改标题", "content": "新的内容"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # 查询审计日志
    audit_resp = await client.get(
        f"/api/v1/audit-logs?resource_type=document&resource_id={doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert audit_resp.status_code == 200
    logs = audit_resp.json()["items"]
    # 应有 2 条记录（title 和 content 各一条）
    update_logs = [l for l in logs if l["action"] == "UPDATE"]
    assert len(update_logs) == 2
    fields_changed = {l["field_changed"] for l in update_logs}
    assert "title" in fields_changed
    assert "content" in fields_changed


@pytest.mark.asyncio
async def test_update_document_audit_log_keeps_full_before_after_values(client: AsyncClient):
    """测试文档更新审计日志保留完整前后值."""
    token = await _register_and_login(client)
    original_content = "原始内容-" + ("A" * 140)
    updated_content = "更新内容-" + ("B" * 160)

    create_resp = await client.post(
        "/api/v1/documents",
        json={"title": "长文本审计", "doc_type": "URS", "content": original_content},
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/documents/{doc_id}",
        json={"content": updated_content},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    audit_resp = await client.get(
        f"/api/v1/audit-logs?resource_type=document&resource_id={doc_id}&action=UPDATE",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert audit_resp.status_code == 200

    content_logs = [
        log
        for log in audit_resp.json()["items"]
        if log["field_changed"] == "content"
    ]
    assert len(content_logs) == 1
    assert content_logs[0]["old_value"] == original_content
    assert content_logs[0]["new_value"] == updated_content

"""审批工作流 API 测试."""

import pytest
from httpx import AsyncClient


async def _setup_user_and_doc(client: AsyncClient) -> tuple[str, str]:
    """创建用户和文档，返回 (token, doc_id)."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "wfuser",
            "email": "wf@example.com",
            "full_name": "Workflow User",
            "password": "Test@1234",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "wfuser", "password": "Test@1234"},
    )
    token = resp.json()["access_token"]

    # 创建文档
    doc_resp = await client.post(
        "/api/v1/documents",
        json={"title": "测试文档", "doc_type": "URS"},
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = doc_resp.json()["id"]
    return token, doc_id


async def _create_template(client: AsyncClient, token: str) -> str:
    """创建工作流模板，返回 template_id."""
    resp = await client.post(
        "/api/v1/workflows/templates",
        json={
            "name": "URS审批流程",
            "doc_type": "URS",
            "description": "用户需求审批",
            "steps": [
                {"name": "QA审核", "step_type": "review"},
                {"name": "QA批准", "step_type": "approve"},
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_workflow_template(client: AsyncClient):
    """测试创建工作流模板."""
    token, _ = await _setup_user_and_doc(client)
    resp = await client.post(
        "/api/v1/workflows/templates",
        json={
            "name": "FS审批流程",
            "doc_type": "FS",
            "steps": [
                {"name": "审核", "step_type": "review"},
                {"name": "批准", "step_type": "approve"},
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "FS审批流程"
    assert len(data["steps"]) == 2
    assert data["steps"][0]["step_order"] == 1


@pytest.mark.asyncio
async def test_list_workflow_templates(client: AsyncClient):
    """测试获取模板列表."""
    token, _ = await _setup_user_and_doc(client)
    await _create_template(client, token)

    resp = await client.get(
        "/api/v1/workflows/templates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_submit_document_for_review(client: AsyncClient):
    """测试提交文档审批."""
    token, doc_id = await _setup_user_and_doc(client)
    await _create_template(client, token)

    resp = await client.post(
        "/api/v1/workflows/submit",
        json={"document_id": doc_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "in_progress"
    assert data["current_step_order"] == 1
    assert len(data["steps"]) == 2
    assert data["steps"][0]["status"] == "in_progress"
    assert data["steps"][1]["status"] == "pending"


@pytest.mark.asyncio
async def test_submit_non_draft_document_fails(client: AsyncClient):
    """测试非草稿文档不能提交."""
    token, doc_id = await _setup_user_and_doc(client)
    await _create_template(client, token)

    # 第一次提交
    await client.post(
        "/api/v1/workflows/submit",
        json={"document_id": doc_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    # 再次提交应失败
    resp = await client.post(
        "/api/v1/workflows/submit",
        json={"document_id": doc_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_approve_workflow_steps(client: AsyncClient):
    """测试逐步审批直到完成."""
    token, doc_id = await _setup_user_and_doc(client)
    await _create_template(client, token)

    # 提交
    submit_resp = await client.post(
        "/api/v1/workflows/submit",
        json={"document_id": doc_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    workflow_id = submit_resp.json()["id"]

    # 批准第一步
    resp = await client.post(
        f"/api/v1/workflows/{workflow_id}/approve",
        json={"comment": "审核通过"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["current_step_order"] == 2
    assert resp.json()["steps"][0]["status"] == "approved"
    assert resp.json()["steps"][1]["status"] == "in_progress"

    # 批准第二步 → 流程完成
    resp = await client.post(
        f"/api/v1/workflows/{workflow_id}/approve",
        json={"comment": "批准生效"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_reject_workflow(client: AsyncClient):
    """测试拒绝审批."""
    token, doc_id = await _setup_user_and_doc(client)
    await _create_template(client, token)

    submit_resp = await client.post(
        "/api/v1/workflows/submit",
        json={"document_id": doc_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    workflow_id = submit_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/workflows/{workflow_id}/reject",
        json={"comment": "内容不完整"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_withdraw_workflow(client: AsyncClient):
    """测试撤回审批."""
    token, doc_id = await _setup_user_and_doc(client)
    await _create_template(client, token)

    submit_resp = await client.post(
        "/api/v1/workflows/submit",
        json={"document_id": doc_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    workflow_id = submit_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/workflows/{workflow_id}/withdraw",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_get_workflow_actions(client: AsyncClient):
    """测试获取审批操作历史."""
    token, doc_id = await _setup_user_and_doc(client)
    await _create_template(client, token)

    submit_resp = await client.post(
        "/api/v1/workflows/submit",
        json={"document_id": doc_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    workflow_id = submit_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/workflows/{workflow_id}/actions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    actions = resp.json()
    assert len(actions) >= 1
    assert actions[0]["action"] == "submit"

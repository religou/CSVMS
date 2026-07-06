"""追溯矩阵 + 仪表板 API 测试."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Role, User


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
        json={"title": "URS-001", "doc_type": "URS"},
        headers={"Authorization": f"Bearer {token}"},
    )
    fs_resp = await client.post(
        "/api/v1/documents",
        json={"title": "FS-001", "doc_type": "FS"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token, urs_resp.json()["id"], fs_resp.json()["id"]


async def _setup_two_projects(
    client: AsyncClient, db_session: AsyncSession, token: str
) -> tuple[str, str]:
    """赋予 traceuser admin 角色并创建两个独立项目，返回 (project_a_id, project_b_id)."""
    role_result = await db_session.execute(select(Role).where(Role.name == "admin"))
    admin_role = role_result.scalar_one_or_none()
    if admin_role is None:
        admin_role = Role(name="admin", display_name="admin")
        db_session.add(admin_role)
        await db_session.flush()
    user_result = await db_session.execute(
        select(User).where(User.username == "traceuser")
    )
    user = user_result.scalar_one()
    user.roles = [admin_role]
    await db_session.commit()

    system_resp = await client.post(
        "/api/v1/systems",
        json={"code": "SYS-DASH", "name": "仪表板测试系统"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert system_resp.status_code == 200, system_resp.text
    system_id = system_resp.json()["id"]

    project_a = await client.post(
        "/api/v1/projects",
        json={"name": "项目A", "system_id": system_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert project_a.status_code == 200, project_a.text

    project_b = await client.post(
        "/api/v1/projects",
        json={"name": "项目B", "system_id": system_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert project_b.status_code == 200, project_b.text

    return project_a.json()["id"], project_b.json()["id"]


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
        "/api/v1/traceability/matrix",
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


@pytest.mark.asyncio
async def test_dashboard_scoped_to_project(
    client: AsyncClient, db_session: AsyncSession
):
    """测试仪表板统计按项目范围隔离，不同项目互不影响."""
    token, _, _ = await _setup(client)
    project_a_id, project_b_id = await _setup_two_projects(client, db_session, token)

    # 项目A下创建 2 个文档，项目B下创建 1 个文档
    await client.post(
        "/api/v1/documents",
        json={"title": "A-URS", "doc_type": "URS", "project_id": project_a_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        "/api/v1/documents",
        json={"title": "A-FS", "doc_type": "FS", "project_id": project_a_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        "/api/v1/documents",
        json={"title": "B-URS", "doc_type": "URS", "project_id": project_b_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp_a = await client.get(
        f"/api/v1/dashboard?project_id={project_a_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_a.status_code == 200
    assert resp_a.json()["total_documents"] == 2

    resp_b = await client.get(
        f"/api/v1/dashboard?project_id={project_b_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_b.status_code == 200
    assert resp_b.json()["total_documents"] == 1


@pytest.mark.asyncio
async def test_trace_matrix_scoped_to_project(
    client: AsyncClient, db_session: AsyncSession
):
    """测试追溯矩阵按项目范围隔离，不同项目的文档与追溯关系互不影响."""
    token, _, _ = await _setup(client)
    project_a_id, project_b_id = await _setup_two_projects(client, db_session, token)

    # 项目A: URS -> FS 一条追溯关系
    a_urs = await client.post(
        "/api/v1/documents",
        json={"title": "A-URS", "doc_type": "URS", "project_id": project_a_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    a_fs = await client.post(
        "/api/v1/documents",
        json={"title": "A-FS", "doc_type": "FS", "project_id": project_a_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        "/api/v1/traceability/links",
        json={
            "source_document_id": a_urs.json()["id"],
            "target_document_id": a_fs.json()["id"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # 项目B: 一个未被追溯的 URS 文档
    await client.post(
        "/api/v1/documents",
        json={"title": "B-URS", "doc_type": "URS", "project_id": project_b_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp_a = await client.get(
        f"/api/v1/traceability/matrix?project_id={project_a_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert len(data_a["links"]) == 1
    assert data_a["coverage"]["URS"]["total"] == 1
    assert data_a["coverage"]["URS"]["covered"] == 1
    # URS 已被追溯到 FS，不应出现在 Gap 中；FS 尚无下游追溯，会出现在 Gap 中
    gap_doc_numbers = {g["doc_number"] for g in data_a["gaps"]}
    assert a_urs.json()["doc_number"] not in gap_doc_numbers

    resp_b = await client.get(
        f"/api/v1/traceability/matrix?project_id={project_b_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["links"] == []
    assert data_b["coverage"]["URS"]["total"] == 1
    assert data_b["coverage"]["URS"]["covered"] == 0
    assert len(data_b["gaps"]) == 1

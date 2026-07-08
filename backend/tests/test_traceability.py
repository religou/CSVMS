"""追溯矩阵 + 仪表板 API 测试."""

import uuid

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.urs import URSItem, URSReference
from app.models.user import Role, User
from app.services.traceability_service import TraceabilityService


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


# ---------------------------------------------------------------------------
# Property-based test: 追溯矩阵按项目范围隔离 URS 条目统计 (Task 7.2, Property 13)
# ---------------------------------------------------------------------------


async def _create_admin_user_p13(db: AsyncSession, *, username: str) -> User:
    """直接写入一个具备 admin 角色的用户，供属性测试满足权限校验."""
    result = await db.execute(select(Role).where(Role.name == "admin"))
    admin_role = result.scalar_one_or_none()
    if admin_role is None:
        admin_role = Role(name="admin", display_name="管理员")
        db.add(admin_role)
        await db.flush()

    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username,
        password_hash=hash_password("Admin@1234"),
    )
    user.roles = [admin_role]
    db.add(user)
    await db.flush()
    await db.commit()
    return user


@st.composite
def _property13_projects(draw):
    """生成 2~3 个项目，每个项目下有 0~4 个 URS_Item，每个条目是否被引用随机决定；
    并随机选定其中一个项目作为待查询的目标项目, 返回
    (projects_covered_flags, target_index)，其中 projects_covered_flags 是
    List[List[bool]]（外层为项目，内层为该项目下每个条目是否被覆盖）。"""
    project_count = draw(st.integers(min_value=2, max_value=3))
    projects_covered_flags = [
        draw(st.lists(st.booleans(), min_size=0, max_size=4))
        for _ in range(project_count)
    ]
    target_index = draw(st.integers(min_value=0, max_value=project_count - 1))
    return projects_covered_flags, target_index


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(scenario=_property13_projects())
@pytest.mark.asyncio
async def test_property_trace_matrix_isolates_urs_items_by_project(
    db_session: AsyncSession,
    scenario: tuple,
):
    """
    Feature: urs-traceability-matrix, Property 13: 追溯矩阵按项目范围隔离 URS 条目统计

    For any 分布在多个不同项目下的 URS_Document 及其 URS_Item、URS_Reference 数据集合，
    指定某一 project_id 计算追溯矩阵时，其 urs_coverage 与 uncovered_urs_items SHALL
    仅反映该 project_id 范围内的 URS_Item 数据，不包含其他项目的数据。

    Validates: Requirements 5.5
    """
    projects_covered_flags, target_index = scenario
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user_p13(db_session, username=f"prop13-admin-{suffix}")

    # 为每个项目创建一个 URS 文档 + 其条目集合，覆盖的条目再关联一个同项目的 FS 文档。
    project_item_ids: list[list[str]] = []
    target_project_id: str | None = None

    for project_index, covered_flags in enumerate(projects_covered_flags):
        project_id = f"prop13-project-{suffix}-{project_index}"
        if project_index == target_index:
            target_project_id = project_id

        urs_document = Document(
            title=f"URS-{suffix}-{project_index}",
            doc_type=DocumentType.URS,
            doc_number=f"URS-PROP13-{suffix}-{project_index}",
            status=DocumentStatus.DRAFT,
            project_id=project_id,
            author_id=admin.id,
        )
        db_session.add(urs_document)
        await db_session.flush()

        item_ids: list[str] = []
        for item_index, is_covered in enumerate(covered_flags):
            item = URSItem(
                document_id=urs_document.id,
                item_code=f"ITEM-{item_index}",
                description=f"条目描述-{project_index}-{item_index}",
                created_by=admin.id,
            )
            db_session.add(item)
            await db_session.flush()
            item_ids.append(item.id)

            if is_covered:
                ref_document = Document(
                    title=f"FS-{suffix}-{project_index}-{item_index}",
                    doc_type=DocumentType.FS,
                    doc_number=f"FS-PROP13-{suffix}-{project_index}-{item_index}",
                    status=DocumentStatus.DRAFT,
                    project_id=project_id,
                    author_id=admin.id,
                )
                db_session.add(ref_document)
                await db_session.flush()

                reference = URSReference(
                    document_id=ref_document.id,
                    urs_item_id=item.id,
                    created_by=admin.id,
                )
                db_session.add(reference)
                await db_session.flush()

        project_item_ids.append(item_ids)

    await db_session.commit()

    assert target_project_id is not None

    service = TraceabilityService(db_session)
    result = await service.get_matrix(project_id=target_project_id)

    target_covered_flags = projects_covered_flags[target_index]
    target_item_ids = set(project_item_ids[target_index])
    other_item_ids: set[str] = set()
    for project_index, item_ids in enumerate(project_item_ids):
        if project_index != target_index:
            other_item_ids.update(item_ids)

    expected_total = len(target_covered_flags)
    expected_covered = sum(1 for c in target_covered_flags if c)
    expected_uncovered = expected_total - expected_covered

    urs_coverage = result["urs_coverage"]
    assert urs_coverage["total"] == expected_total
    assert urs_coverage["covered"] == expected_covered
    assert urs_coverage["uncovered"] == expected_uncovered

    uncovered_item_ids = {u["id"] for u in result["uncovered_urs_items"]}
    # 未覆盖条目集合必须恰好等于目标项目内未被引用的条目集合
    expected_uncovered_ids = {
        item_id
        for item_id, is_covered in zip(project_item_ids[target_index], target_covered_flags)
        if not is_covered
    }
    assert uncovered_item_ids == expected_uncovered_ids

    # 未覆盖条目集合中不应包含目标项目之外的任何条目 id
    assert uncovered_item_ids.isdisjoint(other_item_ids)
    # 未覆盖条目集合中的所有 id 必须属于目标项目的条目集合
    assert uncovered_item_ids.issubset(target_item_ids)


# ---------------------------------------------------------------------------
# Property-based tests: URS 条目级追溯覆盖率 (urs-traceability-matrix)
# ---------------------------------------------------------------------------

import uuid

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.core.security import hash_password
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.project import Project
from app.models.urs import URSItem, URSReference
from app.services.traceability_service import TraceabilityService


async def _create_admin_user_for_trace(db: AsyncSession, *, username: str) -> User:
    """直接写入一个具备 admin 角色的用户，供属性测试满足权限校验."""
    result = await db.execute(select(Role).where(Role.name == "admin"))
    admin_role = result.scalar_one_or_none()
    if admin_role is None:
        admin_role = Role(name="admin", display_name="管理员")
        db.add(admin_role)
        await db.flush()

    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username,
        password_hash=hash_password("Admin@1234"),
    )
    user.roles = [admin_role]
    db.add(user)
    await db.flush()
    await db.commit()
    return user


_REFERENCING_DOC_TYPES_TRACE = [
    DocumentType.FS,
    DocumentType.DS,
    DocumentType.IQ,
    DocumentType.OQ,
    DocumentType.PQ,
]


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    has_reference_flags=st.lists(st.booleans(), min_size=0, max_size=6),
)
@pytest.mark.asyncio
async def test_property_urs_item_uncovered_status_determination(
    db_session: AsyncSession,
    has_reference_flags: list[bool],
):
    """
    Feature: urs-traceability-matrix, Property 11: URS 条目的未覆盖状态判定

    For any URS_Item 及任意一组 URS_Reference 记录，该条目被判定为 Uncovered_URS_Item，
    当且仅当不存在任何 urs_item_id 等于该条目 id 的 URS_Reference 记录。

    Validates: Requirements 5.1, 5.2
    """
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user_for_trace(db_session, username=f"prop11-admin-{suffix}")

    urs_document = Document(
        title=f"URS-{suffix}",
        doc_type=DocumentType.URS,
        doc_number=f"URS-PROP11-{suffix}",
        status=DocumentStatus.DRAFT,
        project_id=None,
        author_id=admin.id,
    )
    db_session.add(urs_document)
    await db_session.flush()

    covered_item_ids: set[str] = set()
    uncovered_item_ids: set[str] = set()

    for i, has_reference in enumerate(has_reference_flags):
        item = URSItem(
            document_id=urs_document.id,
            item_code=f"ITEM-{suffix}-{i}",
            description=f"条目描述-{i}",
            created_by=admin.id,
        )
        db_session.add(item)
        await db_session.flush()

        if has_reference:
            ref_doc_type = _REFERENCING_DOC_TYPES_TRACE[i % len(_REFERENCING_DOC_TYPES_TRACE)]
            referencing_document = Document(
                title=f"{ref_doc_type.value}-{suffix}-{i}",
                doc_type=ref_doc_type,
                doc_number=f"{ref_doc_type.value}-PROP11-{suffix}-{i}",
                status=DocumentStatus.DRAFT,
                project_id=None,
                author_id=admin.id,
            )
            db_session.add(referencing_document)
            await db_session.flush()

            db_session.add(
                URSReference(
                    document_id=referencing_document.id,
                    urs_item_id=item.id,
                    created_by=admin.id,
                )
            )
            covered_item_ids.add(item.id)
        else:
            uncovered_item_ids.add(item.id)

    await db_session.commit()

    service = TraceabilityService(db_session)
    matrix = await service.get_matrix()

    reported_uncovered_ids = {
        entry["id"]
        for entry in matrix["uncovered_urs_items"]
        if entry["document_id"] == urs_document.id
    }

    assert reported_uncovered_ids == uncovered_item_ids
    assert reported_uncovered_ids.isdisjoint(covered_item_ids)


# ---------------------------------------------------------------------------
# 集成测试: 端到端流程（Task 8.1）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_end_to_end_urs_traceability_flow(
    client: AsyncClient, db_session: AsyncSession
):
    """
    集成测试: 完整走通"创建 URS 文档 → 新增条目 → 创建 FS 文档 → 关联条目 →
    查询详情 → 提交审批 → 查询追溯矩阵"端到端流程。

    验证:
    1. 创建 URS 文档并添加条目正常工作
    2. 创建 FS 文档并关联 URS 条目正常工作
    3. FS 文档未关联 URS 条目时无法提交审批 (400)
    4. 关联 URS 条目后提交审批不因缺少引用被拒（可能因缺模板被拒，但不因 URS 引用校验）
    5. 追溯矩阵正确反映 URS 覆盖率

    Requirements validated: 1.1, 2.1, 2.2, 3.1, 4.1
    """
    # --- 注册用户并赋予 admin 角色 ---
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "e2euser",
            "email": "e2e@example.com",
            "full_name": "E2E User",
            "password": "Test@1234",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "e2euser", "password": "Test@1234"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 赋予 admin 角色以创建项目和管理文档
    from app.models.user import Role, User as UserModel
    role_result = await db_session.execute(select(Role).where(Role.name == "admin"))
    admin_role = role_result.scalar_one_or_none()
    if admin_role is None:
        admin_role = Role(name="admin", display_name="admin")
        db_session.add(admin_role)
        await db_session.flush()
    user_result = await db_session.execute(
        select(User).where(User.username == "e2euser")
    )
    user = user_result.scalar_one()
    user.roles = [admin_role]
    await db_session.commit()

    # --- 创建系统和项目 ---
    sys_resp = await client.post(
        "/api/v1/systems",
        json={"code": "SYS-E2E", "name": "E2E测试系统"},
        headers=headers,
    )
    assert sys_resp.status_code == 200, sys_resp.text
    system_id = sys_resp.json()["id"]

    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "E2E项目", "system_id": system_id},
        headers=headers,
    )
    assert proj_resp.status_code == 200, proj_resp.text
    project_id = proj_resp.json()["id"]

    # === 步骤 1: 创建 URS 文档 ===
    urs_resp = await client.post(
        "/api/v1/documents",
        json={"title": "URS-E2E", "doc_type": "URS", "project_id": project_id},
        headers=headers,
    )
    assert urs_resp.status_code == 200, urs_resp.text
    urs_doc_id = urs_resp.json()["id"]

    # === 步骤 2: 为 URS 文档新增条目 ===
    item1_resp = await client.post(
        f"/api/v1/documents/{urs_doc_id}/urs-items",
        json={"description": "用户登录功能"},
        headers=headers,
    )
    assert item1_resp.status_code == 200, item1_resp.text
    item1_id = item1_resp.json()["id"]
    item1_code = item1_resp.json()["item_code"]
    # item_code is auto-generated, verify format matches {doc_number}-{NNN}
    assert item1_code.endswith("-001")
    assert item1_resp.json()["description"] == "用户登录功能"

    item2_resp = await client.post(
        f"/api/v1/documents/{urs_doc_id}/urs-items",
        json={"description": "数据导出功能"},
        headers=headers,
    )
    assert item2_resp.status_code == 200, item2_resp.text
    item2_id = item2_resp.json()["id"]
    item2_code = item2_resp.json()["item_code"]
    assert item2_code.endswith("-002")

    # 验证条目列表
    items_resp = await client.get(
        f"/api/v1/documents/{urs_doc_id}/urs-items",
        headers=headers,
    )
    assert items_resp.status_code == 200
    items = items_resp.json()
    assert len(items) == 2

    # === 步骤 3: 创建 FS 文档 ===
    fs_resp = await client.post(
        "/api/v1/documents",
        json={"title": "FS-E2E", "doc_type": "FS", "project_id": project_id},
        headers=headers,
    )
    assert fs_resp.status_code == 200, fs_resp.text
    fs_doc_id = fs_resp.json()["id"]

    # === 步骤 4: FS 文档在未关联 URS 条目时提交审批应被拒绝 (Requirement 3.1) ===
    submit_resp = await client.post(
        "/api/v1/workflows/submit",
        json={"document_id": fs_doc_id},
        headers=headers,
    )
    assert submit_resp.status_code == 400, (
        f"FS 文档未关联 URS 条目时提交审批应返回 400, got {submit_resp.status_code}: {submit_resp.text}"
    )
    assert "URS" in submit_resp.json().get("detail", submit_resp.text)

    # === 步骤 5: 为 FS 文档关联 URS 条目 (Requirement 2.1, 2.2) ===
    ref1_resp = await client.post(
        f"/api/v1/documents/{fs_doc_id}/urs-references",
        json={"urs_item_id": item1_id},
        headers=headers,
    )
    assert ref1_resp.status_code == 200, ref1_resp.text
    assert ref1_resp.json()["urs_item_id"] == item1_id
    assert ref1_resp.json()["item_code"] == item1_code

    # === 步骤 6: 查询 FS 文档的 URS 引用列表 (Requirement 4.1) ===
    refs_resp = await client.get(
        f"/api/v1/documents/{fs_doc_id}/urs-references",
        headers=headers,
    )
    assert refs_resp.status_code == 200
    refs = refs_resp.json()
    assert len(refs) == 1
    assert refs[0]["item_code"] == item1_code
    assert refs[0]["description"] == "用户登录功能"

    # === 步骤 7: 关联 URS 条目后再次提交审批 (Requirement 3.1) ===
    # 此时 URS 引用校验应通过，可能因其他原因（如缺少模板）失败但不应因 URS 引用被拒
    submit_resp2 = await client.post(
        "/api/v1/workflows/submit",
        json={"document_id": fs_doc_id},
        headers=headers,
    )
    # 如果返回 400，错误信息不应该包含"URS 条目"相关的引用校验错误
    if submit_resp2.status_code == 400:
        detail = submit_resp2.json().get("detail", "")
        assert "URS" not in detail and "关联" not in detail, (
            f"提交应不因 URS 引用校验失败, got detail: {detail}"
        )
        # 这证明了 Requirement 3.2: 通过 URS 引用校验后，其他规则仍可拒绝提交

    # === 步骤 8: 查询追溯矩阵，验证 URS 覆盖率 (Requirement 5.1, 5.4) ===
    matrix_resp = await client.get(
        f"/api/v1/traceability/matrix?project_id={project_id}",
        headers=headers,
    )
    assert matrix_resp.status_code == 200, matrix_resp.text
    matrix = matrix_resp.json()

    # 验证 urs_coverage 字段存在且计算正确
    assert "urs_coverage" in matrix
    urs_cov = matrix["urs_coverage"]
    assert urs_cov["total"] == 2  # 共 2 个 URS 条目
    assert urs_cov["covered"] == 1  # 只有 item1 被 FS 文档引用
    assert urs_cov["uncovered"] == 1  # item2 未被引用
    assert urs_cov["rate"] == 50.0  # 50% 覆盖率

    # 验证未覆盖条目列表
    assert "uncovered_urs_items" in matrix
    uncovered = matrix["uncovered_urs_items"]
    assert len(uncovered) == 1
    assert uncovered[0]["id"] == item2_id
    assert uncovered[0]["item_code"] == item2_code
    assert uncovered[0]["description"] == "数据导出功能"


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    has_reference_flags=st.lists(st.booleans(), min_size=0, max_size=10),
)
@pytest.mark.asyncio
async def test_property_urs_coverage_statistics_correctness(
    db_session: AsyncSession,
    has_reference_flags: list[bool],
):
    """
    Feature: urs-traceability-matrix, Property 14: URS 条目覆盖率统计的正确性

    For any 一组 URS_Item 及其覆盖状态（包括空集合），urs_coverage.total SHALL 等于
    条目总数，urs_coverage.covered SHALL 等于被覆盖的条目数，urs_coverage.uncovered
    SHALL 等于总数减去已覆盖数，urs_coverage.rate SHALL 等于 covered / total * 100
    并保留一位小数；当 total 为零时，rate SHALL 为零且计算过程不引发除零错误。

    Validates: Requirements 5.4, 6.1, 6.2
    """
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user_for_trace(db_session, username=f"prop14-admin-{suffix}")

    # 每个 hypothesis 样例使用独立的项目范围隔离，避免同一测试函数的多次迭代之间
    # （表不会在迭代间重置）互相污染 urs_coverage 的统计结果。
    project = Project(
        name=f"prop14-project-{suffix}",
        code=f"PROP14-{suffix}",
        system_name="prop14-system",
        created_by=admin.id,
    )
    db_session.add(project)
    await db_session.flush()

    urs_document = Document(
        title=f"URS-{suffix}",
        doc_type=DocumentType.URS,
        doc_number=f"URS-PROP14-{suffix}",
        status=DocumentStatus.DRAFT,
        project_id=project.id,
        author_id=admin.id,
    )
    db_session.add(urs_document)
    await db_session.flush()

    covered_count = 0

    for i, has_reference in enumerate(has_reference_flags):
        item = URSItem(
            document_id=urs_document.id,
            item_code=f"ITEM-{suffix}-{i}",
            description=f"条目描述-{i}",
            created_by=admin.id,
        )
        db_session.add(item)
        await db_session.flush()

        if has_reference:
            ref_doc_type = _REFERENCING_DOC_TYPES_TRACE[i % len(_REFERENCING_DOC_TYPES_TRACE)]
            referencing_document = Document(
                title=f"{ref_doc_type.value}-{suffix}-{i}",
                doc_type=ref_doc_type,
                doc_number=f"{ref_doc_type.value}-PROP14-{suffix}-{i}",
                status=DocumentStatus.DRAFT,
                project_id=project.id,
                author_id=admin.id,
            )
            db_session.add(referencing_document)
            await db_session.flush()

            db_session.add(
                URSReference(
                    document_id=referencing_document.id,
                    urs_item_id=item.id,
                    created_by=admin.id,
                )
            )
            covered_count += 1

    await db_session.commit()

    service = TraceabilityService(db_session)
    matrix = await service.get_matrix(project_id=project.id)
    urs_coverage = matrix["urs_coverage"]

    total = len(has_reference_flags)
    expected_uncovered = total - covered_count
    expected_rate = round(covered_count / total * 100, 1) if total > 0 else 0

    assert urs_coverage["total"] == total
    assert urs_coverage["covered"] == covered_count
    assert urs_coverage["uncovered"] == expected_uncovered
    assert urs_coverage["rate"] == expected_rate

    if total == 0:
        assert urs_coverage["rate"] == 0

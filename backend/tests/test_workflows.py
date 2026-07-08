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


# ---------------------------------------------------------------------------
# Unit test: URS 引用数量校验通过后，既有审批规则仍可独立拒绝提交 (urs-traceability-matrix)
# ---------------------------------------------------------------------------

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.core.security import hash_password
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.urs import URSItem, URSReference
from app.models.user import Role, User
from app.services.document_service import DocumentService
from app.services.workflow_service import WorkflowService


async def _create_admin_user_wf(db: AsyncSession, *, username: str) -> User:
    """直接写入一个具备 admin 角色的用户，供服务层直接调用满足权限校验."""
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


@pytest.mark.asyncio
async def test_submit_document_rejected_by_missing_template_after_urs_check_passes(
    db_session: AsyncSession,
):
    """URS 引用数量校验通过后，既有审批规则（未配置模板）仍可独立拒绝提交.

    构造一个 FS 类型草稿文档，已关联至少一条 URS_Reference（使新增的 URS 引用
    数量校验通过），但未为 FS 配置任何工作流模板。提交审批时 SHALL 仍被拒绝，
    且拒绝原因应为模板缺失（而非 URS 引用数量不足），文档状态保持草稿。

    Validates: Requirements 3.2
    """
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user_wf(db_session, username=f"task62-admin-{suffix}")

    # 创建 URS 文档及其条目
    urs_document = Document(
        title=f"URS-{suffix}",
        doc_type=DocumentType.URS,
        doc_number=f"URS-TASK62-{suffix}",
        status=DocumentStatus.DRAFT,
        project_id=None,
        author_id=admin.id,
    )
    db_session.add(urs_document)
    await db_session.flush()

    urs_item = URSItem(
        document_id=urs_document.id,
        item_code="ITEM-1",
        description="示例用户需求条目",
        created_by=admin.id,
    )
    db_session.add(urs_item)
    await db_session.flush()

    # 创建 FS 草稿文档，并为其关联该 URS 条目
    fs_document = Document(
        title=f"FS-{suffix}",
        doc_type=DocumentType.FS,
        doc_number=f"FS-TASK62-{suffix}",
        status=DocumentStatus.DRAFT,
        project_id=None,
        author_id=admin.id,
    )
    db_session.add(fs_document)
    await db_session.flush()

    db_session.add(
        URSReference(
            document_id=fs_document.id,
            urs_item_id=urs_item.id,
            created_by=admin.id,
        )
    )
    await db_session.commit()

    # 确认 URS 引用数量校验会通过（至少一条引用）
    doc_service = DocumentService(db_session)
    ref_count = await doc_service.count_urs_references(fs_document.id)
    assert ref_count >= 1

    # 未为 FS 配置任何工作流模板，提交审批应因模板缺失被拒绝
    workflow_service = WorkflowService(db_session)
    with pytest.raises(BusinessError) as exc_info:
        await workflow_service.submit_document(fs_document.id, admin.id)

    assert "未配置审批流程模板" in str(exc_info.value)

    # 文档状态应保持草稿
    await db_session.refresh(fs_document)
    assert fs_document.status == DocumentStatus.DRAFT


# ---------------------------------------------------------------------------
# Property-based test: 提交审批的 URS 引用数量校验的适用范围 (Task 6.1, Property 9)
# ---------------------------------------------------------------------------

import uuid

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.core.security import hash_password
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.urs import URSItem, URSReference
from app.models.user import Role, User
from app.models.workflow import StepType, WorkflowTemplate, WorkflowTemplateStep
from app.services.workflow_service import WorkflowService


async def _create_admin_user_p9(db: AsyncSession, *, username: str) -> User:
    """直接写入一个具备 admin 角色的用户，供 Property 9 测试满足权限校验."""
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


async def _create_draft_document_p9(
    db: AsyncSession, *, author_id: str, doc_number: str, doc_type: DocumentType
) -> Document:
    """直接写入一个草稿状态的全局（project_id=None）文档，doc_type 可自定义."""
    document = Document(
        title=f"{doc_type.value}-{doc_number}",
        doc_type=doc_type,
        doc_number=doc_number,
        status=DocumentStatus.DRAFT,
        project_id=None,
        author_id=author_id,
    )
    db.add(document)
    await db.flush()
    await db.commit()
    return document


async def _create_active_template_p9(
    db: AsyncSession, *, doc_type: DocumentType, created_by: str
) -> WorkflowTemplate:
    """直接写入一个具备至少一个步骤的活动工作流模板，供该 doc_type 使用."""
    template = WorkflowTemplate(
        name=f"{doc_type.value}-审批流程",
        doc_type=doc_type.value,
        description="Property 9 测试模板",
        is_active=True,
        created_by=created_by,
    )
    db.add(template)
    await db.flush()

    step = WorkflowTemplateStep(
        template_id=template.id,
        step_order=1,
        name="审核",
        step_type=StepType.REVIEW,
    )
    db.add(step)
    await db.commit()
    await db.refresh(template)
    return template


_REFERENCING_DOC_TYPES_P9 = [
    DocumentType.FS,
    DocumentType.DS,
    DocumentType.IQ,
    DocumentType.OQ,
    DocumentType.PQ,
]

_ALL_DOC_TYPES_P9 = list(DocumentType)


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    doc_type=st.sampled_from(_ALL_DOC_TYPES_P9),
    has_reference=st.booleans(),
)
@pytest.mark.asyncio
async def test_property_submit_document_urs_reference_check_scope(
    db_session: AsyncSession,
    doc_type: DocumentType,
    has_reference: bool,
):
    """
    Feature: urs-traceability-matrix, Property 9: 提交审批的 URS 引用数量校验的适用范围

    For any 提交审批的文档：当其 doc_type 属于 {FS, DS, IQ, OQ, PQ} 且已关联的
    URS_Reference 数量为零时，提交 SHALL 被拒绝且文档 status 保持为草稿；当其
    doc_type 不属于该集合，或已关联的 URS_Reference 数量大于零时，本项校验
    SHALL 不阻塞提交（提交仍可能因其他既有审批规则被拒绝）。

    Validates: Requirements 3.1, 3.3
    """
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user_p9(db_session, username=f"prop9-admin-{suffix}")

    target_document = await _create_draft_document_p9(
        db_session,
        author_id=admin.id,
        doc_number=f"{doc_type.value}-PROP9-{suffix}",
        doc_type=doc_type,
    )

    if has_reference:
        urs_document = await _create_draft_document_p9(
            db_session,
            author_id=admin.id,
            doc_number=f"URS-PROP9-REF-{suffix}",
            doc_type=DocumentType.URS,
        )
        urs_item = URSItem(
            document_id=urs_document.id,
            item_code=f"ITEM-{suffix}",
            description="条目描述",
            created_by=admin.id,
        )
        db_session.add(urs_item)
        await db_session.flush()

        db_session.add(
            URSReference(
                document_id=target_document.id,
                urs_item_id=urs_item.id,
                created_by=admin.id,
            )
        )
        await db_session.commit()

    # 配置一个具备步骤的活动模板，使 URS 校验通过后提交可以真正走完既有提交流程，
    # 从而对"未阻塞提交"给出更强的断言（提交实际成功，而非仅仅未抛出特定异常）。
    await _create_active_template_p9(
        db_session, doc_type=doc_type, created_by=admin.id
    )

    workflow_service = WorkflowService(db_session)
    should_be_blocked_by_urs_check = (
        doc_type in _REFERENCING_DOC_TYPES_P9 and not has_reference
    )

    if should_be_blocked_by_urs_check:
        with pytest.raises(BusinessError) as exc_info:
            await workflow_service.submit_document(target_document.id, admin.id)
        assert exc_info.value.detail == "文档尚未关联任何 URS 条目，无法提交审批"

        result = await db_session.execute(
            select(Document).where(Document.id == target_document.id)
        )
        refreshed = result.scalar_one()
        assert refreshed.status == DocumentStatus.DRAFT
    else:
        workflow = await workflow_service.submit_document(target_document.id, admin.id)
        assert workflow is not None

        result = await db_session.execute(
            select(Document).where(Document.id == target_document.id)
        )
        refreshed = result.scalar_one()
        assert refreshed.status == DocumentStatus.UNDER_REVIEW

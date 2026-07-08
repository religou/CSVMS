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


# ---------------------------------------------------------------------------
# Property-based tests: URS Item / URS Reference (urs-traceability-matrix)
# ---------------------------------------------------------------------------

import uuid

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError, PermissionDeniedError
from app.core.security import hash_password
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.urs import URSItem, URSReference
from app.models.user import Role, User
from app.schemas.urs import URSItemCreate, URSItemUpdate
from app.services.document_service import DocumentService


async def _create_admin_user(db: AsyncSession, *, username: str) -> User:
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


async def _create_draft_urs_document(db: AsyncSession, *, author_id: str, doc_number: str) -> Document:
    """直接写入一个草稿状态的全局（project_id=None）URS 文档."""
    document = Document(
        title=f"URS-{doc_number}",
        doc_type=DocumentType.URS,
        doc_number=doc_number,
        status=DocumentStatus.DRAFT,
        project_id=None,
        author_id=author_id,
    )
    db.add(document)
    await db.flush()
    await db.commit()
    return document


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    existing_count=st.integers(min_value=0, max_value=3),
    candidate_code=st.text(min_size=1, max_size=10),
    candidate_description=st.text(max_size=30),
)
@pytest.mark.asyncio
async def test_property_urs_item_creation_uniqueness_and_content_validation(
    db_session: AsyncSession,
    existing_count: int,
    candidate_code: str,
    candidate_description: str,
):
    """
    Feature: urs-traceability-matrix, Property 1: URS 条目创建的编码唯一性与内容校验

    With auto-numbering: item_code is always auto-generated and unique. The only
    validation that can reject a creation is an empty description.

    For any 合法的 URS 文档及任意候选 (item_code, description)：
    当且仅当 description 非空（不含仅由空白字符组成）时，新增操作 SHALL 成功创建条目
    并自动生成唯一的 item_code；否则 SHALL 被拒绝，返回描述性错误，且该文档下已有
    条目数据保持不变。

    Validates: Requirements 1.2, 1.3
    """
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user(db_session, username=f"prop1-admin-{suffix}")
    doc_number = f"URS-PROP1-{suffix}"
    document = await _create_draft_urs_document(
        db_session, author_id=admin.id, doc_number=doc_number
    )

    # 预置已存在的条目（使用自动编号格式）
    for i in range(existing_count):
        db_session.add(
            URSItem(
                document_id=document.id,
                item_code=f"{doc_number}-{i + 1:03d}",
                description="既有条目描述",
                created_by=admin.id,
            )
        )
    await db_session.commit()

    service = DocumentService(db_session)
    should_succeed = candidate_description.strip() != ""

    if should_succeed:
        item = await service.create_urs_item(
            document.id,
            URSItemCreate(item_code=candidate_code, description=candidate_description),
            admin,
        )
        # item_code is auto-generated, not user-provided
        import re
        assert re.match(rf"^{re.escape(doc_number)}-\d{{3}}$", item.item_code)
        assert item.description == candidate_description

        result = await db_session.execute(
            select(URSItem).where(URSItem.document_id == document.id)
        )
        items = result.scalars().all()
        assert len(items) == existing_count + 1
    else:
        with pytest.raises(BusinessError):
            await service.create_urs_item(
                document.id,
                URSItemCreate(item_code=candidate_code, description=candidate_description),
                admin,
            )

        result = await db_session.execute(
            select(URSItem).where(URSItem.document_id == document.id)
        )
        items = result.scalars().all()
        assert len(items) == existing_count


async def _create_draft_document(
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


_NON_URS_DOC_TYPES = [dt for dt in DocumentType if dt != DocumentType.URS]


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    doc_type=st.sampled_from(_NON_URS_DOC_TYPES),
    operation=st.sampled_from(["create", "update", "delete"]),
)
@pytest.mark.asyncio
async def test_property_urs_item_operations_only_apply_to_urs_documents(
    db_session: AsyncSession,
    doc_type: DocumentType,
    operation: str,
):
    """
    Feature: urs-traceability-matrix, Property 2: URS 条目操作仅适用于 URS 类型文档

    For any doc_type 不为 URS 的文档，对其发起的新增、修改或删除 URS_Item 请求
    SHALL 始终被拒绝，返回描述性错误。

    Validates: Requirements 1.4
    """
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user(db_session, username=f"prop2-admin-{suffix}")
    document = await _create_draft_document(
        db_session,
        author_id=admin.id,
        doc_number=f"{doc_type.value}-PROP2-{suffix}",
        doc_type=doc_type,
    )

    service = DocumentService(db_session)

    if operation == "create":
        with pytest.raises(BusinessError):
            await service.create_urs_item(
                document.id,
                URSItemCreate(item_code="X1", description="desc"),
                admin,
            )
    elif operation == "update":
        with pytest.raises(BusinessError):
            await service.update_urs_item(
                document.id,
                "nonexistent-item-id",
                URSItemUpdate(description="new"),
                admin,
            )
    else:
        with pytest.raises(BusinessError):
            await service.delete_urs_item(
                document.id,
                "nonexistent-item-id",
                admin,
            )


async def _create_urs_document_with_status(
    db: AsyncSession, *, author_id: str, doc_number: str, status: DocumentStatus
) -> Document:
    """直接写入一个指定 status 的全局（project_id=None）URS 文档."""
    document = Document(
        title=f"URS-{doc_number}",
        doc_type=DocumentType.URS,
        doc_number=doc_number,
        status=status,
        project_id=None,
        author_id=author_id,
    )
    db.add(document)
    await db.flush()
    await db.commit()
    return document


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    status=st.sampled_from(list(DocumentStatus)),
    operation=st.sampled_from(["create", "update", "delete"]),
)
@pytest.mark.asyncio
async def test_property_urs_item_maintenance_only_allowed_in_draft_status(
    db_session: AsyncSession,
    status: DocumentStatus,
    operation: str,
):
    """
    Feature: urs-traceability-matrix, Property 3: URS 条目维护仅允许在草稿状态下进行

    For any URS 文档，当其 status 不为草稿时，新增、修改、删除 URS_Item 的请求
    SHALL 被拒绝且已有条目数据保持不变；当其 status 为草稿且其他前置条件满足时，
    该请求 SHALL 被允许。

    Validates: Requirements 1.5
    """
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user(db_session, username=f"prop3-admin-{suffix}")
    document = await _create_urs_document_with_status(
        db_session,
        author_id=admin.id,
        doc_number=f"URS-PROP3-{suffix}",
        status=status,
    )

    # 预置一个已存在的条目，供 update/delete 操作使用。
    existing_item = URSItem(
        document_id=document.id,
        item_code=f"EXIST-{suffix}",
        description="原始描述",
        created_by=admin.id,
    )
    db_session.add(existing_item)
    await db_session.commit()

    service = DocumentService(db_session)
    new_item_code = f"NEWCODE-{suffix}"

    if status == DocumentStatus.DRAFT:
        if operation == "create":
            item = await service.create_urs_item(
                document.id,
                URSItemCreate(item_code=new_item_code, description="desc"),
                admin,
            )
            # item_code is auto-generated, not user-provided
            import re as _re
            assert _re.match(r"^URS-PROP3-.+-\d{3}$", item.item_code)

            result = await db_session.execute(
                select(URSItem).where(
                    URSItem.document_id == document.id,
                    URSItem.item_code == item.item_code,
                )
            )
            assert result.scalar_one_or_none() is not None
        elif operation == "update":
            updated = await service.update_urs_item(
                document.id,
                existing_item.id,
                URSItemUpdate(description="更新后的描述"),
                admin,
            )
            assert updated.description == "更新后的描述"
        else:
            await service.delete_urs_item(document.id, existing_item.id, admin)

            result = await db_session.execute(
                select(URSItem).where(URSItem.id == existing_item.id)
            )
            assert result.scalar_one_or_none() is None
    else:
        if operation == "create":
            with pytest.raises(BusinessError):
                await service.create_urs_item(
                    document.id,
                    URSItemCreate(item_code=new_item_code, description="desc"),
                    admin,
                )

            result = await db_session.execute(
                select(URSItem).where(URSItem.document_id == document.id)
            )
            items = result.scalars().all()
            assert len(items) == 1
            assert items[0].item_code == existing_item.item_code
        elif operation == "update":
            with pytest.raises(BusinessError):
                await service.update_urs_item(
                    document.id,
                    existing_item.id,
                    URSItemUpdate(description="更新后的描述"),
                    admin,
                )

            result = await db_session.execute(
                select(URSItem).where(URSItem.id == existing_item.id)
            )
            unchanged = result.scalar_one()
            assert unchanged.description == "原始描述"
        else:
            with pytest.raises(BusinessError):
                await service.delete_urs_item(document.id, existing_item.id, admin)

            result = await db_session.execute(
                select(URSItem).where(URSItem.id == existing_item.id)
            )
            assert result.scalar_one_or_none() is not None


_REFERENCING_DOC_TYPES = [
    DocumentType.FS,
    DocumentType.DS,
    DocumentType.IQ,
    DocumentType.OQ,
    DocumentType.PQ,
]


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    reference_count=st.integers(min_value=0, max_value=3),
)
@pytest.mark.asyncio
async def test_property_urs_item_with_references_cannot_be_deleted(
    db_session: AsyncSession,
    reference_count: int,
):
    """
    Feature: urs-traceability-matrix, Property 4: 存在引用的 URS 条目禁止删除

    For any URS_Item，删除该条目的请求 SHALL 被允许，当且仅当不存在任何引用该条目的
    URS_Reference；若存在至少一条引用，删除 SHALL 被拒绝，且该条目及其所有引用记录
    保持不变。

    Validates: Requirements 1.6
    """
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user(db_session, username=f"prop4-admin-{suffix}")
    urs_document = await _create_draft_urs_document(
        db_session, author_id=admin.id, doc_number=f"URS-PROP4-{suffix}"
    )

    target_item = URSItem(
        document_id=urs_document.id,
        item_code=f"ITEM-{suffix}",
        description="待删除条目",
        created_by=admin.id,
    )
    db_session.add(target_item)
    await db_session.flush()

    for i in range(reference_count):
        ref_doc_type = _REFERENCING_DOC_TYPES[i % len(_REFERENCING_DOC_TYPES)]
        referencing_document = Document(
            title=f"{ref_doc_type.value}-{suffix}-{i}",
            doc_type=ref_doc_type,
            doc_number=f"{ref_doc_type.value}-PROP4-{suffix}-{i}",
            status=DocumentStatus.DRAFT,
            project_id=None,
            author_id=admin.id,
        )
        db_session.add(referencing_document)
        await db_session.flush()

        db_session.add(
            URSReference(
                document_id=referencing_document.id,
                urs_item_id=target_item.id,
                created_by=admin.id,
            )
        )

    await db_session.commit()

    service = DocumentService(db_session)

    if reference_count == 0:
        await service.delete_urs_item(urs_document.id, target_item.id, admin)

        result = await db_session.execute(
            select(URSItem).where(URSItem.id == target_item.id)
        )
        assert result.scalar_one_or_none() is None
    else:
        with pytest.raises(BusinessError):
            await service.delete_urs_item(urs_document.id, target_item.id, admin)

        result = await db_session.execute(
            select(URSItem).where(URSItem.id == target_item.id)
        )
        assert result.scalar_one_or_none() is not None

        result = await db_session.execute(
            select(URSReference).where(URSReference.urs_item_id == target_item.id)
        )
        remaining_refs = result.scalars().all()
        assert len(remaining_refs) == reference_count


# ---------------------------------------------------------------------------
# Unit tests: 目标文档不存在时新增/修改/删除 URS 条目返回资源不存在错误
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_urs_item_nonexistent_document_returns_not_found(
    db_session: AsyncSession,
):
    """
    Feature: urs-traceability-matrix, Task 3.8

    当目标文档不存在时，新增 URS 条目 SHALL 抛出 BusinessError（资源不存在，404）。

    Validates: Requirements 1.1
    """
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user(db_session, username=f"task38-admin-a-{suffix}")

    service = DocumentService(db_session)

    with pytest.raises(BusinessError) as exc_info:
        await service.create_urs_item(
            "nonexistent-document-id",
            URSItemCreate(item_code="X1", description="desc"),
            admin,
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "文档不存在"


@pytest.mark.asyncio
async def test_update_urs_item_nonexistent_document_returns_not_found(
    db_session: AsyncSession,
):
    """
    Feature: urs-traceability-matrix, Task 3.8

    当目标文档不存在时，修改 URS 条目 SHALL 抛出 BusinessError（资源不存在，404）。

    Validates: Requirements 1.1
    """
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user(db_session, username=f"task38-admin-u-{suffix}")

    service = DocumentService(db_session)

    with pytest.raises(BusinessError) as exc_info:
        await service.update_urs_item(
            "nonexistent-document-id",
            "nonexistent-item-id",
            URSItemUpdate(description="新描述"),
            admin,
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "文档不存在"


@pytest.mark.asyncio
async def test_delete_urs_item_nonexistent_document_returns_not_found(
    db_session: AsyncSession,
):
    """
    Feature: urs-traceability-matrix, Task 3.8

    当目标文档不存在时，删除 URS 条目 SHALL 抛出 BusinessError（资源不存在，404）。

    Validates: Requirements 1.1
    """
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user(db_session, username=f"task38-admin-d-{suffix}")

    service = DocumentService(db_session)

    with pytest.raises(BusinessError) as exc_info:
        await service.delete_urs_item(
            "nonexistent-document-id",
            "nonexistent-item-id",
            admin,
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "文档不存在"


async def _create_non_admin_user(db: AsyncSession, *, username: str) -> User:
    """直接写入一个不具备任何角色（含 admin）的普通用户，供属性测试验证权限拒绝."""
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username,
        password_hash=hash_password("User@1234"),
    )
    # 显式将 roles 置为空列表，使该关系在内存中已被填充，避免后续在异步
    # 上下文之外触发 SQLAlchemy 的懒加载（这会导致 MissingGreenlet 错误）。
    user.roles = []
    db.add(user)
    await db.flush()
    await db.commit()
    return user


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    operation=st.sampled_from(["create", "update", "delete"]),
)
@pytest.mark.asyncio
async def test_property_urs_item_operations_by_unauthorized_user_always_rejected(
    db_session: AsyncSession,
    operation: str,
):
    """
    Feature: urs-traceability-matrix, Property 5: 无权限用户的 URS 条目操作一律被拒绝

    For any 不具备 Documents_Manage_Permission 的用户，及针对任意 URS_Item 的新增、
    修改或删除请求（无论其他条件是否满足），系统 SHALL 拒绝该操作，返回权限不足的
    错误信息，并保持数据不变。

    Validates: Requirements 1.7
    """
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user(db_session, username=f"prop5-admin-{suffix}")
    non_admin = await _create_non_admin_user(db_session, username=f"prop5-user-{suffix}")
    document = await _create_draft_urs_document(
        db_session, author_id=admin.id, doc_number=f"URS-PROP5-{suffix}"
    )

    # 预置一个已存在的条目，供 update/delete 操作使用。
    existing_item = URSItem(
        document_id=document.id,
        item_code=f"EXIST-{suffix}",
        description="原始描述",
        created_by=admin.id,
    )
    db_session.add(existing_item)
    await db_session.commit()

    service = DocumentService(db_session)
    new_item_code = f"NEWCODE-{suffix}"

    if operation == "create":
        with pytest.raises(PermissionDeniedError):
            await service.create_urs_item(
                document.id,
                URSItemCreate(item_code=new_item_code, description="desc"),
                non_admin,
            )

        result = await db_session.execute(
            select(URSItem).where(URSItem.document_id == document.id)
        )
        items = result.scalars().all()
        assert len(items) == 1
        assert items[0].item_code == existing_item.item_code
    elif operation == "update":
        with pytest.raises(PermissionDeniedError):
            await service.update_urs_item(
                document.id,
                existing_item.id,
                URSItemUpdate(description="被篡改的描述"),
                non_admin,
            )

        result = await db_session.execute(
            select(URSItem).where(URSItem.id == existing_item.id)
        )
        unchanged = result.scalar_one()
        assert unchanged.description == "原始描述"
    else:
        with pytest.raises(PermissionDeniedError):
            await service.delete_urs_item(document.id, existing_item.id, non_admin)

        result = await db_session.execute(
            select(URSItem).where(URSItem.id == existing_item.id)
        )
        assert result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Property-based tests: URS_Reference 状态门控与删除隔离性 (Task 4.4, Property 7)
# ---------------------------------------------------------------------------

from app.schemas.urs import URSReferenceCreate as _URSReferenceCreate_P7


async def _create_urs_item_p7(
    db: AsyncSession, *, document_id: str, author_id: str, item_code: str
) -> URSItem:
    """直接写入一个 URS 条目，供 Property 7 测试复用."""
    item = URSItem(
        document_id=document_id,
        item_code=item_code,
        description="条目描述",
        created_by=author_id,
    )
    db.add(item)
    await db.flush()
    await db.commit()
    return item


async def _create_document_with_type_and_status_p7(
    db: AsyncSession,
    *,
    author_id: str,
    doc_number: str,
    doc_type: DocumentType,
    status: DocumentStatus,
) -> Document:
    """直接写入一个指定 doc_type 与 status 的全局（project_id=None）文档，供 Property 7 测试复用."""
    document = Document(
        title=f"{doc_type.value}-{doc_number}",
        doc_type=doc_type,
        doc_number=doc_number,
        status=status,
        project_id=None,
        author_id=author_id,
    )
    db.add(document)
    await db.flush()
    await db.commit()
    return document


_NON_DRAFT_STATUSES_P7 = [s for s in DocumentStatus if s != DocumentStatus.DRAFT]


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    status=st.sampled_from(_NON_DRAFT_STATUSES_P7),
    operation=st.sampled_from(["create", "delete"]),
)
@pytest.mark.asyncio
async def test_property_urs_reference_non_draft_status_gating(
    db_session: AsyncSession,
    status: DocumentStatus,
    operation: str,
):
    """
    Feature: urs-traceability-matrix, Property 7: 引用文档状态门控与删除的隔离性

    For any Referencing_Document 处于非草稿状态时，新增或删除其 URS_Reference 的请求
    SHALL 被拒绝；当处于草稿状态时，删除其中一条 URS_Reference SHALL 精确移除该记录，
    且该文档与任意其他 URS_Item 之间的引用关系、以及其他文档的引用关系 SHALL 保持不变。

    Validates: Requirements 2.6, 2.7
    """
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user(db_session, username=f"prop7-admin-{suffix}")
    urs_document = await _create_draft_urs_document(
        db_session, author_id=admin.id, doc_number=f"URS-PROP7-{suffix}"
    )
    urs_item = await _create_urs_item_p7(
        db_session,
        document_id=urs_document.id,
        author_id=admin.id,
        item_code=f"ITEM-{suffix}",
    )
    ref_document = await _create_document_with_type_and_status_p7(
        db_session,
        author_id=admin.id,
        doc_number=f"FS-PROP7-{suffix}",
        doc_type=DocumentType.FS,
        status=status,
    )

    service = DocumentService(db_session)

    if operation == "create":
        with pytest.raises(BusinessError):
            await service.create_urs_reference(
                ref_document.id,
                _URSReferenceCreate_P7(urs_item_id=urs_item.id),
                admin,
            )

        result = await db_session.execute(
            select(URSReference).where(URSReference.document_id == ref_document.id)
        )
        assert result.scalar_one_or_none() is None
    else:
        # 直接写入一条既有引用记录（service.create_urs_reference 要求草稿状态，
        # 因此非草稿状态下无法通过 service 预置数据，需绕过 service 直接插入）。
        reference = URSReference(
            document_id=ref_document.id,
            urs_item_id=urs_item.id,
            created_by=admin.id,
        )
        db_session.add(reference)
        await db_session.commit()

        with pytest.raises(BusinessError):
            await service.delete_urs_reference(ref_document.id, reference.id, admin)

        result = await db_session.execute(
            select(URSReference).where(URSReference.id == reference.id)
        )
        assert result.scalar_one_or_none() is not None


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    other_item_count=st.integers(min_value=0, max_value=3),
)
@pytest.mark.asyncio
async def test_property_urs_reference_draft_deletion_isolation(
    db_session: AsyncSession,
    other_item_count: int,
):
    """
    Feature: urs-traceability-matrix, Property 7: 引用文档状态门控与删除的隔离性

    For any Referencing_Document 处于非草稿状态时，新增或删除其 URS_Reference 的请求
    SHALL 被拒绝；当处于草稿状态时，删除其中一条 URS_Reference SHALL 精确移除该记录，
    且该文档与任意其他 URS_Item 之间的引用关系、以及其他文档的引用关系 SHALL 保持不变。

    Validates: Requirements 2.6, 2.7
    """
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user(db_session, username=f"prop7b-admin-{suffix}")
    urs_document = await _create_draft_urs_document(
        db_session, author_id=admin.id, doc_number=f"URS-PROP7B-{suffix}"
    )

    target_item = await _create_urs_item_p7(
        db_session,
        document_id=urs_document.id,
        author_id=admin.id,
        item_code=f"TARGET-{suffix}",
    )
    other_items = [
        await _create_urs_item_p7(
            db_session,
            document_id=urs_document.id,
            author_id=admin.id,
            item_code=f"OTHER-{suffix}-{i}",
        )
        for i in range(other_item_count)
    ]
    unrelated_item = await _create_urs_item_p7(
        db_session,
        document_id=urs_document.id,
        author_id=admin.id,
        item_code=f"UNRELATED-{suffix}",
    )

    ref_document = await _create_document_with_type_and_status_p7(
        db_session,
        author_id=admin.id,
        doc_number=f"FS-PROP7B-{suffix}",
        doc_type=DocumentType.FS,
        status=DocumentStatus.DRAFT,
    )
    unrelated_ref_document = await _create_document_with_type_and_status_p7(
        db_session,
        author_id=admin.id,
        doc_number=f"DS-PROP7B-{suffix}",
        doc_type=DocumentType.DS,
        status=DocumentStatus.DRAFT,
    )

    service = DocumentService(db_session)

    target_reference = await service.create_urs_reference(
        ref_document.id, _URSReferenceCreate_P7(urs_item_id=target_item.id), admin
    )
    other_references = [
        await service.create_urs_reference(
            ref_document.id, _URSReferenceCreate_P7(urs_item_id=item.id), admin
        )
        for item in other_items
    ]
    unrelated_reference = await service.create_urs_reference(
        unrelated_ref_document.id,
        _URSReferenceCreate_P7(urs_item_id=unrelated_item.id),
        admin,
    )

    await service.delete_urs_reference(ref_document.id, target_reference.id, admin)

    # 目标引用记录已被精确移除
    result = await db_session.execute(
        select(URSReference).where(URSReference.id == target_reference.id)
    )
    assert result.scalar_one_or_none() is None

    # 该文档与其他 URS_Item 之间的引用关系保持不变
    for ref in other_references:
        result = await db_session.execute(
            select(URSReference).where(URSReference.id == ref.id)
        )
        assert result.scalar_one_or_none() is not None

    # 其他文档的引用关系保持不变
    result = await db_session.execute(
        select(URSReference).where(URSReference.id == unrelated_reference.id)
    )
    assert result.scalar_one_or_none() is not None

    # 该文档剩余引用数量精确等于删除前的数量减一
    result = await db_session.execute(
        select(URSReference).where(URSReference.document_id == ref_document.id)
    )
    remaining = result.scalars().all()
    assert len(remaining) == other_item_count
    assert target_item.id not in {r.urs_item_id for r in remaining}


# ---------------------------------------------------------------------------
# Property-based tests: 无权限用户的 URS_Reference 操作一律被拒绝 (Task 4.5, Property 8)
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    operation=st.sampled_from(["create", "delete"]),
)
@pytest.mark.asyncio
async def test_property_urs_reference_operations_by_unauthorized_user_always_rejected(
    db_session: AsyncSession,
    operation: str,
):
    """
    Feature: urs-traceability-matrix, Property 8: 无权限用户的 URS_Reference 操作一律被拒绝

    For any 不具备 Documents_Manage_Permission 的用户，及针对任意 Referencing_Document
    的新增或删除 URS_Reference 请求（无论其他条件是否满足），系统 SHALL 拒绝该操作，
    返回权限不足的错误信息，并保持数据不变。

    Validates: Requirements 2.8
    """
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user(db_session, username=f"prop8-admin-{suffix}")
    non_admin = await _create_non_admin_user(db_session, username=f"prop8-user-{suffix}")

    urs_document = await _create_draft_urs_document(
        db_session, author_id=admin.id, doc_number=f"URS-PROP8-{suffix}"
    )
    existing_item = await _create_urs_item_p7(
        db_session,
        document_id=urs_document.id,
        author_id=admin.id,
        item_code=f"EXIST-{suffix}",
    )
    new_item = await _create_urs_item_p7(
        db_session,
        document_id=urs_document.id,
        author_id=admin.id,
        item_code=f"NEW-{suffix}",
    )

    ref_document = await _create_document_with_type_and_status_p7(
        db_session,
        author_id=admin.id,
        doc_number=f"FS-PROP8-{suffix}",
        doc_type=DocumentType.FS,
        status=DocumentStatus.DRAFT,
    )

    service = DocumentService(db_session)

    # 预置一条既有引用记录（由管理员创建），供 delete 操作使用。
    existing_reference = await service.create_urs_reference(
        ref_document.id, _URSReferenceCreate_P7(urs_item_id=existing_item.id), admin
    )

    if operation == "create":
        with pytest.raises(PermissionDeniedError):
            await service.create_urs_reference(
                ref_document.id,
                _URSReferenceCreate_P7(urs_item_id=new_item.id),
                non_admin,
            )

        result = await db_session.execute(
            select(URSReference).where(URSReference.document_id == ref_document.id)
        )
        references = result.scalars().all()
        assert len(references) == 1
        assert references[0].id == existing_reference.id
        assert references[0].urs_item_id == existing_item.id
    else:
        with pytest.raises(PermissionDeniedError):
            await service.delete_urs_reference(
                ref_document.id, existing_reference.id, non_admin
            )

        result = await db_session.execute(
            select(URSReference).where(URSReference.id == existing_reference.id)
        )
        unchanged = result.scalar_one_or_none()
        assert unchanged is not None
        assert unchanged.urs_item_id == existing_item.id


# ---------------------------------------------------------------------------
# Property-based test: URS_Reference 创建结果由前置条件精确决定 (Task 4.3, Property 6)
# ---------------------------------------------------------------------------

from app.schemas.urs import URSReferenceCreate as _URSReferenceCreate_P6


async def _create_document_with_project_and_status_p6(
    db: AsyncSession,
    *,
    author_id: str,
    doc_number: str,
    doc_type: DocumentType,
    status: DocumentStatus,
    project_id: str | None,
) -> Document:
    """直接写入一个指定 doc_type / status / project_id 的文档，供 Property 6 测试复用."""
    document = Document(
        title=f"{doc_type.value}-{doc_number}",
        doc_type=doc_type,
        doc_number=doc_number,
        status=status,
        project_id=project_id,
        author_id=author_id,
    )
    db.add(document)
    await db.flush()
    await db.commit()
    return document


@st.composite
def _property6_conditions(draw):
    """组合 4 个前置条件；item_exists=False 时 already_referenced 恒为 False（
    条目不存在时不可能已存在指向该条目的引用记录）."""
    item_exists = draw(st.booleans())
    same_project = draw(st.booleans())
    is_draft = draw(st.booleans())
    already_referenced = draw(st.booleans()) if item_exists else False
    return item_exists, same_project, is_draft, already_referenced


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(conditions=_property6_conditions())
@pytest.mark.asyncio
async def test_property_urs_reference_creation_determined_by_preconditions(
    db_session: AsyncSession,
    conditions: tuple,
):
    """
    Feature: urs-traceability-matrix, Property 6: URS_Reference 创建结果由前置条件精确决定

    For any Referencing_Document 与 URS_Item 的组合及其上下文（该条目是否存在、二者
    project_id 是否一致、该文档是否为草稿状态、二者之间是否已存在引用关系）：创建
    URS_Reference 的请求 SHALL 成功，当且仅当该 URS_Item 存在、与该文档属于同一项目、
    该文档处于草稿状态、且二者之间尚不存在引用关系；否则 SHALL 被拒绝并返回与具体
    缺失条件相符的描述性错误，且现有 URS_Reference 数据保持不变。

    Validates: Requirements 2.2, 2.3, 2.4, 2.5
    """
    item_exists, same_project, is_draft, already_referenced = conditions
    suffix = uuid.uuid4().hex[:12]
    admin = await _create_admin_user(db_session, username=f"prop6-admin-{suffix}")

    project_a = f"project-a-{suffix}"
    project_b = f"project-b-{suffix}"

    urs_document = await _create_document_with_project_and_status_p6(
        db_session,
        author_id=admin.id,
        doc_number=f"URS-PROP6-{suffix}",
        doc_type=DocumentType.URS,
        status=DocumentStatus.DRAFT,
        project_id=project_a,
    )

    if item_exists:
        urs_item = URSItem(
            document_id=urs_document.id,
            item_code=f"ITEM-{suffix}",
            description="条目描述",
            created_by=admin.id,
        )
        db_session.add(urs_item)
        await db_session.flush()
        await db_session.commit()
        urs_item_id = urs_item.id
    else:
        urs_item_id = f"nonexistent-item-{suffix}"

    ref_document = await _create_document_with_project_and_status_p6(
        db_session,
        author_id=admin.id,
        doc_number=f"FS-PROP6-{suffix}",
        doc_type=DocumentType.FS,
        status=DocumentStatus.DRAFT if is_draft else DocumentStatus.UNDER_REVIEW,
        project_id=project_a if same_project else project_b,
    )

    if already_referenced:
        existing_reference = URSReference(
            document_id=ref_document.id,
            urs_item_id=urs_item_id,
            created_by=admin.id,
        )
        db_session.add(existing_reference)
        await db_session.flush()
        await db_session.commit()

    result = await db_session.execute(
        select(URSReference).where(URSReference.document_id == ref_document.id)
    )
    references_before = len(result.scalars().all())

    service = DocumentService(db_session)
    should_succeed = item_exists and same_project and is_draft and not already_referenced

    if should_succeed:
        reference = await service.create_urs_reference(
            ref_document.id, _URSReferenceCreate_P6(urs_item_id=urs_item_id), admin
        )
        assert reference.document_id == ref_document.id
        assert reference.urs_item_id == urs_item_id

        result = await db_session.execute(
            select(URSReference).where(URSReference.document_id == ref_document.id)
        )
        assert len(result.scalars().all()) == references_before + 1
    else:
        with pytest.raises(BusinessError):
            await service.create_urs_reference(
                ref_document.id, _URSReferenceCreate_P6(urs_item_id=urs_item_id), admin
            )

        result = await db_session.execute(
            select(URSReference).where(URSReference.document_id == ref_document.id)
        )
        assert len(result.scalars().all()) == references_before

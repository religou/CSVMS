"""文档服务 - CRUD 和版本管理."""

from datetime import datetime, timezone

from sqlalchemy import Integer, select, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError, PermissionDeniedError
from app.models.document import Document, DocumentVersion, DocumentStatus, DocumentType
from app.models.signature import ElectronicSignature
from app.models.workflow import Workflow, WorkflowStatus
from app.models.urs import URSItem, URSReference
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.schemas.urs import URSItemCreate, URSItemUpdate, URSReferenceCreate
from app.services.audit_service import (
    AuditService,
    DocumentCreated,
    DocumentDeleted,
    DocumentFieldsChanged,
    DocumentRevised,
    FieldChange,
    SignaturesVoided,
    UrsItemAdded,
    UrsItemDescriptionChanged,
    UrsItemRemoved,
    UrsReferenceAdded,
    UrsReferenceRemoved,
    VoidedSignature,
)
from app.services.permission_service import user_has_role
from app.services.project_service import ProjectService


def _parse_major(version: str) -> int:
    """从版本标签解析主版本号，无法解析时按 0 处理."""
    try:
        return int(version.split(".")[0])
    except (ValueError, IndexError):
        return 0


def bump_major_version(version: str) -> str:
    """主版本进位：x.y -> (x+1).0（文档批准通过时）."""
    return f"{_parse_major(version) + 1}.0"


def bump_minor_version(version: str) -> str:
    """次版本进位：x.y -> x.(y+1)（已批准文档发起变更回到草稿时）."""
    parts = version.split(".")
    try:
        major, minor = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return version
    return f"{major}.{minor + 1}"


class DocumentService:
    """验证文档服务."""

    _MAX_ITEM_CODE_RETRIES = 3

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _generate_doc_number(self, doc_type: DocumentType) -> str:
        """生成文档编号: 类型-YYYYMMDD-序号."""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"{doc_type.value}-{today}"

        result = await self.db.execute(
            select(func.count()).where(Document.doc_number.like(f"{prefix}%"))
        )
        count = result.scalar() or 0
        return f"{prefix}-{count + 1:03d}"

    async def _generate_item_code(self, document_id: str, doc_number: str) -> str:
        """生成 URS 条目编号: {doc_number}-{序号:03d}.

        通过查询当前文档下 item_code 后缀最大值 +1 确定序号。
        """
        result = await self.db.execute(
            select(func.max(
                func.cast(
                    func.substring(URSItem.item_code, len(doc_number) + 2),
                    Integer
                )
            )).where(URSItem.document_id == document_id)
        )
        max_seq = result.scalar() or 0
        next_seq = max_seq + 1
        return f"{doc_number}-{next_seq:03d}"

    async def create_document(
        self, data: DocumentCreate, author_id: str, ip_address: str | None = None
    ) -> Document:
        """创建新文档草稿."""
        doc_number = await self._generate_doc_number(data.doc_type)

        document = Document(
            title=data.title,
            doc_type=data.doc_type,
            doc_number=doc_number,
            content=data.content,
            summary=data.summary,
            project_id=data.project_id,
            status=DocumentStatus.DRAFT,
            version="0.1",
            author_id=author_id,
        )
        self.db.add(document)
        # 不提交：事务归属在请求 seam 上（ADR-0004）
        await self.db.flush()

        await AuditService(self.db).record(
            DocumentCreated(
                document_id=document.id,
                doc_number=document.doc_number,
                title=document.title,
            ),
            actor=author_id,
            ip_address=ip_address,
        )

        await self.db.refresh(document)
        return document

    async def get_document(self, document_id: str) -> Document:
        """获取文档详情."""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            raise BusinessError("文档不存在", status_code=404)
        return document

    async def list_documents(
        self,
        doc_type: DocumentType | None = None,
        status: DocumentStatus | None = None,
        keyword: str | None = None,
        project_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Document], int]:
        """获取文档列表."""
        query = select(Document)

        if project_id:
            query = query.where(Document.project_id == project_id)
        if doc_type:
            query = query.where(Document.doc_type == doc_type)
        if status:
            query = query.where(Document.status == status)
        if keyword:
            query = query.where(
                or_(
                    Document.title.contains(keyword),
                    Document.doc_number.contains(keyword),
                )
            )

        # Total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginated results
        query = query.order_by(Document.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)

        return list(result.scalars().all()), total

    #: 可编辑字段 —— 变更差异由本 service 自己算，端点不需要先读旧值（ADR-0006）
    _EDITABLE_FIELDS = ("title", "content", "summary")

    async def update_document(
        self,
        document_id: str,
        data: DocumentUpdate,
        user_id: str,
        ip_address: str | None = None,
    ) -> Document:
        """更新文档内容（仅草稿状态可编辑）."""
        document = await self.get_document(document_id)

        if document.status != DocumentStatus.DRAFT:
            raise BusinessError("只有草稿状态的文档可以编辑")

        changes: list[FieldChange] = []
        for name in self._EDITABLE_FIELDS:
            new_value = getattr(data, name)
            if new_value is None:
                continue
            old_value = getattr(document, name)
            if new_value == old_value:
                continue
            setattr(document, name, new_value)
            changes.append(
                FieldChange(field=name, old_value=old_value, new_value=new_value)
            )

        document.updated_at = datetime.now(timezone.utc)

        # 审计轨迹：每个变更字段各一条，与状态变更同事务（ADR-0003、ADR-0006）
        if changes:
            await AuditService(self.db).record(
                DocumentFieldsChanged(
                    document_id=document_id,
                    title=document.title,
                    changes=tuple(changes),
                ),
                actor=user_id,
                ip_address=ip_address,
            )

        # 不提交：事务归属在请求 seam 上（ADR-0004）
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def revise_document(
        self, document_id: str, user_id: str, change_reason: str, ip_address: str | None = None
    ) -> Document:
        """对已批准文档发起变更：冻结当前已批准版本为不可变快照，文档退回草稿。

        单事务内完成：快照旧版本 -> 状态 APPROVED->DRAFT -> 次版本进位 -> 审计。
        历史版本与其电子签名保持不变、永久保留。
        """
        if not change_reason or not change_reason.strip():
            raise BusinessError("发起变更必须填写变更原因")

        document = await self.get_document(document_id)
        if document.status != DocumentStatus.APPROVED:
            raise BusinessError("只有已批准的文档可以发起变更")

        # 冻结当前已批准版本为不可变快照（保留其原始版本标签）
        result = await self.db.execute(
            select(func.max(DocumentVersion.version_number)).where(
                DocumentVersion.document_id == document_id
            )
        )
        max_version = result.scalar() or 0
        self.db.add(DocumentVersion(
            document_id=document_id,
            version_number=max_version + 1,
            version_label=document.version,
            content=document.content,
            change_reason=change_reason,
            created_by=user_id,
        ))

        # 打破之前状态：活动文档退回草稿，次版本进位
        old_status = document.status.value
        approved_version = document.version  # 被取代的已批准版本标签（如 "1.0"）
        document.status = DocumentStatus.DRAFT
        document.version = bump_minor_version(document.version)
        document.updated_at = datetime.now(timezone.utc)

        # 审计轨迹：显式记录「批准状态被破坏」（同事务）
        audit = AuditService(self.db)
        await audit.record(
            DocumentRevised(
                document_id=document_id,
                old_status=old_status,
                new_status=DocumentStatus.DRAFT.value,
                change_reason=change_reason,
            ),
            actor=user_id,
            ip_address=ip_address,
        )

        # 审计轨迹：为被取代的每条电子签名各记一条「签名失效」（不销毁签名，is_valid 保持 True）
        # 签名以其所属的已批准工作流为准（签名写入时版本尚未进位，故按 workflow_id 匹配最可靠）
        approved_wf_id = (await self.db.execute(
            select(Workflow.id)
            .where(
                Workflow.document_id == document_id,
                Workflow.status == WorkflowStatus.APPROVED,
            )
            .order_by(Workflow.completed_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        voided_sigs = []
        if approved_wf_id:
            voided_sigs = (await self.db.execute(
                select(ElectronicSignature).where(
                    ElectronicSignature.workflow_id == approved_wf_id
                )
            )).scalars().all()
        await audit.record(
            SignaturesVoided(
                document_id=document_id,
                approved_version=approved_version,
                change_reason=change_reason,
                signatures=tuple(
                    VoidedSignature(
                        signature_id=sig.id,
                        signer_name=sig.user.full_name if sig.user else sig.user_id,
                        meaning=sig.meaning,
                    )
                    for sig in voided_sigs
                ),
            ),
            actor=user_id,
            ip_address=ip_address,
        )

        # 不提交：版本快照、状态跃迁与两类审计轨迹必须同生共死
        # （ADR-0002、ADR-0003、ADR-0004）
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def get_versions(self, document_id: str) -> list[DocumentVersion]:
        """获取文档版本历史."""
        result = await self.db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def delete_document(
        self, document_id: str, user_id: str, ip_address: str | None = None
    ) -> None:
        """删除文档（仅草稿状态可删除）."""
        document = await self.get_document(document_id)

        if document.status != DocumentStatus.DRAFT:
            raise BusinessError("只有草稿状态的文档可以删除")
        if document.author_id != user_id:
            raise BusinessError("只有文档作者可以删除文档")

        # 审计先于删除：删掉之后就取不到编号与标题了
        await AuditService(self.db).record(
            DocumentDeleted(
                document_id=document_id,
                doc_number=document.doc_number,
                title=document.title,
            ),
            actor=user_id,
            ip_address=ip_address,
        )

        await self.db.delete(document)
        # 不提交：事务归属在请求 seam 上（ADR-0004）
        await self.db.flush()

    async def _require_document_manage_permission(
        self, document: Document, user: User
    ) -> None:
        """校验用户具备维护该文档 URS 条目/引用的权限.

        系统管理员直接放行；有 `project_id` 时委托 `ProjectService` 校验
        `project.documents.manage` 权限；`project_id` 为空（全局文档）时仅
        系统管理员可维护，其余用户一律拒绝。
        """
        if user_has_role(user, "admin"):
            return

        if document.project_id:
            project_service = ProjectService(self.db, is_admin=False)
            permissions = await project_service.get_current_user_permissions(
                document.project_id, user.id
            )
            if "project.documents.manage" not in permissions:
                raise PermissionDeniedError("权限不足，无法维护该文档的 URS 条目/引用")
        else:
            raise PermissionDeniedError("权限不足，无法维护该文档的 URS 条目/引用")

    async def _require_urs_document_draft(
        self, document_id: str, user: User
    ) -> Document:
        """获取 URS 文档并校验权限、类型、状态，供条目维护方法复用.

        校验顺序：文档存在 → 权限 → 类型为 URS → 状态为草稿。
        """
        document = await self.get_document(document_id)
        await self._require_document_manage_permission(document, user)

        if document.doc_type != DocumentType.URS:
            raise BusinessError("仅 URS 类型文档可维护条目")
        if document.status != DocumentStatus.DRAFT:
            raise BusinessError("只有草稿状态的 URS 文档可以维护条目")

        return document

    async def _get_urs_item(self, document_id: str, item_id: str) -> URSItem:
        """获取指定 URS 文档下的条目，不存在则抛出 BusinessError."""
        result = await self.db.execute(
            select(URSItem).where(
                URSItem.id == item_id, URSItem.document_id == document_id
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise BusinessError("URS 条目不存在", status_code=404)
        return item

    async def create_urs_item(
        self,
        document_id: str,
        data: URSItemCreate,
        user: User,
        ip_address: str | None = None,
    ) -> URSItem:
        """新增 URS 条目（自动生成 item_code）."""
        document = await self._require_urs_document_draft(document_id, user)

        description = data.description
        if not description or not description.strip():
            raise BusinessError("条目描述不能为空")

        for attempt in range(self._MAX_ITEM_CODE_RETRIES):
            item_code = await self._generate_item_code(document_id, document.doc_number)

            item = URSItem(
                document_id=document_id,
                item_code=item_code,
                description=description,
                created_by=user.id,
            )
            # 用 savepoint 圈住这次尝试：编号冲突只回滚这一次插入，不动本请求
            # 已暂存的其余工作（ADR-0004）。add 必须在 savepoint 内，回滚时
            # 待插入的对象才会被一并撤销。
            try:
                async with self.db.begin_nested():
                    self.db.add(item)
                    await self.db.flush()
                break
            except IntegrityError:
                if attempt == self._MAX_ITEM_CODE_RETRIES - 1:
                    raise BusinessError("条目编号生成冲突，请重试")

        await AuditService(self.db).record(
            UrsItemAdded(document_id=document_id, item_code=item.item_code),
            actor=user,
            ip_address=ip_address,
        )

        # 不提交：事务归属在请求 seam 上（ADR-0004）
        await self.db.refresh(item)
        return item

    async def list_urs_items(self, document_id: str) -> list[URSItem]:
        """获取指定文档下的 URS 条目列表."""
        await self.get_document(document_id)

        result = await self.db.execute(
            select(URSItem)
            .where(URSItem.document_id == document_id)
            .order_by(URSItem.item_code.asc())
        )
        return list(result.scalars().all())

    async def update_urs_item(
        self,
        document_id: str,
        item_id: str,
        data: URSItemUpdate,
        user: User,
        ip_address: str | None = None,
    ) -> URSItem:
        """更新 URS 条目（item_code 不可修改）."""
        await self._require_urs_document_draft(document_id, user)
        item = await self._get_urs_item(document_id, item_id)

        old_description = item.description
        if data.description is not None:
            if not data.description.strip():
                raise BusinessError("条目描述不能为空")
            item.description = data.description

        item.updated_at = datetime.now(timezone.utc)

        if item.description != old_description:
            await AuditService(self.db).record(
                UrsItemDescriptionChanged(
                    document_id=document_id,
                    item_code=item.item_code,
                    old_value=old_description,
                    new_value=item.description,
                ),
                actor=user,
                ip_address=ip_address,
            )

        # 不提交：事务归属在请求 seam 上（ADR-0004）
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def delete_urs_item(
        self,
        document_id: str,
        item_id: str,
        user: User,
        ip_address: str | None = None,
    ) -> None:
        """删除 URS 条目.

        校验顺序：文档存在 → 权限 → 类型为 URS → 状态为草稿 → 条目存在 →
        不存在任何引用该条目的 URS_Reference。
        """
        await self._require_urs_document_draft(document_id, user)
        item = await self._get_urs_item(document_id, item_id)

        result = await self.db.execute(
            select(func.count()).where(URSReference.urs_item_id == item_id)
        )
        ref_count = result.scalar() or 0
        if ref_count > 0:
            raise BusinessError("该条目已被引用，无法删除")

        # 审计先于删除：删掉之后就取不到条目编号了
        await AuditService(self.db).record(
            UrsItemRemoved(document_id=document_id, item_code=item.item_code),
            actor=user,
            ip_address=ip_address,
        )

        await self.db.delete(item)
        # 不提交：事务归属在请求 seam 上（ADR-0004）
        await self.db.flush()

    _REFERENCING_DOC_TYPES = {
        DocumentType.FS,
        DocumentType.DS,
        DocumentType.IQ,
        DocumentType.OQ,
        DocumentType.PQ,
    }

    async def create_urs_reference(
        self,
        ref_document_id: str,
        data: URSReferenceCreate,
        user: User,
        ip_address: str | None = None,
    ) -> URSReference:
        """新增 URS 引用.

        校验顺序：文档存在 → 权限 → 引用文档类型属于 {FS,DS,IQ,OQ,PQ} →
        状态为草稿 → 条目存在 → 项目一致 → 不重复。
        """
        ref_document = await self.get_document(ref_document_id)
        await self._require_document_manage_permission(ref_document, user)

        if ref_document.doc_type not in self._REFERENCING_DOC_TYPES:
            raise BusinessError("仅 FS/DS/IQ/OQ/PQ 类型文档可关联 URS 条目")
        if ref_document.status != DocumentStatus.DRAFT:
            raise BusinessError("只有草稿状态的文档可以关联 URS 条目")

        result = await self.db.execute(
            select(URSItem).where(URSItem.id == data.urs_item_id)
        )
        urs_item = result.scalar_one_or_none()
        if not urs_item:
            raise BusinessError("所选 URS 条目不存在")

        urs_document = await self.get_document(urs_item.document_id)
        if urs_document.project_id != ref_document.project_id:
            raise BusinessError("不能引用其他项目的 URS 条目")

        result = await self.db.execute(
            select(URSReference).where(
                URSReference.document_id == ref_document_id,
                URSReference.urs_item_id == data.urs_item_id,
            )
        )
        if result.scalar_one_or_none() is not None:
            raise BusinessError("该条目已被本文档引用")

        reference = URSReference(
            document_id=ref_document_id,
            urs_item_id=data.urs_item_id,
            created_by=user.id,
        )
        self.db.add(reference)
        # 不提交：事务归属在请求 seam 上（ADR-0004）
        await self.db.flush()

        await AuditService(self.db).record(
            UrsReferenceAdded(
                document_id=ref_document_id, item_code=urs_item.item_code
            ),
            actor=user,
            ip_address=ip_address,
        )

        await self.db.refresh(reference)
        return reference

    async def _get_urs_reference(
        self, ref_document_id: str, reference_id: str
    ) -> URSReference:
        """获取指定文档下的 URS 引用记录，不存在则抛出 BusinessError."""
        result = await self.db.execute(
            select(URSReference).where(
                URSReference.id == reference_id,
                URSReference.document_id == ref_document_id,
            )
        )
        reference = result.scalar_one_or_none()
        if not reference:
            raise BusinessError("URS 引用不存在", status_code=404)
        return reference

    async def delete_urs_reference(
        self,
        ref_document_id: str,
        reference_id: str,
        user: User,
        ip_address: str | None = None,
    ) -> None:
        """删除 URS 引用.

        校验顺序：文档存在 → 权限 → 状态为草稿 → 引用记录存在。
        精确按 id 删除，不影响该文档或其他文档的其余引用记录。
        """
        ref_document = await self.get_document(ref_document_id)
        await self._require_document_manage_permission(ref_document, user)

        if ref_document.status != DocumentStatus.DRAFT:
            raise BusinessError("只有草稿状态的文档可以删除 URS 引用")

        reference = await self._get_urs_reference(ref_document_id, reference_id)

        # 审计先于删除：删掉之后就取不到被引用条目的编号了
        await AuditService(self.db).record(
            UrsReferenceRemoved(
                document_id=ref_document_id,
                item_code=reference.urs_item.item_code
                if reference.urs_item
                else reference.urs_item_id,
            ),
            actor=user,
            ip_address=ip_address,
        )

        await self.db.delete(reference)
        # 不提交：事务归属在请求 seam 上（ADR-0004）
        await self.db.flush()

    async def list_urs_references(self, ref_document_id: str) -> list[URSReference]:
        """获取指定文档下的 URS 引用列表."""
        await self.get_document(ref_document_id)

        result = await self.db.execute(
            select(URSReference)
            .where(URSReference.document_id == ref_document_id)
            .order_by(URSReference.created_at.asc())
        )
        return list(result.scalars().all())

    async def count_urs_references(self, ref_document_id: str) -> int:
        """统计指定文档下的 URS 引用数量（供 Workflow_Service 提交前校验复用）."""
        result = await self.db.execute(
            select(func.count()).where(URSReference.document_id == ref_document_id)
        )
        return result.scalar() or 0

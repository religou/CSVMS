"""文档服务 - CRUD 和版本管理."""

from datetime import datetime, timezone

from sqlalchemy import Integer, select, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError, PermissionDeniedError
from app.models.document import Document, DocumentVersion, DocumentStatus, DocumentType
from app.models.urs import URSItem, URSReference
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.schemas.urs import URSItemCreate, URSItemUpdate, URSReferenceCreate
from app.services.permission_service import user_has_role
from app.services.project_service import ProjectService


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
        self, data: DocumentCreate, author_id: str
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
        await self.db.commit()
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

    async def update_document(
        self, document_id: str, data: DocumentUpdate, user_id: str
    ) -> Document:
        """更新文档内容（仅草稿状态可编辑）."""
        document = await self.get_document(document_id)

        if document.status != DocumentStatus.DRAFT:
            raise BusinessError("只有草稿状态的文档可以编辑")

        if data.title is not None:
            document.title = data.title
        if data.content is not None:
            document.content = data.content
        if data.summary is not None:
            document.summary = data.summary

        document.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def create_version_snapshot(
        self, document_id: str, user_id: str, change_reason: str | None = None
    ) -> DocumentVersion:
        """创建文档版本快照（提交审核时自动调用）."""
        document = await self.get_document(document_id)

        # 计算新版本号
        result = await self.db.execute(
            select(func.max(DocumentVersion.version_number)).where(
                DocumentVersion.document_id == document_id
            )
        )
        max_version = result.scalar() or 0
        new_version_number = max_version + 1

        # 主版本号在批准后递增，次版本号在提交审核时递增
        major = new_version_number
        version_label = f"{major}.0"

        version = DocumentVersion(
            document_id=document_id,
            version_number=new_version_number,
            version_label=version_label,
            content=document.content,
            change_reason=change_reason,
            created_by=user_id,
        )
        self.db.add(version)

        # 更新文档版本号
        document.version = version_label
        await self.db.commit()
        await self.db.refresh(version)
        return version

    async def get_versions(self, document_id: str) -> list[DocumentVersion]:
        """获取文档版本历史."""
        result = await self.db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def delete_document(self, document_id: str, user_id: str) -> None:
        """删除文档（仅草稿状态可删除）."""
        document = await self.get_document(document_id)

        if document.status != DocumentStatus.DRAFT:
            raise BusinessError("只有草稿状态的文档可以删除")
        if document.author_id != user_id:
            raise BusinessError("只有文档作者可以删除文档")

        await self.db.delete(document)
        await self.db.commit()

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
        self, document_id: str, data: URSItemCreate, user: User
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
            self.db.add(item)
            try:
                await self.db.flush()
                break
            except IntegrityError:
                await self.db.rollback()
                if attempt == self._MAX_ITEM_CODE_RETRIES - 1:
                    raise BusinessError("条目编号生成冲突，请重试")

        await self.db.commit()
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
        self, document_id: str, item_id: str, data: URSItemUpdate, user: User
    ) -> URSItem:
        """更新 URS 条目（item_code 不可修改）."""
        await self._require_urs_document_draft(document_id, user)
        item = await self._get_urs_item(document_id, item_id)

        if data.description is not None:
            if not data.description.strip():
                raise BusinessError("条目描述不能为空")
            item.description = data.description

        item.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_urs_item(
        self, document_id: str, item_id: str, user: User
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

        await self.db.delete(item)
        await self.db.commit()

    _REFERENCING_DOC_TYPES = {
        DocumentType.FS,
        DocumentType.DS,
        DocumentType.IQ,
        DocumentType.OQ,
        DocumentType.PQ,
    }

    async def create_urs_reference(
        self, ref_document_id: str, data: URSReferenceCreate, user: User
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
        await self.db.commit()
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
        self, ref_document_id: str, reference_id: str, user: User
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

        await self.db.delete(reference)
        await self.db.commit()

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

"""文档服务 - CRUD 和版本管理."""

from datetime import datetime, timezone

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.document import Document, DocumentVersion, DocumentStatus, DocumentType
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentUpdate


class DocumentService:
    """验证文档服务."""

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

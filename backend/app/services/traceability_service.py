"""追溯矩阵服务."""

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.document import Document, DocumentType
from app.models.traceability import TraceLink


# 标准追溯链：URS → FS → DS → IQ/OQ/PQ
TRACE_CHAIN = {
    "URS": ["FS"],
    "FS": ["DS"],
    "DS": ["IQ", "OQ", "PQ"],
}


class TraceabilityService:
    """追溯矩阵服务."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_link(
        self,
        source_document_id: str,
        target_document_id: str,
        created_by: str,
        source_section: str | None = None,
        target_section: str | None = None,
        link_type: str = "traces_to",
        description: str | None = None,
    ) -> TraceLink:
        """创建追溯关系."""
        # 验证文档存在
        source = await self.db.get(Document, source_document_id)
        if not source:
            raise BusinessError("源文档不存在")
        target = await self.db.get(Document, target_document_id)
        if not target:
            raise BusinessError("目标文档不存在")

        if source_document_id == target_document_id:
            raise BusinessError("不能创建自身的追溯关系")

        # 检查重复
        existing = await self.db.execute(
            select(TraceLink).where(
                TraceLink.source_document_id == source_document_id,
                TraceLink.target_document_id == target_document_id,
            )
        )
        if existing.scalar_one_or_none():
            raise BusinessError("追溯关系已存在")

        link = TraceLink(
            source_document_id=source_document_id,
            target_document_id=target_document_id,
            source_section=source_section,
            target_section=target_section,
            link_type=link_type,
            description=description,
            created_by=created_by,
        )
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def delete_link(self, link_id: str) -> None:
        """删除追溯关系."""
        link = await self.db.get(TraceLink, link_id)
        if not link:
            raise BusinessError("追溯关系不存在")
        await self.db.delete(link)
        await self.db.commit()

    async def get_links_for_document(self, document_id: str) -> dict:
        """获取文档的上下游追溯关系."""
        # 作为源的（下游）
        downstream_result = await self.db.execute(
            select(TraceLink).where(TraceLink.source_document_id == document_id)
        )
        downstream = list(downstream_result.scalars().all())

        # 作为目标的（上游）
        upstream_result = await self.db.execute(
            select(TraceLink).where(TraceLink.target_document_id == document_id)
        )
        upstream = list(upstream_result.scalars().all())

        return {"upstream": upstream, "downstream": downstream}

    async def get_matrix(self, system_name: str | None = None) -> dict:
        """获取完整追溯矩阵 + 覆盖率统计."""
        # 获取所有相关文档
        doc_query = select(Document)
        if system_name:
            doc_query = doc_query.where(Document.system_name == system_name)
        doc_result = await self.db.execute(doc_query)
        documents = list(doc_result.scalars().all())

        doc_map = {d.id: d for d in documents}
        doc_ids = list(doc_map.keys())

        # 获取所有链接
        link_result = await self.db.execute(
            select(TraceLink).where(
                TraceLink.source_document_id.in_(doc_ids) | TraceLink.target_document_id.in_(doc_ids)
            )
        )
        links = list(link_result.scalars().all())

        # 按文档类型分组
        by_type: dict[str, list] = {}
        for doc in documents:
            dt = doc.doc_type.value if hasattr(doc.doc_type, 'value') else doc.doc_type
            by_type.setdefault(dt, []).append(doc)

        # 计算覆盖率
        coverage = {}
        for src_type, expected_targets in TRACE_CHAIN.items():
            src_docs = by_type.get(src_type, [])
            if not src_docs:
                continue

            covered = 0
            for src_doc in src_docs:
                has_link = any(
                    link.source_document_id == src_doc.id
                    for link in links
                )
                if has_link:
                    covered += 1

            coverage[src_type] = {
                "total": len(src_docs),
                "covered": covered,
                "rate": round(covered / len(src_docs) * 100, 1) if src_docs else 0,
                "expected_targets": expected_targets,
            }

        # Gap analysis - 未覆盖的文档
        gaps = []
        for src_type, expected_targets in TRACE_CHAIN.items():
            for src_doc in by_type.get(src_type, []):
                linked_targets = [
                    link.target_document_id for link in links
                    if link.source_document_id == src_doc.id
                ]
                if not linked_targets:
                    gaps.append({
                        "document_id": src_doc.id,
                        "doc_number": src_doc.doc_number,
                        "title": src_doc.title,
                        "doc_type": src_type,
                        "missing_targets": expected_targets,
                    })

        return {
            "documents": documents,
            "links": links,
            "coverage": coverage,
            "gaps": gaps,
        }

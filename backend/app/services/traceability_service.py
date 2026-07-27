"""追溯矩阵服务."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.urs import URSItem, URSReference


class TraceabilityService:
    """追溯矩阵服务（以 URS 条目覆盖关系为核心）."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_matrix(self, project_id: str | None = None) -> dict:
        """获取以 URS 条目为核心的覆盖追溯矩阵（可选按项目范围隔离）.

        追溯关系以 URS_Item → Referencing_Document（FS/DS/IQ/OQ/PQ）的引用为基础，
        而非文档间的 TraceLink。矩阵每一行对应一个 URS_Item，列出引用（覆盖）该条目
        的下游文档集合。
        """
        # 获取当前范围内的所有文档，用于解析条目所属 URS 文档与引用文档的展示信息。
        doc_query = select(Document)
        if project_id:
            doc_query = doc_query.where(Document.project_id == project_id)
        doc_result = await self.db.execute(doc_query)
        documents = list(doc_result.scalars().all())

        doc_map = {d.id: d for d in documents}

        # 按文档类型分组，取出 URS 文档及其条目。
        by_type: dict[str, list] = {}
        for doc in documents:
            dt = doc.doc_type.value if hasattr(doc.doc_type, "value") else doc.doc_type
            by_type.setdefault(dt, []).append(doc)

        urs_docs = by_type.get("URS", [])
        urs_doc_ids = [d.id for d in urs_docs]

        urs_items: list[URSItem] = []
        if urs_doc_ids:
            item_result = await self.db.execute(
                select(URSItem).where(URSItem.document_id.in_(urs_doc_ids))
            )
            urs_items = list(item_result.scalars().all())

        urs_item_ids = [item.id for item in urs_items]

        # 查询引用这些条目的记录，并按条目聚合引用文档。
        refs_by_item: dict[str, list[str]] = {}
        ref_doc_ids: set[str] = set()
        if urs_item_ids:
            ref_result = await self.db.execute(
                select(URSReference).where(URSReference.urs_item_id.in_(urs_item_ids))
            )
            for ref in ref_result.scalars().all():
                refs_by_item.setdefault(ref.urs_item_id, []).append(ref.document_id)
                ref_doc_ids.add(ref.document_id)

        # 引用文档可能不在当前项目范围文档集合中，补齐其展示信息。
        missing_doc_ids = [rid for rid in ref_doc_ids if rid not in doc_map]
        if missing_doc_ids:
            missing_result = await self.db.execute(
                select(Document).where(Document.id.in_(missing_doc_ids))
            )
            for doc in missing_result.scalars().all():
                doc_map[doc.id] = doc

        def _doc_type_value(doc: Document) -> str:
            return doc.doc_type.value if hasattr(doc.doc_type, "value") else doc.doc_type

        # 构建以 URS 条目为核心的覆盖追溯矩阵。
        urs_matrix = []
        for item in urs_items:
            referencing_doc_ids = refs_by_item.get(item.id, [])
            references = [
                {
                    "document_id": rid,
                    "doc_number": doc_map[rid].doc_number,
                    "title": doc_map[rid].title,
                    "doc_type": _doc_type_value(doc_map[rid]),
                }
                for rid in referencing_doc_ids
                if rid in doc_map
            ]
            urs_matrix.append(
                {
                    "urs_item_id": item.id,
                    "item_code": item.item_code,
                    "description": item.description,
                    "source_document_id": item.document_id,
                    "source_doc_number": doc_map[item.document_id].doc_number,
                    "covered": len(references) > 0,
                    "references": references,
                }
            )

        uncovered_urs_items = [
            {
                "id": item.id,
                "item_code": item.item_code,
                "description": item.description,
            }
            for item in urs_items
            if not refs_by_item.get(item.id)
        ]

        return {
            "documents": documents,
            "urs_matrix": urs_matrix,
            "uncovered_urs_items": uncovered_urs_items,
        }

"""仪表板统计服务."""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.workflow import Workflow, WorkflowStatus, WorkflowStep, StepStatus
from app.models.signature import ElectronicSignature


class DashboardService:
    """仪表板统计."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _count_by(
        self, column, group_col, project_id: str | None = None
    ) -> dict[str, int]:
        """通用分组计数（可选按项目过滤）."""
        query = select(group_col, func.count(column))
        if project_id:
            query = query.where(Document.project_id == project_id)
        query = query.group_by(group_col)
        result = await self.db.execute(query)
        return {
            (row[0].value if hasattr(row[0], 'value') else row[0]): row[1]
            for row in result.all()
        }

    async def get_stats(
        self, user_id: str | None = None, project_id: str | None = None
    ) -> dict:
        """获取总览统计（按项目范围隔离）."""
        doc_count_query = select(func.count(Document.id))
        if project_id:
            doc_count_query = doc_count_query.where(
                Document.project_id == project_id
            )
        total_docs_result = await self.db.execute(doc_count_query)
        total_docs = total_docs_result.scalar() or 0

        status_distribution = await self._count_by(
            Document.id, Document.status, project_id
        )
        type_distribution = await self._count_by(
            Document.id, Document.doc_type, project_id
        )

        workflow_query = select(Workflow.status, func.count(Workflow.id))
        if project_id:
            workflow_query = workflow_query.join(
                Document, Workflow.document_id == Document.id
            ).where(Document.project_id == project_id)
        workflow_query = workflow_query.group_by(Workflow.status)
        workflow_result = await self.db.execute(workflow_query)
        workflow_stats = {
            (row[0].value if hasattr(row[0], 'value') else row[0]): row[1]
            for row in workflow_result.all()
        }

        # 待办事项（用户相关）
        pending_count = 0
        my_drafts = 0
        if user_id:
            # 我的待审批
            pending_query = select(func.count(WorkflowStep.id)).where(
                WorkflowStep.assignee_id == user_id,
                WorkflowStep.status == StepStatus.IN_PROGRESS,
            )
            if project_id:
                pending_query = pending_query.join(
                    Workflow, WorkflowStep.workflow_id == Workflow.id
                ).join(Document, Workflow.document_id == Document.id).where(
                    Document.project_id == project_id
                )
            pending_result = await self.db.execute(pending_query)
            pending_count = pending_result.scalar() or 0

            # 我的草稿
            draft_query = select(func.count(Document.id)).where(
                Document.author_id == user_id,
                Document.status == DocumentStatus.DRAFT,
            )
            if project_id:
                draft_query = draft_query.where(Document.project_id == project_id)
            draft_result = await self.db.execute(draft_query)
            my_drafts = draft_result.scalar() or 0

        # 签名统计
        sig_query = select(func.count(ElectronicSignature.id))
        if project_id:
            sig_query = sig_query.join(
                Document, ElectronicSignature.document_id == Document.id
            ).where(Document.project_id == project_id)
        sig_result = await self.db.execute(sig_query)
        total_signatures = sig_result.scalar() or 0

        return {
            "total_documents": total_docs,
            "status_distribution": status_distribution,
            "type_distribution": type_distribution,
            "workflow_stats": workflow_stats,
            "pending_approvals": pending_count,
            "my_drafts": my_drafts,
            "total_signatures": total_signatures,
        }

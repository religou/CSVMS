"""仪表板统计服务."""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.workflow import Workflow, WorkflowStatus, WorkflowStep, StepStatus
from app.models.signature import ElectronicSignature
from app.models.audit_log import AuditLog


class DashboardService:
    """仪表板统计."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _count_by(self, column, group_col) -> dict[str, int]:
        """通用分组计数."""
        result = await self.db.execute(
            select(group_col, func.count(column)).group_by(group_col)
        )
        return {
            (row[0].value if hasattr(row[0], 'value') else row[0]): row[1]
            for row in result.all()
        }

    async def get_stats(self, user_id: str | None = None) -> dict:
        """获取总览统计."""
        total_docs_result = await self.db.execute(select(func.count(Document.id)))
        total_docs = total_docs_result.scalar() or 0

        status_distribution = await self._count_by(Document.id, Document.status)
        type_distribution = await self._count_by(Document.id, Document.doc_type)
        workflow_stats = await self._count_by(Workflow.id, Workflow.status)

        # 待办事项（用户相关）
        pending_count = 0
        my_drafts = 0
        if user_id:
            # 我的待审批
            pending_result = await self.db.execute(
                select(func.count(WorkflowStep.id)).where(
                    WorkflowStep.assignee_id == user_id,
                    WorkflowStep.status == StepStatus.IN_PROGRESS,
                )
            )
            pending_count = pending_result.scalar() or 0

            # 我的草稿
            draft_result = await self.db.execute(
                select(func.count(Document.id)).where(
                    Document.author_id == user_id,
                    Document.status == DocumentStatus.DRAFT,
                )
            )
            my_drafts = draft_result.scalar() or 0

        # 签名统计
        sig_result = await self.db.execute(select(func.count(ElectronicSignature.id)))
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

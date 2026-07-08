"""审批工作流服务 - 状态机引擎."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessError
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.workflow import (
    ActionType,
    StepStatus,
    StepType,
    Workflow,
    WorkflowAction,
    WorkflowStatus,
    WorkflowStep,
    WorkflowTemplate,
    WorkflowTemplateStep,
)
from app.services.document_service import DocumentService


class WorkflowService:
    """审批工作流引擎."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- 工作流模板 ----------

    async def create_template(
        self,
        name: str,
        doc_type: str,
        steps: list[dict],
        description: str | None = None,
        created_by: str = "",
    ) -> WorkflowTemplate:
        """创建工作流模板."""
        template = WorkflowTemplate(
            name=name,
            doc_type=doc_type,
            description=description,
            created_by=created_by,
        )
        self.db.add(template)
        await self.db.flush()

        for i, step_data in enumerate(steps, start=1):
            step = WorkflowTemplateStep(
                template_id=template.id,
                step_order=i,
                name=step_data["name"],
                step_type=step_data["step_type"],
                role_id=step_data.get("role_id"),
                assignee_id=step_data.get("assignee_id"),
                project_role=step_data.get("project_role"),
            )
            self.db.add(step)

        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def update_template(
        self,
        template_id: str,
        name: str | None = None,
        doc_type: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
        steps: list[dict] | None = None,
    ) -> WorkflowTemplate:
        """更新工作流模板."""
        template = await self.get_template(template_id)

        if name is not None:
            template.name = name
        if doc_type is not None:
            template.doc_type = doc_type
        if description is not None:
            template.description = description
        if is_active is not None:
            template.is_active = is_active

        if steps is not None:
            # 全量替换步骤
            for old_step in list(template.steps):
                await self.db.delete(old_step)
            await self.db.flush()

            for i, step_data in enumerate(steps, start=1):
                step = WorkflowTemplateStep(
                    template_id=template.id,
                    step_order=i,
                    name=step_data["name"],
                    step_type=step_data["step_type"],
                    role_id=step_data.get("role_id"),
                    assignee_id=step_data.get("assignee_id"),
                    project_role=step_data.get("project_role"),
                )
                self.db.add(step)

        await self.db.commit()
        return await self.get_template(template_id)

    async def get_template(self, template_id: str) -> WorkflowTemplate:
        """获取工作流模板."""
        result = await self.db.execute(
            select(WorkflowTemplate)
            .options(selectinload(WorkflowTemplate.steps))
            .where(WorkflowTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if not template:
            raise BusinessError("工作流模板不存在")
        return template

    async def get_template_for_doc_type(self, doc_type: str) -> WorkflowTemplate | None:
        """获取某文档类型的活动模板."""
        result = await self.db.execute(
            select(WorkflowTemplate)
            .options(selectinload(WorkflowTemplate.steps))
            .where(
                WorkflowTemplate.doc_type == doc_type,
                WorkflowTemplate.is_active == True,  # noqa: E712
            )
            .order_by(WorkflowTemplate.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_templates(self) -> list[WorkflowTemplate]:
        """获取所有工作流模板."""
        result = await self.db.execute(
            select(WorkflowTemplate)
            .options(selectinload(WorkflowTemplate.steps))
            .order_by(WorkflowTemplate.created_at.desc())
        )
        return list(result.scalars().all())

    # ---------- 工作流实例 - 提交审批 ----------

    async def submit_document(self, document_id: str, submitter_id: str) -> Workflow:
        """提交文档进入审批流程."""
        # 获取文档
        doc = await self.db.get(Document, document_id)
        if not doc:
            raise BusinessError("文档不存在")
        if doc.status != DocumentStatus.DRAFT:
            raise BusinessError("只有草稿状态的文档可以提交审核")
        if doc.author_id != submitter_id:
            raise BusinessError("只有文档作者可以提交审核")

        # 检查是否已有进行中的工作流
        existing = await self.db.execute(
            select(Workflow).where(
                Workflow.document_id == document_id,
                Workflow.status.in_([WorkflowStatus.PENDING, WorkflowStatus.IN_PROGRESS]),
            )
        )
        if existing.scalar_one_or_none():
            raise BusinessError("该文档已有进行中的审批流程")

        # URS 引用数量校验：FS/DS/IQ/OQ/PQ 文档提交审批前必须已关联至少一个 URS 条目
        if doc.doc_type in {
            DocumentType.FS,
            DocumentType.DS,
            DocumentType.IQ,
            DocumentType.OQ,
            DocumentType.PQ,
        }:
            ref_count = await DocumentService(self.db).count_urs_references(document_id)
            if ref_count == 0:
                raise BusinessError("文档尚未关联任何 URS 条目，无法提交审批")

        # 获取该文档类型的工作流模板
        template = await self.get_template_for_doc_type(doc.doc_type.value)
        if not template:
            raise BusinessError(f"文档类型 {doc.doc_type.value} 未配置审批流程模板")
        if not template.steps:
            raise BusinessError("审批流程模板没有配置步骤")

        # 创建工作流实例
        workflow = Workflow(
            template_id=template.id,
            document_id=document_id,
            status=WorkflowStatus.IN_PROGRESS,
            current_step_order=1,
            initiated_by=submitter_id,
        )
        self.db.add(workflow)
        await self.db.flush()

        # 从模板创建步骤实例
        for tmpl_step in template.steps:
            step = WorkflowStep(
                workflow_id=workflow.id,
                step_order=tmpl_step.step_order,
                name=tmpl_step.name,
                step_type=tmpl_step.step_type,
                status=StepStatus.IN_PROGRESS if tmpl_step.step_order == 1 else StepStatus.PENDING,
                assignee_id=tmpl_step.assignee_id,
            )
            self.db.add(step)

        # 记录提交动作
        action = WorkflowAction(
            workflow_id=workflow.id,
            action=ActionType.SUBMIT,
            actor_id=submitter_id,
            comment="提交文档审核",
        )
        self.db.add(action)

        # 更新文档状态
        doc.status = DocumentStatus.UNDER_REVIEW
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    # ---------- 审批操作 ----------

    async def approve_step(self, workflow_id: str, actor_id: str, comment: str | None = None) -> Workflow:
        """批准当前步骤."""
        workflow = await self._get_workflow(workflow_id)
        self._validate_workflow_active(workflow)

        current_step = self._get_current_step(workflow)
        self._validate_actor(current_step, actor_id)

        # 更新步骤状态
        current_step.status = StepStatus.APPROVED
        current_step.acted_by = actor_id
        current_step.acted_at = datetime.now(timezone.utc)
        current_step.comment = comment

        # 记录动作
        self.db.add(WorkflowAction(
            workflow_id=workflow_id,
            step_id=current_step.id,
            action=ActionType.APPROVE,
            actor_id=actor_id,
            comment=comment,
        ))

        # 进入下一步或完成
        next_step = self._get_next_step(workflow)
        if next_step:
            next_step.status = StepStatus.IN_PROGRESS
            workflow.current_step_order = next_step.step_order
        else:
            # 所有步骤完成 → 工作流完成
            workflow.status = WorkflowStatus.APPROVED
            workflow.completed_at = datetime.now(timezone.utc)
            # 更新文档状态
            doc = await self.db.get(Document, workflow.document_id)
            if doc:
                doc.status = DocumentStatus.APPROVED

        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def reject_step(self, workflow_id: str, actor_id: str, comment: str) -> Workflow:
        """拒绝当前步骤 - 终止流程."""
        if not comment:
            raise BusinessError("拒绝审批必须填写意见")

        workflow = await self._get_workflow(workflow_id)
        self._validate_workflow_active(workflow)

        current_step = self._get_current_step(workflow)
        self._validate_actor(current_step, actor_id)

        # 更新步骤状态
        current_step.status = StepStatus.REJECTED
        current_step.acted_by = actor_id
        current_step.acted_at = datetime.now(timezone.utc)
        current_step.comment = comment

        # 终止工作流
        workflow.status = WorkflowStatus.REJECTED
        workflow.completed_at = datetime.now(timezone.utc)

        # 记录动作
        self.db.add(WorkflowAction(
            workflow_id=workflow_id,
            step_id=current_step.id,
            action=ActionType.REJECT,
            actor_id=actor_id,
            comment=comment,
        ))

        # 文档退回草稿
        doc = await self.db.get(Document, workflow.document_id)
        if doc:
            doc.status = DocumentStatus.DRAFT

        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def return_step(self, workflow_id: str, actor_id: str, comment: str) -> Workflow:
        """退回到上一步或起草人."""
        if not comment:
            raise BusinessError("退回审批必须填写意见")

        workflow = await self._get_workflow(workflow_id)
        self._validate_workflow_active(workflow)

        current_step = self._get_current_step(workflow)
        self._validate_actor(current_step, actor_id)

        # 记录退回动作
        self.db.add(WorkflowAction(
            workflow_id=workflow_id,
            step_id=current_step.id,
            action=ActionType.RETURN,
            actor_id=actor_id,
            comment=comment,
        ))

        # 退回到第一步或起草人
        if workflow.current_step_order == 1:
            # 第一步退回 = 退回给起草人
            current_step.status = StepStatus.REJECTED
            current_step.acted_by = actor_id
            current_step.acted_at = datetime.now(timezone.utc)
            current_step.comment = comment

            workflow.status = WorkflowStatus.REJECTED
            workflow.completed_at = datetime.now(timezone.utc)

            doc = await self.db.get(Document, workflow.document_id)
            if doc:
                doc.status = DocumentStatus.DRAFT
        else:
            # 退回到上一步
            current_step.status = StepStatus.PENDING
            current_step.acted_by = None
            current_step.acted_at = None

            prev_step_order = workflow.current_step_order - 1
            prev_step = next(
                (s for s in workflow.steps if s.step_order == prev_step_order), None
            )
            if prev_step:
                prev_step.status = StepStatus.IN_PROGRESS
                prev_step.acted_by = None
                prev_step.acted_at = None
                prev_step.comment = None
                workflow.current_step_order = prev_step_order

        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def withdraw(self, workflow_id: str, actor_id: str) -> Workflow:
        """撤回审批（仅发起人可操作）."""
        workflow = await self._get_workflow(workflow_id)
        self._validate_workflow_active(workflow)

        if workflow.initiated_by != actor_id:
            raise BusinessError("只有发起人可以撤回审批")

        workflow.status = WorkflowStatus.CANCELLED
        workflow.completed_at = datetime.now(timezone.utc)

        self.db.add(WorkflowAction(
            workflow_id=workflow_id,
            action=ActionType.WITHDRAW,
            actor_id=actor_id,
            comment="发起人撤回",
        ))

        # 文档回到草稿
        doc = await self.db.get(Document, workflow.document_id)
        if doc:
            doc.status = DocumentStatus.DRAFT

        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    # ---------- 查询 ----------

    async def get_workflow(self, workflow_id: str) -> Workflow:
        """获取工作流详情."""
        return await self._get_workflow(workflow_id)

    async def get_workflow_by_document(self, document_id: str) -> Workflow | None:
        """获取文档当前的工作流."""
        result = await self.db.execute(
            select(Workflow)
            .options(selectinload(Workflow.steps))
            .where(Workflow.document_id == document_id)
            .order_by(Workflow.initiated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_pending_workflows(self, user_id: str) -> list[Workflow]:
        """获取用户待处理的审批."""
        result = await self.db.execute(
            select(Workflow)
            .join(WorkflowStep)
            .where(
                Workflow.status == WorkflowStatus.IN_PROGRESS,
                WorkflowStep.assignee_id == user_id,
                WorkflowStep.status == StepStatus.IN_PROGRESS,
            )
            .options(selectinload(Workflow.steps), selectinload(Workflow.document))
        )
        return list(result.scalars().unique().all())

    # ---------- 内部方法 ----------

    async def _get_workflow(self, workflow_id: str) -> Workflow:
        result = await self.db.execute(
            select(Workflow)
            .options(selectinload(Workflow.steps))
            .where(Workflow.id == workflow_id)
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise BusinessError("工作流不存在")
        return workflow

    def _validate_workflow_active(self, workflow: Workflow) -> None:
        if workflow.status != WorkflowStatus.IN_PROGRESS:
            raise BusinessError("工作流不在进行中状态")

    def _get_current_step(self, workflow: Workflow) -> WorkflowStep:
        step = next(
            (s for s in workflow.steps if s.step_order == workflow.current_step_order),
            None,
        )
        if not step:
            raise BusinessError("找不到当前审批步骤")
        return step

    def _validate_actor(self, step: WorkflowStep, actor_id: str) -> None:
        """验证操作人是否有权限操作此步骤."""
        if step.assignee_id and step.assignee_id != actor_id:
            raise BusinessError("您不是当前步骤的审批人")

    def _get_next_step(self, workflow: Workflow) -> WorkflowStep | None:
        """获取下一个待处理步骤."""
        return next(
            (s for s in workflow.steps if s.step_order > workflow.current_step_order and s.status == StepStatus.PENDING),
            None,
        )

"""审批工作流 API 路由."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.workflow import Workflow, WorkflowAction as WorkflowActionModel
from app.schemas.workflow import (
    WorkflowActionRequest,
    WorkflowActionResponse,
    WorkflowResponse,
    WorkflowStepResponse,
    WorkflowSubmit,
    WorkflowTemplateCreate,
    WorkflowTemplateResponse,
)
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["审批工作流"])


# ---------- 工作流模板管理 ----------


@router.post("/templates", response_model=WorkflowTemplateResponse)
async def create_workflow_template(
    data: WorkflowTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建工作流模板."""
    service = WorkflowService(db)
    template = await service.create_template(
        name=data.name,
        doc_type=data.doc_type,
        steps=[s.model_dump() for s in data.steps],
        description=data.description,
        created_by=current_user.id,
    )
    return WorkflowTemplateResponse.model_validate(template)


@router.get("/templates", response_model=list[WorkflowTemplateResponse])
async def list_workflow_templates(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取所有工作流模板."""
    service = WorkflowService(db)
    templates = await service.list_templates()
    return [WorkflowTemplateResponse.model_validate(t) for t in templates]


@router.get("/templates/{template_id}", response_model=WorkflowTemplateResponse)
async def get_workflow_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取工作流模板详情."""
    service = WorkflowService(db)
    template = await service.get_template(template_id)
    return WorkflowTemplateResponse.model_validate(template)


# ---------- 工作流操作 ----------


@router.post("/submit", response_model=WorkflowResponse)
async def submit_for_review(
    data: WorkflowSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交文档进入审批流程."""
    service = WorkflowService(db)
    workflow = await service.submit_document(data.document_id, current_user.id)
    return _build_workflow_response(workflow)


@router.post("/{workflow_id}/approve", response_model=WorkflowResponse)
async def approve_workflow(
    workflow_id: str,
    data: WorkflowActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批准当前步骤."""
    service = WorkflowService(db)
    workflow = await service.approve_step(workflow_id, current_user.id, data.comment)
    return _build_workflow_response(workflow)


@router.post("/{workflow_id}/reject", response_model=WorkflowResponse)
async def reject_workflow(
    workflow_id: str,
    data: WorkflowActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """拒绝当前步骤."""
    service = WorkflowService(db)
    workflow = await service.reject_step(workflow_id, current_user.id, data.comment or "")
    return _build_workflow_response(workflow)


@router.post("/{workflow_id}/return", response_model=WorkflowResponse)
async def return_workflow(
    workflow_id: str,
    data: WorkflowActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """退回到上一步."""
    service = WorkflowService(db)
    workflow = await service.return_step(workflow_id, current_user.id, data.comment or "")
    return _build_workflow_response(workflow)


@router.post("/{workflow_id}/withdraw", response_model=WorkflowResponse)
async def withdraw_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """撤回审批."""
    service = WorkflowService(db)
    workflow = await service.withdraw(workflow_id, current_user.id)
    return _build_workflow_response(workflow)


# ---------- 工作流查询 ----------


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取工作流详情."""
    service = WorkflowService(db)
    workflow = await service.get_workflow(workflow_id)
    return _build_workflow_response(workflow)


@router.get("/document/{document_id}", response_model=WorkflowResponse | None)
async def get_workflow_by_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取文档的当前工作流."""
    service = WorkflowService(db)
    workflow = await service.get_workflow_by_document(document_id)
    if not workflow:
        return None
    return _build_workflow_response(workflow)


@router.get("/pending/mine", response_model=list[WorkflowResponse])
async def get_my_pending_workflows(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取我的待审批工作流."""
    service = WorkflowService(db)
    workflows = await service.get_pending_workflows(current_user.id)
    return [_build_workflow_response(w) for w in workflows]


@router.get("/{workflow_id}/actions", response_model=list[WorkflowActionResponse])
async def get_workflow_actions(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取工作流操作历史."""
    result = await db.execute(
        select(WorkflowActionModel)
        .where(WorkflowActionModel.workflow_id == workflow_id)
        .order_by(WorkflowActionModel.created_at.asc())
    )
    actions = result.scalars().all()
    return [
        WorkflowActionResponse(
            id=a.id,
            action=a.action,
            actor_id=a.actor_id,
            actor_name=a.actor.full_name if a.actor else None,
            comment=a.comment,
            created_at=a.created_at,
        )
        for a in actions
    ]


# ---------- Helper ----------


def _build_workflow_response(workflow: Workflow) -> WorkflowResponse:
    """构建工作流响应."""
    return WorkflowResponse(
        id=workflow.id,
        template_id=workflow.template_id,
        document_id=workflow.document_id,
        status=workflow.status,
        current_step_order=workflow.current_step_order,
        initiated_by=workflow.initiated_by,
        initiator_name=workflow.initiator.full_name if workflow.initiator else None,
        initiated_at=workflow.initiated_at,
        completed_at=workflow.completed_at,
        steps=[
            WorkflowStepResponse(
                id=s.id,
                step_order=s.step_order,
                name=s.name,
                step_type=s.step_type,
                status=s.status,
                assignee_id=s.assignee_id,
                assignee_name=s.assignee.full_name if s.assignee else None,
                acted_by=s.acted_by,
                actor_name=s.actor.full_name if s.actor else None,
                acted_at=s.acted_at,
                comment=s.comment,
            )
            for s in workflow.steps
        ],
    )

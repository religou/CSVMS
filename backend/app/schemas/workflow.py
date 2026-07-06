"""审批工作流 Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.workflow import ActionType, StepStatus, StepType, WorkflowStatus


# ---------- 工作流模板 ----------


class TemplateStepCreate(BaseModel):
    """模板步骤创建."""

    name: str = Field(..., max_length=100)
    step_type: StepType
    role_id: str | None = None
    assignee_id: str | None = None
    project_role: str | None = None


class WorkflowTemplateCreate(BaseModel):
    """工作流模板创建."""

    name: str = Field(..., max_length=100)
    doc_type: str = Field(..., max_length=20)
    description: str | None = None
    steps: list[TemplateStepCreate] = Field(..., min_length=1)


class WorkflowTemplateUpdate(BaseModel):
    """工作流模板更新."""

    name: str | None = Field(None, max_length=100)
    doc_type: str | None = Field(None, max_length=20)
    description: str | None = None
    is_active: bool | None = None
    steps: list[TemplateStepCreate] | None = Field(None, min_length=1)


class TemplateStepResponse(BaseModel):
    """模板步骤响应."""

    id: str
    step_order: int
    name: str
    step_type: StepType
    role_id: str | None = None
    assignee_id: str | None = None
    project_role: str | None = None

    model_config = {"from_attributes": True}


class WorkflowTemplateResponse(BaseModel):
    """工作流模板响应."""

    id: str
    name: str
    doc_type: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    steps: list[TemplateStepResponse] = []

    model_config = {"from_attributes": True}


# ---------- 工作流实例 ----------


class WorkflowSubmit(BaseModel):
    """提交审批."""

    document_id: str


class WorkflowActionRequest(BaseModel):
    """审批操作请求."""

    comment: str | None = None


class WorkflowStepResponse(BaseModel):
    """工作流步骤响应."""

    id: str
    step_order: int
    name: str
    step_type: StepType
    status: StepStatus
    assignee_id: str | None = None
    assignee_name: str | None = None
    acted_by: str | None = None
    actor_name: str | None = None
    acted_at: datetime | None = None
    comment: str | None = None

    model_config = {"from_attributes": True}


class WorkflowResponse(BaseModel):
    """工作流响应."""

    id: str
    template_id: str
    document_id: str
    status: WorkflowStatus
    current_step_order: int
    initiated_by: str
    initiator_name: str | None = None
    initiated_at: datetime
    completed_at: datetime | None = None
    steps: list[WorkflowStepResponse] = []

    model_config = {"from_attributes": True}


class WorkflowActionResponse(BaseModel):
    """审批动作记录响应."""

    id: str
    action: ActionType
    actor_id: str
    actor_name: str | None = None
    comment: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

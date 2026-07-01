"""审批工作流数据模型."""

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base
from app.models.user import generate_uuid, utcnow


# ---------- 枚举 ----------


class WorkflowStatus(str, enum.Enum):
    """工作流实例状态."""

    PENDING = "pending"          # 待处理（尚未开始）
    IN_PROGRESS = "in_progress"  # 进行中
    APPROVED = "approved"        # 已批准
    REJECTED = "rejected"        # 已拒绝
    CANCELLED = "cancelled"      # 已撤回


class StepType(str, enum.Enum):
    """步骤类型."""

    REVIEW = "review"      # 审核
    APPROVE = "approve"    # 批准


class StepStatus(str, enum.Enum):
    """步骤状态."""

    PENDING = "pending"      # 待处理
    IN_PROGRESS = "in_progress"  # 进行中（当前活动步骤）
    APPROVED = "approved"    # 已通过
    REJECTED = "rejected"    # 已拒绝
    SKIPPED = "skipped"      # 已跳过


class ActionType(str, enum.Enum):
    """审批动作类型."""

    SUBMIT = "submit"      # 提交审核
    APPROVE = "approve"    # 批准
    REJECT = "reject"      # 拒绝
    RETURN = "return"      # 退回（到上一步或起草人）
    WITHDRAW = "withdraw"  # 撤回


# ---------- 工作流模板 ----------


class WorkflowTemplate(Base):
    """工作流模板 - 定义不同文档类型的审批流程."""

    __tablename__ = "workflow_templates"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_type: Mapped[str] = mapped_column(String(20), index=True)  # 对应 DocumentType
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    steps: Mapped[list["WorkflowTemplateStep"]] = relationship(
        back_populates="template", order_by="WorkflowTemplateStep.step_order",
        cascade="all, delete-orphan", lazy="selectin"
    )
    workflows: Mapped[list["Workflow"]] = relationship(back_populates="template")


class WorkflowTemplateStep(Base):
    """工作流模板步骤 - 定义审批流的每个步骤."""

    __tablename__ = "workflow_template_steps"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)
    template_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("workflow_templates.id"), index=True)
    step_order: Mapped[int] = mapped_column(Integer)  # 步骤顺序（1-based）
    name: Mapped[str] = mapped_column(String(100))
    step_type: Mapped[StepType] = mapped_column(Enum(StepType))
    role_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("roles.id"), nullable=True)
    assignee_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=True)
    # 如果 role_id 和 assignee_id 都为空，则由管理员手动指派

    # Relationships
    template: Mapped["WorkflowTemplate"] = relationship(back_populates="steps")


# ---------- 工作流实例 ----------


class Workflow(Base):
    """工作流实例 - 一个文档的具体审批流程."""

    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)
    template_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("workflow_templates.id"), index=True)
    document_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("documents.id"), index=True)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus), default=WorkflowStatus.PENDING
    )
    current_step_order: Mapped[int] = mapped_column(Integer, default=0)

    initiated_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"))
    initiated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    template: Mapped["WorkflowTemplate"] = relationship(back_populates="workflows")
    document: Mapped["Document"] = relationship("Document", lazy="selectin")
    steps: Mapped[list["WorkflowStep"]] = relationship(
        back_populates="workflow", order_by="WorkflowStep.step_order",
        cascade="all, delete-orphan", lazy="selectin"
    )
    initiator: Mapped["User"] = relationship("User", foreign_keys=[initiated_by], lazy="selectin")


class WorkflowStep(Base):
    """工作流步骤实例 - 审批流中每一步的实际执行状态."""

    __tablename__ = "workflow_steps"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)
    workflow_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("workflows.id"), index=True)
    step_order: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(100))
    step_type: Mapped[StepType] = mapped_column(Enum(StepType))
    status: Mapped[StepStatus] = mapped_column(Enum(StepStatus), default=StepStatus.PENDING)

    assignee_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=True)
    acted_by: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=True)
    acted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="steps")
    assignee: Mapped["User"] = relationship("User", foreign_keys=[assignee_id], lazy="selectin")
    actor: Mapped["User"] = relationship("User", foreign_keys=[acted_by], lazy="selectin")


# ---------- 审批动作记录 ----------


class WorkflowAction(Base):
    """审批动作记录 - 不可变的操作日志."""

    __tablename__ = "workflow_actions"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)
    workflow_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("workflows.id"), index=True)
    step_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("workflow_steps.id"), nullable=True)
    action: Mapped[ActionType] = mapped_column(Enum(ActionType))
    actor_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Relationships
    actor: Mapped["User"] = relationship("User", foreign_keys=[actor_id], lazy="selectin")

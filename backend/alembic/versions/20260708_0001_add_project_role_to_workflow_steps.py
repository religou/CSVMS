"""add project_role column to workflow_steps and backfill in-progress flows

审批步骤实例（workflow_steps）新增 project_role 字段，作为该步骤固有的
“步骤角色要求”（Step Role Requirement）——决定审批候选人集合与审批记录中的
角色归属。此前该角色要求只存在于模板步骤（workflow_template_steps.project_role），
未固化到实例步骤上。

本迁移在加列之后，对存量流程回填 project_role：按实例步骤所属工作流的
template_id + step_order，对应到模板步骤，取其 project_role。仅回填当前仍在
进行中/待处理的流程（其 workflow.status 为 in_progress/pending），使这些老流程
也具备角色展示与候选人校验能力；已终结（approved/rejected/cancelled）的历史流程
不追溯回填，保持其历史步骤原样。

Revision ID: 20260708_0001
Revises: 20260707_0001
Create Date: 2026-07-08 00:01:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0001"
down_revision = "20260707_0001"
branch_labels = None
depends_on = None


def _validate_schema(bind) -> None:
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    required_tables = {"workflow_steps", "workflow_template_steps", "workflows"}
    missing_tables = sorted(required_tables - tables)
    if missing_tables:
        raise RuntimeError(
            "审批步骤角色回填迁移缺少必要数据表: " + ", ".join(missing_tables)
        )


def upgrade_data(bind: sa.engine.Connection) -> None:
    """按 template_id + step_order 从模板步骤回填进行中流程的 project_role。"""
    _validate_schema(bind)

    # 仅回填仍在进行中/待处理流程的步骤。
    bind.execute(
        sa.text(
            """
            UPDATE workflow_steps AS ws
            JOIN workflows AS w ON w.id = ws.workflow_id
            JOIN workflow_template_steps AS wts
                ON wts.template_id = w.template_id
               AND wts.step_order = ws.step_order
            SET ws.project_role = wts.project_role
            WHERE ws.project_role IS NULL
              AND w.status IN ('IN_PROGRESS', 'PENDING')
            """
        )
    )


def upgrade() -> None:
    op.add_column(
        "workflow_steps",
        sa.Column("project_role", sa.String(50), nullable=True),
    )
    upgrade_data(op.get_bind())


def downgrade() -> None:
    op.drop_column("workflow_steps", "project_role")

"""add project_role column to workflow_template_steps

审批模板步骤新增 project_role 字段，用于指定由哪个项目角色（来自 project_role 字典）
执行"审核"/"批准"步骤。

Revision ID: 20260703_0001
Revises: 20260701_0003
Create Date: 2026-07-03 00:01:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260703_0001"
down_revision = "20260701_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_template_steps",
        sa.Column("project_role", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflow_template_steps", "project_role")

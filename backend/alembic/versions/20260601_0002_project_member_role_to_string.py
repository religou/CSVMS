"""convert project member role to string

Revision ID: 20260601_0002
Revises: 20260601_0001
Create Date: 2026-06-01 00:02:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260601_0002"
down_revision = "20260601_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "project_members",
        "role",
        existing_type=sa.Enum("OWNER", "MANAGER", "MEMBER", "VIEWER", name="projectrole"),
        type_=sa.String(length=50),
        existing_nullable=False,
    )
    op.execute("UPDATE project_members SET role = LOWER(role)")


def downgrade() -> None:
    op.execute("UPDATE project_members SET role = UPPER(role)")
    op.alter_column(
        "project_members",
        "role",
        existing_type=sa.String(length=50),
        type_=sa.Enum("OWNER", "MANAGER", "MEMBER", "VIEWER", name="projectrole"),
        existing_nullable=False,
    )
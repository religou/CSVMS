"""create systems table and add system_id to projects

Revision ID: 20260615_0001
Revises: 20260601_0005
Create Date: 2026-06-15 00:01:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import CHAR


# revision identifiers, used by Alembic.
revision = "20260615_0001"
down_revision = "20260601_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "systems",
        sa.Column("id", CHAR(36), primary_key=True),
        sa.Column("code", sa.String(50), unique=True, index=True, nullable=False),
        sa.Column("name", sa.String(200), index=True, nullable=False),
        sa.Column("vendor", sa.String(200), nullable=True),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("gxp_category", sa.String(50), nullable=True),
        sa.Column("gamp5_category", sa.String(50), nullable=True),
        sa.Column("owner_id", CHAR(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.add_column(
        "projects",
        sa.Column("system_id", CHAR(36), sa.ForeignKey("systems.id"), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "system_id")
    op.drop_table("systems")

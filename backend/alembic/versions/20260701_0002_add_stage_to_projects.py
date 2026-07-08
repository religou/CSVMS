"""add stage column to projects

Revision ID: 20260701_0002
Revises: 20260701_0001
Create Date: 2026-07-01 00:02:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260701_0002"
down_revision = "20260701_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("stage", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "stage")

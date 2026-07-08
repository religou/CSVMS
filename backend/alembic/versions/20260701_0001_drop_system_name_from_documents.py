"""drop system_name column from documents

Revision ID: 20260701_0001
Revises: 20260615_0001
Create Date: 2026-07-01 00:01:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260701_0001"
down_revision = "20260615_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("documents", "system_name")


def downgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("system_name", sa.String(100), nullable=True),
    )

"""add permission_profile to dict_items

Revision ID: 20260601_0001
Revises:
Create Date: 2026-06-01 00:01:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260601_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dict_items",
        sa.Column("permission_profile", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dict_items", "permission_profile")
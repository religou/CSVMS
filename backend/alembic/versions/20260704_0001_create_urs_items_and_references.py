"""create urs_items and urs_references tables

新增 URS 条目级追溯所需的两张子资源表：
- urs_items: 归属于某一 URS 文档的结构化用户需求条目
- urs_references: Referencing_Document 与其引用的 URS_Item 之间的关联关系

Revision ID: 20260704_0001
Revises: 20260703_0001
Create Date: 2026-07-04 00:01:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import CHAR


# revision identifiers, used by Alembic.
revision = "20260704_0001"
down_revision = "20260703_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "urs_items",
        sa.Column("id", CHAR(36), primary_key=True),
        sa.Column("document_id", CHAR(36), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("item_code", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("created_by", CHAR(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("document_id", "item_code", name="uq_urs_items_document_item_code"),
    )

    op.create_table(
        "urs_references",
        sa.Column("id", CHAR(36), primary_key=True),
        sa.Column("document_id", CHAR(36), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("urs_item_id", CHAR(36), sa.ForeignKey("urs_items.id"), nullable=False, index=True),
        sa.Column("created_by", CHAR(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("document_id", "urs_item_id", name="uq_urs_references_document_urs_item"),
    )


def downgrade() -> None:
    op.drop_table("urs_references")
    op.drop_table("urs_items")

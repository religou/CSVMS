"""drop trace_links table

移除文档级追溯功能（TraceLink）遗留的 trace_links 表。追溯矩阵已改为以 URS 条目
覆盖关系为核心（urs_items / urs_references），不再使用文档间的 trace_links 表。

Revision ID: 20260705_0001
Revises: 20260704_0001
Create Date: 2026-07-05 00:01:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import CHAR


# revision identifiers, used by Alembic.
revision = "20260705_0001"
down_revision = "20260704_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 该表可能由早期 create_all 创建而非迁移创建，因此存在性无法保证。
    # 仅在表存在时才删除，保证迁移在任意环境下都可安全执行（幂等）。
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "trace_links" in inspector.get_table_names():
        op.drop_table("trace_links")


def downgrade() -> None:
    # 恢复原 trace_links 表结构（文档间追溯关系）。
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "trace_links" in inspector.get_table_names():
        return

    op.create_table(
        "trace_links",
        sa.Column("id", CHAR(36), primary_key=True),
        sa.Column(
            "source_document_id",
            CHAR(36),
            sa.ForeignKey("documents.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("source_section", sa.String(100), nullable=True),
        sa.Column(
            "target_document_id",
            CHAR(36),
            sa.ForeignKey("documents.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("target_section", sa.String(100), nullable=True),
        sa.Column("link_type", sa.String(50), nullable=False, server_default="traces_to"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_by", CHAR(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index(
        "ix_trace_links_pair",
        "trace_links",
        ["source_document_id", "target_document_id"],
    )

"""backfill project role permission profiles

Revision ID: 20260601_0003
Revises: 20260601_0002
Create Date: 2026-06-01 00:03:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260601_0003"
down_revision = "20260601_0002"
branch_labels = None
depends_on = None


def _infer_permission_profile(code: str, label: str | None) -> str:
    normalized_code = (code or "").strip().lower()
    normalized_label = (label or "").strip().lower()

    if normalized_code == "owner" or "项目负责人" in normalized_label:
        return "owner"

    if (
        normalized_code in {"manager", "pm", "vm", "bm", "qa", "it", "system_owner", "it_owner"}
        or "经理" in normalized_label
        or "负责人" in normalized_label
    ):
        return "manager"

    if (
        normalized_code in {"viewer", "read_only", "readonly"}
        or "只读" in normalized_label
        or "查看" in normalized_label
    ):
        return "viewer"

    return "member"


def upgrade() -> None:
    bind = op.get_bind()

    project_role_category_id = bind.execute(
        sa.text(
            "SELECT id FROM dict_categories WHERE code = :category_code LIMIT 1"
        ),
        {"category_code": "project_role"},
    ).scalar()

    if not project_role_category_id:
        return

    rows = bind.execute(
        sa.text(
            """
            SELECT id, code, label
            FROM dict_items
            WHERE category_id = :category_id
              AND (permission_profile IS NULL OR TRIM(permission_profile) = '')
            """
        ),
        {"category_id": project_role_category_id},
    ).mappings()

    for row in rows:
        bind.execute(
            sa.text(
                "UPDATE dict_items SET permission_profile = :permission_profile WHERE id = :item_id"
            ),
            {
                "item_id": row["id"],
                "permission_profile": _infer_permission_profile(
                    row["code"],
                    row["label"],
                ),
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    project_role_category_id = bind.execute(
        sa.text(
            "SELECT id FROM dict_categories WHERE code = :category_code LIMIT 1"
        ),
        {"category_code": "project_role"},
    ).scalar()

    if not project_role_category_id:
        return

    bind.execute(
        sa.text(
            "UPDATE dict_items SET permission_profile = NULL WHERE category_id = :category_id"
        ),
        {"category_id": project_role_category_id},
    )
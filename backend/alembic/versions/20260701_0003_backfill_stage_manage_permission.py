"""backfill project.stage.manage into owner/manager project_role items

早期 permission_codes 的种子数据未包含 `project.stage.manage`，导致 owner/manager
角色的项目成员无法在仪表盘编辑并保存项目阶段。本迁移为所有 permission_profile 为
owner 或 manager 且尚未包含该权限编码的 project_role 字典项补齐 `project.stage.manage`。

Revision ID: 20260701_0003
Revises: 20260701_0002
Create Date: 2026-07-01 00:03:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260701_0003"
down_revision = "20260701_0002"
branch_labels = None
depends_on = None

STAGE_MANAGE_CODE = "project.stage.manage"
MANAGE_PROFILES = {"owner", "manager"}


def _iter_project_role_items(bind):
    dict_items = sa.table(
        "dict_items",
        sa.column("id", sa.String),
        sa.column("category_id", sa.String),
        sa.column("permission_profile", sa.String),
        sa.column("permission_codes", sa.JSON),
    )
    dict_categories = sa.table(
        "dict_categories",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
    )

    category_id = bind.execute(
        sa.select(dict_categories.c.id).where(
            dict_categories.c.code == "project_role"
        )
    ).scalar()

    if not category_id:
        return dict_items, []

    rows = (
        bind.execute(
            sa.select(
                dict_items.c.id,
                dict_items.c.permission_profile,
                dict_items.c.permission_codes,
            ).where(dict_items.c.category_id == category_id)
        )
        .mappings()
        .all()
    )
    return dict_items, rows


def upgrade() -> None:
    bind = op.get_bind()
    dict_items, rows = _iter_project_role_items(bind)

    for row in rows:
        if row["permission_profile"] not in MANAGE_PROFILES:
            continue

        codes = list(row["permission_codes"] or [])
        if STAGE_MANAGE_CODE in codes:
            continue

        codes.append(STAGE_MANAGE_CODE)
        bind.execute(
            sa.update(dict_items)
            .where(dict_items.c.id == row["id"])
            .values(permission_codes=codes)
        )


def downgrade() -> None:
    bind = op.get_bind()
    dict_items, rows = _iter_project_role_items(bind)

    for row in rows:
        if row["permission_profile"] not in MANAGE_PROFILES:
            continue

        codes = list(row["permission_codes"] or [])
        if STAGE_MANAGE_CODE not in codes:
            continue

        codes = [c for c in codes if c != STAGE_MANAGE_CODE]
        bind.execute(
            sa.update(dict_items)
            .where(dict_items.c.id == row["id"])
            .values(permission_codes=codes)
        )

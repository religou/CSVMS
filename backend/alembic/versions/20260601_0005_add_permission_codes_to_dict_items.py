"""add permission_codes to dict_items

Revision ID: 20260601_0005
Revises: 20260601_0004
Create Date: 2026-06-01 00:05:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260601_0005"
down_revision = "20260601_0004"
branch_labels = None
depends_on = None


def _default_project_role_permission_codes(permission_profile: str | None) -> list[str] | None:
    base_codes = [
        "project.dashboard.menu",
        "project.dashboard.view",
        "project.documents.menu",
        "project.documents.view",
        "project.workflows.menu",
        "project.workflows.view",
        "project.traceability.menu",
        "project.traceability.view",
        "project.audit_log.menu",
        "project.audit_log.view",
        "project.members.menu",
        "project.members.view",
    ]

    if permission_profile in {"owner", "manager"}:
        return base_codes + [
            "project.documents.manage",
            "project.workflows.manage",
            "project.members.manage",
        ]

    if permission_profile == "member":
        return base_codes + ["project.documents.manage"]

    if permission_profile == "viewer":
        return base_codes

    return None


def upgrade() -> None:
    op.add_column(
        "dict_items",
        sa.Column("permission_codes", sa.JSON(), nullable=True),
    )

    bind = op.get_bind()
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

    project_role_category_id = bind.execute(
        sa.select(dict_categories.c.id).where(dict_categories.c.code == "project_role")
    ).scalar()

    if not project_role_category_id:
        return

    rows = bind.execute(
        sa.select(
            dict_items.c.id,
            dict_items.c.permission_profile,
            dict_items.c.permission_codes,
        ).where(dict_items.c.category_id == project_role_category_id)
    ).mappings().all()

    for row in rows:
        if row["permission_codes"]:
            continue

        default_codes = _default_project_role_permission_codes(row["permission_profile"])
        if default_codes is None:
            continue

        bind.execute(
            sa.update(dict_items)
            .where(dict_items.c.id == row["id"])
            .values(permission_codes=default_codes)
        )


def downgrade() -> None:
    op.drop_column("dict_items", "permission_codes")
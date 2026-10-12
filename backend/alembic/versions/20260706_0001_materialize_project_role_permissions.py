"""materialize project role permissions

Revision ID: 20260706_0001
Revises: 20260705_0001
Create Date: 2026-07-06 00:01:00
"""

import uuid

from alembic import op
import sqlalchemy as sa

from app.core.permission_catalog import (
    default_project_role_permission_codes,
    default_system_role_permission_codes,
    permission_seed_data,
    validate_project_role_permission_codes,
)


revision = "20260706_0001"
down_revision = "20260705_0001"
branch_labels = None
depends_on = None


_REQUIRED_SCHEMA = {
    "dict_categories": {"id", "code"},
    "dict_items": {
        "id",
        "category_id",
        "code",
        "permission_profile",
        "permission_codes",
    },
    "permissions": {
        "id",
        "code",
        "resource_type",
        "action",
        "display_name",
        "description",
    },
    "roles": {"id", "name"},
    "role_permissions": {"role_id", "permission_id"},
}


def _validate_schema(bind) -> None:
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    missing_tables = sorted(set(_REQUIRED_SCHEMA) - table_names)
    if missing_tables:
        raise RuntimeError(
            "项目角色权限迁移缺少必要数据表: " + ", ".join(missing_tables)
        )

    missing_columns = []
    for table_name, required_columns in _REQUIRED_SCHEMA.items():
        actual_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        for column_name in sorted(required_columns - actual_columns):
            missing_columns.append(f"{table_name}.{column_name}")
    if missing_columns:
        raise RuntimeError(
            "项目角色权限迁移缺少必要字段: " + ", ".join(missing_columns)
        )


def _tables():
    dict_categories = sa.table(
        "dict_categories",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
    )
    dict_items = sa.table(
        "dict_items",
        sa.column("id", sa.String),
        sa.column("category_id", sa.String),
        sa.column("code", sa.String),
        sa.column("permission_profile", sa.String),
        sa.column("permission_codes", sa.JSON),
    )
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
        sa.column("resource_type", sa.String),
        sa.column("action", sa.String),
        sa.column("display_name", sa.String),
        sa.column("description", sa.Text),
    )
    roles = sa.table(
        "roles",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.String),
        sa.column("permission_id", sa.String),
    )
    return dict_categories, dict_items, permissions, roles, role_permissions


def _plan_project_role_updates(bind, dict_categories, dict_items):
    category_ids = bind.execute(
        sa.select(dict_categories.c.id).where(
            dict_categories.c.code == "project_role"
        )
    ).scalars().all()
    if len(category_ids) > 1:
        raise RuntimeError("存在多个 project_role 字典类别")
    if not category_ids:
        return []

    rows = bind.execute(
        sa.select(
            dict_items.c.id,
            dict_items.c.code,
            dict_items.c.permission_profile,
            dict_items.c.permission_codes,
        ).where(dict_items.c.category_id == category_ids[0])
    ).mappings().all()

    updates = []
    for row in rows:
        permission_codes = row["permission_codes"]
        role_ref = f"{row['code']} ({row['id']})"

        if permission_codes is not None and permission_codes != []:
            if not isinstance(permission_codes, list) or not all(
                isinstance(code, str) for code in permission_codes
            ):
                raise RuntimeError(
                    f"项目角色 {role_ref} 的 permission_codes 必须是字符串数组"
                )
            try:
                validate_project_role_permission_codes(permission_codes)
            except ValueError as exc:
                raise RuntimeError(
                    f"项目角色 {role_ref} 的权限配置无效: {exc}"
                ) from exc
            continue

        try:
            default_codes = default_project_role_permission_codes(
                row["permission_profile"]
            )
        except ValueError as exc:
            raise RuntimeError(
                f"项目角色 {role_ref} 无法物化权限: {exc}"
            ) from exc
        updates.append((row["id"], default_codes))
    return updates


def _upsert_catalog(bind, permissions):
    catalog = permission_seed_data()
    existing_rows = bind.execute(
        sa.select(permissions.c.id, permissions.c.code).where(
            permissions.c.code.in_([item["code"] for item in catalog])
        )
    ).mappings().all()
    permission_ids = {row["code"]: row["id"] for row in existing_rows}

    for item in catalog:
        permission_id = permission_ids.get(item["code"])
        values = {
            "resource_type": item["resource_type"],
            "action": item["action"],
            "display_name": item["display_name"],
            "description": item["description"],
        }
        if permission_id is None:
            permission_id = str(uuid.uuid4())
            bind.execute(
                sa.insert(permissions).values(
                    id=permission_id,
                    code=item["code"],
                    **values,
                )
            )
            permission_ids[item["code"]] = permission_id
        else:
            bind.execute(
                sa.update(permissions)
                .where(permissions.c.id == permission_id)
                .values(**values)
            )
    return permission_ids


def _get_admin_id(bind, roles):
    admin_rows = bind.execute(
        sa.select(roles.c.id).where(roles.c.name == "admin")
    ).scalars().all()
    if len(admin_rows) != 1:
        raise RuntimeError("迁移要求且仅允许存在一个 admin 系统角色")
    return admin_rows[0]


def _merge_admin_permissions(
    bind,
    admin_id,
    role_permissions,
    permission_ids,
):
    required_ids = {
        permission_ids[code]
        for code in default_system_role_permission_codes("admin")
    }
    existing_ids = set(
        bind.execute(
            sa.select(role_permissions.c.permission_id).where(
                role_permissions.c.role_id == admin_id,
                role_permissions.c.permission_id.in_(required_ids),
            )
        ).scalars().all()
    )
    for permission_id in required_ids - existing_ids:
        bind.execute(
            sa.insert(role_permissions).values(
                role_id=admin_id,
                permission_id=permission_id,
            )
        )


def upgrade_data(bind: sa.engine.Connection) -> None:
    """物化旧项目角色权限，并同步唯一 Permission Catalog。"""
    _validate_schema(bind)
    (
        dict_categories,
        dict_items,
        permissions,
        roles,
        role_permissions,
    ) = _tables()

    project_role_updates = _plan_project_role_updates(
        bind,
        dict_categories,
        dict_items,
    )
    admin_id = _get_admin_id(bind, roles)
    permission_ids = _upsert_catalog(bind, permissions)

    for item_id, default_codes in project_role_updates:
        bind.execute(
            sa.update(dict_items)
            .where(dict_items.c.id == item_id)
            .values(permission_codes=default_codes)
        )

    _merge_admin_permissions(
        bind,
        admin_id,
        role_permissions,
        permission_ids,
    )


def upgrade() -> None:
    upgrade_data(op.get_bind())


def downgrade() -> None:
    # 原始 NULL、[] 与显式默认值在物化后不可区分；目录更新也无法无损恢复。
    pass

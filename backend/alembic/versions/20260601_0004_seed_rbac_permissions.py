"""seed rbac permissions and default system role mappings

Revision ID: 20260601_0004
Revises: 20260601_0003
Create Date: 2026-06-01 00:04:00
"""

from datetime import datetime, timezone
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260601_0004"
down_revision = "20260601_0003"
branch_labels = None
depends_on = None


BUILTIN_SYSTEM_ROLES = [
    {
        "name": "admin",
        "display_name": "系统管理员",
        "description": "拥有系统管理全部权限的内置角色",
        "is_system": True,
    },
    {
        "name": "validation_admin",
        "display_name": "验证管理员",
        "description": "受限内置角色，可访问系统管理但不能分配角色权限",
        "is_system": True,
    },
    {
        "name": "user",
        "display_name": "普通用户",
        "description": "默认业务用户角色",
        "is_system": True,
    },
]


PERMISSION_CATALOG = [
    {
        "code": "system.admin.menu",
        "resource_type": "system_menu",
        "action": "access",
        "display_name": "系统管理菜单",
        "description": "显示系统管理一级菜单",
    },
    {
        "code": "system.admin.users.menu",
        "resource_type": "system_menu",
        "action": "access",
        "display_name": "用户管理菜单",
        "description": "显示用户管理菜单入口",
    },
    {
        "code": "system.admin.users.view",
        "resource_type": "system_page",
        "action": "view",
        "display_name": "查看用户管理页面",
        "description": "允许访问用户管理页面",
    },
    {
        "code": "system.admin.users.manage",
        "resource_type": "system_button",
        "action": "manage",
        "display_name": "管理用户",
        "description": "允许执行用户管理相关操作",
    },
    {
        "code": "system.admin.dict.menu",
        "resource_type": "system_menu",
        "action": "access",
        "display_name": "字典管理菜单",
        "description": "显示字典管理菜单入口",
    },
    {
        "code": "system.admin.dict.view",
        "resource_type": "system_page",
        "action": "view",
        "display_name": "查看字典管理页面",
        "description": "允许访问字典管理页面",
    },
    {
        "code": "system.admin.dict.manage",
        "resource_type": "system_button",
        "action": "manage",
        "display_name": "管理字典",
        "description": "允许执行字典管理相关操作",
    },
    {
        "code": "system.admin.roles.menu",
        "resource_type": "system_menu",
        "action": "access",
        "display_name": "角色权限管理菜单",
        "description": "显示角色权限管理菜单入口",
    },
    {
        "code": "system.admin.roles.view",
        "resource_type": "system_page",
        "action": "view",
        "display_name": "查看角色权限管理页面",
        "description": "允许访问角色权限管理页面",
    },
    {
        "code": "system.admin.roles.manage",
        "resource_type": "system_button",
        "action": "manage",
        "display_name": "管理系统角色权限",
        "description": "允许编辑系统角色和分配权限",
    },
    {
        "code": "project.dashboard.menu",
        "resource_type": "project_menu",
        "action": "access",
        "display_name": "项目概览菜单",
        "description": "显示项目概览菜单入口",
    },
    {
        "code": "project.dashboard.view",
        "resource_type": "project_page",
        "action": "view",
        "display_name": "查看项目概览",
        "description": "允许访问项目概览页面",
    },
    {
        "code": "project.documents.menu",
        "resource_type": "project_menu",
        "action": "access",
        "display_name": "文档管理菜单",
        "description": "显示文档管理菜单入口",
    },
    {
        "code": "project.documents.view",
        "resource_type": "project_page",
        "action": "view",
        "display_name": "查看项目文档",
        "description": "允许访问项目文档页面",
    },
    {
        "code": "project.documents.manage",
        "resource_type": "project_button",
        "action": "manage",
        "display_name": "管理项目文档",
        "description": "允许执行项目文档写入相关操作",
    },
    {
        "code": "project.workflows.menu",
        "resource_type": "project_menu",
        "action": "access",
        "display_name": "审批管理菜单",
        "description": "显示审批管理菜单入口",
    },
    {
        "code": "project.workflows.view",
        "resource_type": "project_page",
        "action": "view",
        "display_name": "查看项目审批",
        "description": "允许访问项目审批页面",
    },
    {
        "code": "project.workflows.manage",
        "resource_type": "project_button",
        "action": "manage",
        "display_name": "管理项目审批",
        "description": "允许执行审批相关操作入口",
    },
    {
        "code": "project.traceability.menu",
        "resource_type": "project_menu",
        "action": "access",
        "display_name": "追溯矩阵菜单",
        "description": "显示追溯矩阵菜单入口",
    },
    {
        "code": "project.traceability.view",
        "resource_type": "project_page",
        "action": "view",
        "display_name": "查看追溯矩阵",
        "description": "允许访问追溯矩阵页面",
    },
    {
        "code": "project.audit_log.menu",
        "resource_type": "project_menu",
        "action": "access",
        "display_name": "审计日志菜单",
        "description": "显示审计日志菜单入口",
    },
    {
        "code": "project.audit_log.view",
        "resource_type": "project_page",
        "action": "view",
        "display_name": "查看项目审计日志",
        "description": "允许访问项目审计日志页面",
    },
    {
        "code": "project.members.menu",
        "resource_type": "project_menu",
        "action": "access",
        "display_name": "项目成员菜单",
        "description": "显示项目成员菜单入口",
    },
    {
        "code": "project.members.view",
        "resource_type": "project_page",
        "action": "view",
        "display_name": "查看项目成员",
        "description": "允许访问项目成员页面",
    },
    {
        "code": "project.members.manage",
        "resource_type": "project_button",
        "action": "manage",
        "display_name": "管理项目成员",
        "description": "允许执行项目成员管理相关操作",
    },
]


DEFAULT_ROLE_PERMISSIONS = {
    "admin": {
        permission["code"]
        for permission in PERMISSION_CATALOG
        if permission["code"].startswith("system.")
    },
    "validation_admin": {
        "system.admin.menu",
        "system.admin.users.menu",
        "system.admin.users.view",
        "system.admin.dict.menu",
        "system.admin.dict.view",
        "system.admin.roles.menu",
        "system.admin.roles.view",
    },
    "user": set(),
}


def _generate_uuid() -> str:
    return str(uuid.uuid4())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("permissions"):
        op.create_table(
            "permissions",
            sa.Column("id", sa.CHAR(length=36), primary_key=True, nullable=False),
            sa.Column("code", sa.String(length=100), nullable=False),
            sa.Column("resource_type", sa.String(length=50), nullable=False),
            sa.Column("action", sa.String(length=50), nullable=False),
            sa.Column("display_name", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
        )
        op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)

    if not inspector.has_table("role_permissions"):
        op.create_table(
            "role_permissions",
            sa.Column("role_id", sa.CHAR(length=36), sa.ForeignKey("roles.id"), primary_key=True, nullable=False),
            sa.Column(
                "permission_id",
                sa.CHAR(length=36),
                sa.ForeignKey("permissions.id"),
                primary_key=True,
                nullable=False,
            ),
        )

    if not inspector.has_table("roles"):
        return

    roles_table = sa.table(
        "roles",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("display_name", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_system", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
        sa.column("resource_type", sa.String),
        sa.column("action", sa.String),
        sa.column("display_name", sa.String),
        sa.column("description", sa.Text),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.String),
        sa.column("permission_id", sa.String),
    )

    now = datetime.now(timezone.utc)

    role_rows = bind.execute(
        sa.select(roles_table.c.id, roles_table.c.name).where(
            roles_table.c.name.in_([role["name"] for role in BUILTIN_SYSTEM_ROLES])
        )
    ).mappings().all()
    role_ids = {row["name"]: row["id"] for row in role_rows}

    for role in BUILTIN_SYSTEM_ROLES:
        if role["name"] in role_ids:
            bind.execute(
                sa.update(roles_table)
                .where(roles_table.c.id == role_ids[role["name"]])
                .values(
                    display_name=role["display_name"],
                    description=role["description"],
                    is_system=role["is_system"],
                )
            )
            continue

        role_id = _generate_uuid()
        bind.execute(
            sa.insert(roles_table).values(
                id=role_id,
                name=role["name"],
                display_name=role["display_name"],
                description=role["description"],
                is_system=role["is_system"],
                created_at=now,
            )
        )
        role_ids[role["name"]] = role_id

    permission_rows = bind.execute(
        sa.select(permissions_table.c.id, permissions_table.c.code).where(
            permissions_table.c.code.in_([permission["code"] for permission in PERMISSION_CATALOG])
        )
    ).mappings().all()
    permission_ids = {row["code"]: row["id"] for row in permission_rows}

    for permission in PERMISSION_CATALOG:
        if permission["code"] in permission_ids:
            bind.execute(
                sa.update(permissions_table)
                .where(permissions_table.c.id == permission_ids[permission["code"]])
                .values(
                    resource_type=permission["resource_type"],
                    action=permission["action"],
                    display_name=permission["display_name"],
                    description=permission["description"],
                )
            )
            continue

        permission_id = _generate_uuid()
        bind.execute(
            sa.insert(permissions_table).values(
                id=permission_id,
                code=permission["code"],
                resource_type=permission["resource_type"],
                action=permission["action"],
                display_name=permission["display_name"],
                description=permission["description"],
            )
        )
        permission_ids[permission["code"]] = permission_id

    existing_role_permissions = {
        (row["role_id"], row["permission_id"])
        for row in bind.execute(
            sa.select(
                role_permissions_table.c.role_id,
                role_permissions_table.c.permission_id,
            ).where(
                role_permissions_table.c.role_id.in_(list(role_ids.values())),
                role_permissions_table.c.permission_id.in_(list(permission_ids.values())),
            )
        ).mappings().all()
    }

    for role_name, permission_codes in DEFAULT_ROLE_PERMISSIONS.items():
        role_id = role_ids.get(role_name)
        if role_id is None:
            continue

        for permission_code in permission_codes:
            mapping = (role_id, permission_ids[permission_code])
            if mapping in existing_role_permissions:
                continue
            bind.execute(
                sa.insert(role_permissions_table).values(
                    role_id=role_id,
                    permission_id=permission_ids[permission_code],
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("permissions"):
        return

    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.String),
        sa.column("permission_id", sa.String),
    )

    permission_rows = bind.execute(
        sa.select(permissions_table.c.id, permissions_table.c.code).where(
            permissions_table.c.code.in_([permission["code"] for permission in PERMISSION_CATALOG])
        )
    ).mappings().all()
    permission_ids = [row["id"] for row in permission_rows]

    if inspector.has_table("role_permissions") and permission_ids:
        bind.execute(
            sa.delete(role_permissions_table).where(
                role_permissions_table.c.permission_id.in_(permission_ids)
            )
        )

    if permission_ids:
        bind.execute(
            sa.delete(permissions_table).where(permissions_table.c.id.in_(permission_ids))
        )
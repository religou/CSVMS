"""初始化 RBAC 权限目录与内置系统角色权限.

运行方式: python -m app.scripts.seed_rbac
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_session_factory
from app.models.user import Permission, Role


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
        "description": "允许执行创建、编辑、分配角色、重置密码、删除等用户管理操作",
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
        "description": "允许执行字典类别和字典项管理操作",
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
        "description": "允许编辑系统角色、分配权限和删除可删除角色",
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
        "description": "允许执行审批配置和审批操作入口",
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
        "description": "允许执行添加成员、移除成员和调整成员角色等操作入口",
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


async def seed_rbac(session: AsyncSession) -> None:
    """初始化权限目录、内置系统角色和默认系统角色权限。"""
    role_result = await session.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(Role.name.in_([role["name"] for role in BUILTIN_SYSTEM_ROLES]))
    )
    roles_by_name = {role.name: role for role in role_result.scalars().all()}

    for role_data in BUILTIN_SYSTEM_ROLES:
        role = roles_by_name.get(role_data["name"])
        if role is None:
            role = Role(**role_data)
            session.add(role)
            roles_by_name[role.name] = role
        else:
            role.display_name = role_data["display_name"]
            role.description = role_data["description"]
            role.is_system = role_data["is_system"]

    await session.flush()

    permission_result = await session.execute(
        select(Permission).where(
            Permission.code.in_([permission["code"] for permission in PERMISSION_CATALOG])
        )
    )
    permissions_by_code = {
        permission.code: permission for permission in permission_result.scalars().all()
    }

    for permission_data in PERMISSION_CATALOG:
        permission = permissions_by_code.get(permission_data["code"])
        if permission is None:
            permission = Permission(**permission_data)
            session.add(permission)
            permissions_by_code[permission.code] = permission
        else:
            permission.resource_type = permission_data["resource_type"]
            permission.action = permission_data["action"]
            permission.display_name = permission_data["display_name"]
            permission.description = permission_data["description"]

    await session.flush()

    role_result = await session.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(Role.name.in_(DEFAULT_ROLE_PERMISSIONS.keys()))
    )
    roles_by_name = {role.name: role for role in role_result.scalars().all()}

    for role_name, permission_codes in DEFAULT_ROLE_PERMISSIONS.items():
        role = roles_by_name.get(role_name)
        if role is None:
            continue

        merged_permissions = {
            permission.code: permission for permission in role.permissions
        }
        for permission_code in permission_codes:
            merged_permissions[permission_code] = permissions_by_code[permission_code]
        role.permissions = list(merged_permissions.values())

    await session.commit()


async def _main() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        await seed_rbac(session)
        print("RBAC 权限目录初始化完成")


if __name__ == "__main__":
    asyncio.run(_main())
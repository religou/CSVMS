"""CSVMS 的唯一权限目录。

权限目录是权限定义、项目角色默认权限和系统角色默认权限的权威来源。
数据库 ``permissions`` 表是该目录的持久化投影；项目角色保存目录中项目权限的显式集合。
"""

from dataclasses import asdict, dataclass
from enum import Enum
from types import MappingProxyType
from typing import Iterable


class PermissionScope(str, Enum):
    """权限用途分类。"""

    PRESENTATION = "presentation"
    PROJECT = "project"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class PermissionDefinition:
    code: str
    resource_type: str
    action: str
    display_name: str
    description: str
    scope: PermissionScope

    @property
    def assignable_to_project_role(self) -> bool:
        return self.code.startswith("project.")

    def to_seed_data(self) -> dict[str, str]:
        data = asdict(self)
        data.pop("scope")
        return data


def _permission(
    code: str,
    resource_type: str,
    action: str,
    display_name: str,
    description: str,
) -> PermissionDefinition:
    if code.endswith(".menu"):
        scope = PermissionScope.PRESENTATION
    elif code.startswith("project."):
        scope = PermissionScope.PROJECT
    else:
        scope = PermissionScope.SYSTEM
    return PermissionDefinition(
        code=code,
        resource_type=resource_type,
        action=action,
        display_name=display_name,
        description=description,
        scope=scope,
    )


_PERMISSIONS = (
    _permission(
        "system.admin.menu",
        "system_menu",
        "access",
        "系统管理菜单",
        "显示系统管理一级菜单",
    ),
    _permission(
        "system.admin.users.menu",
        "system_menu",
        "access",
        "用户管理菜单",
        "显示用户管理菜单入口",
    ),
    _permission(
        "system.admin.users.view",
        "system_page",
        "view",
        "查看用户管理页面",
        "允许访问用户管理页面",
    ),
    _permission(
        "system.admin.users.manage",
        "system_button",
        "manage",
        "管理用户",
        "允许执行创建、编辑、分配角色、重置密码、删除等用户管理操作",
    ),
    _permission(
        "system.admin.dict.menu",
        "system_menu",
        "access",
        "字典管理菜单",
        "显示字典管理菜单入口",
    ),
    _permission(
        "system.admin.dict.view",
        "system_page",
        "view",
        "查看字典管理页面",
        "允许访问字典管理页面",
    ),
    _permission(
        "system.admin.dict.manage",
        "system_button",
        "manage",
        "管理字典",
        "允许执行字典类别和字典项管理操作",
    ),
    _permission(
        "system.admin.roles.menu",
        "system_menu",
        "access",
        "角色权限管理菜单",
        "显示角色权限管理菜单入口",
    ),
    _permission(
        "system.admin.roles.view",
        "system_page",
        "view",
        "查看角色权限管理页面",
        "允许访问角色权限管理页面",
    ),
    _permission(
        "system.admin.roles.manage",
        "system_button",
        "manage",
        "管理系统角色权限",
        "允许编辑系统角色、分配权限和删除可删除角色",
    ),
    _permission(
        "system.workflow_templates.view",
        "system_page",
        "view",
        "查看工作流模板",
        "允许查看系统范围内的工作流模板",
    ),
    _permission(
        "system.workflow_templates.manage",
        "system_button",
        "manage",
        "管理工作流模板",
        "允许创建和修改系统范围内的工作流模板",
    ),
    _permission(
        "project.dashboard.menu",
        "project_menu",
        "access",
        "项目概览菜单",
        "显示项目概览菜单入口",
    ),
    _permission(
        "project.dashboard.view",
        "project_page",
        "view",
        "查看项目概览",
        "允许访问项目概览页面",
    ),
    _permission(
        "project.documents.menu",
        "project_menu",
        "access",
        "文档管理菜单",
        "显示文档管理菜单入口",
    ),
    _permission(
        "project.documents.view",
        "project_page",
        "view",
        "查看项目文档",
        "允许访问项目文档页面",
    ),
    _permission(
        "project.documents.manage",
        "project_button",
        "manage",
        "管理项目文档",
        "允许执行项目文档写入相关操作",
    ),
    _permission(
        "project.workflows.menu",
        "project_menu",
        "access",
        "审批管理菜单",
        "显示审批管理菜单入口",
    ),
    _permission(
        "project.workflows.view",
        "project_page",
        "view",
        "查看项目审批",
        "允许访问项目审批页面",
    ),
    _permission(
        "project.workflows.manage",
        "project_button",
        "manage",
        "管理项目审批",
        "允许执行项目审批操作",
    ),
    _permission(
        "project.traceability.menu",
        "project_menu",
        "access",
        "追溯矩阵菜单",
        "显示追溯矩阵菜单入口",
    ),
    _permission(
        "project.traceability.view",
        "project_page",
        "view",
        "查看追溯矩阵",
        "允许访问追溯矩阵页面",
    ),
    _permission(
        "project.audit_log.menu",
        "project_menu",
        "access",
        "审计日志菜单",
        "显示审计日志菜单入口",
    ),
    _permission(
        "project.audit_log.view",
        "project_page",
        "view",
        "查看项目审计日志",
        "允许访问项目审计日志页面",
    ),
    _permission(
        "project.members.menu",
        "project_menu",
        "access",
        "项目成员菜单",
        "显示项目成员菜单入口",
    ),
    _permission(
        "project.members.view",
        "project_page",
        "view",
        "查看项目成员",
        "允许访问项目成员页面",
    ),
    _permission(
        "project.members.manage",
        "project_button",
        "manage",
        "管理项目成员",
        "允许添加、移除和调整项目成员角色",
    ),
    _permission(
        "project.stage.manage",
        "project_button",
        "manage",
        "管理项目阶段",
        "允许修改项目阶段",
    ),
    _permission(
        "project.settings.manage",
        "project_button",
        "manage",
        "管理项目设置",
        "允许修改项目名称、描述和其他设置",
    ),
)

_BY_CODE = MappingProxyType({permission.code: permission for permission in _PERMISSIONS})
if len(_BY_CODE) != len(_PERMISSIONS):  # pragma: no cover - import-time invariant
    raise RuntimeError("Permission Catalog 包含重复权限码")

_BASE_PROJECT_ROLE_CODES = (
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
)

_PROJECT_ROLE_DEFAULTS = MappingProxyType(
    {
        "owner": _BASE_PROJECT_ROLE_CODES
        + (
            "project.documents.manage",
            "project.workflows.manage",
            "project.members.manage",
            "project.stage.manage",
            "project.settings.manage",
        ),
        "manager": _BASE_PROJECT_ROLE_CODES
        + (
            "project.documents.manage",
            "project.workflows.manage",
            "project.members.manage",
            "project.stage.manage",
            "project.settings.manage",
        ),
        "member": _BASE_PROJECT_ROLE_CODES + ("project.documents.manage",),
        "viewer": _BASE_PROJECT_ROLE_CODES,
    }
)

_VALIDATION_ADMIN_DEFAULTS = frozenset(
    {
        "system.admin.menu",
        "system.admin.users.menu",
        "system.admin.users.view",
        "system.admin.dict.menu",
        "system.admin.dict.view",
        "system.admin.roles.menu",
        "system.admin.roles.view",
    }
)


def all_permissions() -> tuple[PermissionDefinition, ...]:
    return _PERMISSIONS


def get_permission(code: str) -> PermissionDefinition | None:
    return _BY_CODE.get(code)


def permission_seed_data() -> list[dict[str, str]]:
    return [permission.to_seed_data() for permission in _PERMISSIONS]


def default_project_role_permission_codes(profile: str) -> list[str]:
    try:
        return list(_PROJECT_ROLE_DEFAULTS[profile])
    except KeyError as exc:
        raise ValueError(f"未知的项目权限档位: {profile}") from exc


def validate_project_role_permission_codes(codes: Iterable[str]) -> list[str]:
    requested = set(codes)
    invalid = sorted(
        code
        for code in requested
        if (permission := _BY_CODE.get(code)) is None
        or not permission.assignable_to_project_role
    )
    if invalid:
        raise ValueError(f"项目角色包含无效权限码: {', '.join(invalid)}")

    return [
        permission.code
        for permission in _PERMISSIONS
        if permission.code in requested
    ]


def default_system_role_permission_codes(role_name: str) -> set[str]:
    if role_name == "admin":
        return {
            permission.code
            for permission in _PERMISSIONS
            if permission.code.startswith("system.")
        }
    if role_name == "validation_admin":
        return set(_VALIDATION_ADMIN_DEFAULTS)
    if role_name == "user":
        return set()
    raise ValueError(f"未知的系统角色: {role_name}")

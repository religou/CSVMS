"""权限服务 - RBAC 权限检查."""

from app.models.user import User


def user_has_permission(user: User, permission_code: str) -> bool:
    """检查用户是否拥有指定权限."""
    for role in user.roles:
        for perm in role.permissions:
            if perm.code == permission_code:
                return True
    return False


def user_has_role(user: User, role_name: str) -> bool:
    """检查用户是否拥有指定角色."""
    return any(role.name == role_name for role in user.roles)


def user_has_any_role(user: User, role_names: list[str]) -> bool:
    """检查用户是否拥有任一指定角色."""
    return any(role.name in role_names for role in user.roles)

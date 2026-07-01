"""API 依赖注入."""

from typing import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_token
from app.models.user import Role, User
from app.services.permission_service import user_has_permission, user_has_any_role

security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """获取当前认证用户."""
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise AuthenticationError("无效的认证令牌")
    if payload.get("type") != "access":
        raise AuthenticationError("无效的令牌类型")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("无效的认证令牌")

    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError("用户不存在")
    if not user.is_active:
        raise AuthenticationError("用户已被禁用")
    if user.is_locked:
        raise AuthenticationError("用户已被锁定")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户."""
    if not current_user.is_active:
        raise AuthenticationError("用户已被禁用")
    return current_user


def require_permissions(*permission_codes: str) -> Callable:
    """权限检查依赖 - 要求用户拥有所有指定权限."""

    async def checker(current_user: User = Depends(get_current_user)) -> User:
        for code in permission_codes:
            if not user_has_permission(current_user, code):
                raise PermissionDeniedError(f"缺少权限: {code}")
        return current_user

    return checker


def require_roles(*role_names: str) -> Callable:
    """角色检查依赖 - 要求用户拥有任一指定角色."""

    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if not user_has_any_role(current_user, list(role_names)):
            raise PermissionDeniedError(f"需要以下角色之一: {', '.join(role_names)}")
        return current_user

    return checker


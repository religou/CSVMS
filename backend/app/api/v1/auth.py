"""认证 API 路由."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, BusinessError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import (
    TokenRefresh,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])


def _build_user_response(user: User) -> UserResponse:
    permission_codes = sorted(
        {
            permission.code
            for role in user.roles
            for permission in role.permissions
        }
    )
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        roles=[role.name for role in user.roles],
        permissions=permission_codes,
    )


@router.post("/register", response_model=UserResponse)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """用户注册."""
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise BusinessError("用户名已存在")

    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise BusinessError("邮箱已被注册")

    user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        password_changed_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return _build_user_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录."""
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError("用户名或密码错误")

    # 检查是否被锁定
    if user.is_locked:
        now = datetime.now(timezone.utc)
        if user.locked_until:
            # 处理 naive datetime（从 DB 读出可能无时区信息）
            lock_time = user.locked_until
            if lock_time.tzinfo is None:
                lock_time = lock_time.replace(tzinfo=timezone.utc)
            if lock_time > now:
                raise AuthenticationError("账户已被锁定，请稍后再试")
        # 锁定时间已过，解除锁定
        user.is_locked = False
        user.failed_login_attempts = 0
        user.locked_until = None

    # 验证密码
    if not verify_password(data.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.LOGIN_FAIL_LOCK_THRESHOLD:
            user.is_locked = True
            user.locked_until = datetime.now(timezone.utc) + \
                timedelta(minutes=settings.LOGIN_FAIL_LOCK_MINUTES)
        await db.commit()
        raise AuthenticationError("用户名或密码错误")

    if not user.is_active:
        raise AuthenticationError("用户已被禁用")

    # 登录成功，重置失败次数
    user.failed_login_attempts = 0
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """刷新 access token."""
    payload = decode_token(data.refresh_token)
    if payload is None:
        raise AuthenticationError("无效的刷新令牌")
    if payload.get("type") != "refresh":
        raise AuthenticationError("无效的令牌类型")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise AuthenticationError("用户不存在或已被禁用")

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息."""
    return _build_user_response(current_user)

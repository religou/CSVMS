"""认证相关的 Pydantic 模型."""

from pydantic import BaseModel, EmailStr, field_validator

from app.core.security import validate_password_strength


class UserRegister(BaseModel):
    """用户注册请求."""

    username: str
    email: EmailStr
    full_name: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        if len(v) < 3 or len(v) > 50:
            raise ValueError("用户名长度必须在3-50字符之间")
        if not v.isalnum() and "_" not in v:
            raise ValueError("用户名只能包含字母、数字和下划线")
        return v

    @field_validator("password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        valid, msg = validate_password_strength(v)
        if not valid:
            raise ValueError(msg)
        return v


class UserLogin(BaseModel):
    """用户登录请求."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Token 响应."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Token 刷新请求."""

    refresh_token: str


class UserResponse(BaseModel):
    """用户信息响应."""

    id: str
    username: str
    email: str
    full_name: str
    is_active: bool
    roles: list[str]
    permissions: list[str] = []

    model_config = {"from_attributes": True}

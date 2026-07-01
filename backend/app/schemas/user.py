"""用户管理相关 Pydantic 模型."""

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """管理员创建用户请求."""

    username: str
    email: EmailStr
    full_name: str
    password: str
    role_codes: list[str] = []


class UserUpdate(BaseModel):
    """更新用户信息请求."""

    email: EmailStr | None = None
    full_name: str | None = None
    is_active: bool | None = None


class UserListResponse(BaseModel):
    """用户列表响应."""

    id: str
    username: str
    email: str
    full_name: str
    is_active: bool
    is_locked: bool
    roles: list["RoleResponse"]

    model_config = {"from_attributes": True}


class RoleResponse(BaseModel):
    """角色响应."""

    id: str
    name: str
    display_name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class RoleDetailResponse(RoleResponse):
    """角色详情响应."""

    is_system: bool
    permissions: list["PermissionResponse"] = []


class RoleCreate(BaseModel):
    """创建角色请求."""

    name: str
    display_name: str
    description: str | None = None
    permission_ids: list[str] = []


class RoleUpdate(BaseModel):
    """更新角色请求."""

    display_name: str | None = None
    description: str | None = None


class RolePermissionUpdate(BaseModel):
    """更新角色权限请求."""

    permission_ids: list[str]


class PermissionResponse(BaseModel):
    """权限响应."""

    id: str
    code: str
    resource_type: str
    action: str
    display_name: str

    model_config = {"from_attributes": True}


class AssignRolesRequest(BaseModel):
    """分配角色请求."""

    role_codes: list[str]


class ResetPasswordRequest(BaseModel):
    """重置密码请求."""

    new_password: str

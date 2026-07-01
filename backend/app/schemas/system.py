"""被验证系统相关 Pydantic 模型."""

from datetime import datetime

from pydantic import BaseModel


class SystemCreate(BaseModel):
    """创建系统请求."""

    code: str
    name: str
    vendor: str | None = None
    version: str | None = None
    description: str | None = None
    gxp_category: str | None = None
    gamp5_category: str | None = None
    owner_id: str | None = None


class SystemUpdate(BaseModel):
    """更新系统请求."""

    name: str | None = None
    vendor: str | None = None
    version: str | None = None
    description: str | None = None
    gxp_category: str | None = None
    gamp5_category: str | None = None
    owner_id: str | None = None
    is_active: bool | None = None


class SystemResponse(BaseModel):
    """系统响应."""

    id: str
    code: str
    name: str
    vendor: str | None = None
    version: str | None = None
    description: str | None = None
    gxp_category: str | None = None
    gamp5_category: str | None = None
    owner_id: str | None = None
    owner_name: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SystemListResponse(BaseModel):
    """系统列表分页响应."""

    items: list[SystemResponse]
    total: int
    page: int
    page_size: int

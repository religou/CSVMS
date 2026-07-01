"""字典管理 Pydantic 模型."""

from datetime import datetime

from pydantic import BaseModel


class DictItemCreate(BaseModel):
    """创建字典项."""

    code: str
    label: str
    description: str | None = None
    sort_order: int = 0
    is_enabled: bool = True
    extra: str | None = None
    permission_profile: str | None = None
    permission_codes: list[str] | None = None


class DictItemUpdate(BaseModel):
    """更新字典项."""

    label: str | None = None
    description: str | None = None
    sort_order: int | None = None
    is_enabled: bool | None = None
    extra: str | None = None
    permission_profile: str | None = None
    permission_codes: list[str] | None = None


class DictItemResponse(BaseModel):
    """字典项响应."""

    id: str
    category_id: str
    code: str
    label: str
    description: str | None = None
    sort_order: int
    is_enabled: bool
    extra: str | None = None
    permission_profile: str | None = None
    permission_codes: list[str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DictCategoryCreate(BaseModel):
    """创建字典类别."""

    code: str
    name: str
    description: str | None = None


class DictCategoryUpdate(BaseModel):
    """更新字典类别."""

    name: str | None = None
    description: str | None = None


class DictCategoryResponse(BaseModel):
    """字典类别响应."""

    id: str
    code: str
    name: str
    description: str | None = None
    is_system: bool
    created_at: datetime
    items: list[DictItemResponse] = []

    model_config = {"from_attributes": True}

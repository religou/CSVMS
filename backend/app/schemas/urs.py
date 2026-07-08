"""URS 条目与引用相关 Pydantic 模型."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class URSItemCreate(BaseModel):
    """创建 URS 条目请求."""

    description: str
    item_code: Optional[str] = None  # 保留为可选，但后端忽略


class URSItemUpdate(BaseModel):
    """更新 URS 条目请求."""

    description: str | None = None


class URSItemResponse(BaseModel):
    """URS 条目响应."""

    id: str
    document_id: str
    item_code: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class URSReferenceCreate(BaseModel):
    """创建 URS 引用请求."""

    urs_item_id: str


class URSReferenceResponse(BaseModel):
    """URS 引用响应."""

    id: str
    document_id: str
    urs_item_id: str
    item_code: str
    description: str
    source_document_id: str
    source_doc_number: str
    created_at: datetime

    model_config = {"from_attributes": True}

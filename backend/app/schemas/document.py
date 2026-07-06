"""文档相关 Pydantic 模型."""

from datetime import datetime

from pydantic import BaseModel

from app.models.document import DocumentStatus, DocumentType


class DocumentCreate(BaseModel):
    """创建文档请求."""

    title: str
    doc_type: DocumentType
    summary: str | None = None
    content: str | None = None
    project_id: str | None = None


class DocumentUpdate(BaseModel):
    """更新文档请求."""

    title: str | None = None
    content: str | None = None
    summary: str | None = None


class DocumentResponse(BaseModel):
    """文档响应."""

    id: str
    title: str
    doc_type: DocumentType
    doc_number: str
    status: DocumentStatus
    version: str
    summary: str | None = None
    project_id: str | None = None
    author_id: str
    author_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentDetailResponse(DocumentResponse):
    """文档详情响应（含内容）."""

    content: str | None = None
    versions: list["DocumentVersionResponse"] = []


class DocumentVersionResponse(BaseModel):
    """文档版本响应."""

    id: str
    version_number: int
    version_label: str
    change_reason: str | None = None
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListQuery(BaseModel):
    """文档列表查询参数."""

    doc_type: DocumentType | None = None
    status: DocumentStatus | None = None
    keyword: str | None = None
    page: int = 1
    page_size: int = 20

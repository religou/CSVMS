"""审计追踪 Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    """审计日志响应."""

    id: str
    user_id: str | None = None
    username: str
    action: str
    resource_type: str
    resource_id: str | None = None
    resource_name: str | None = None
    field_changed: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    reason: str | None = None
    timestamp: datetime
    ip_address: str | None = None

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """审计日志列表响应."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int

"""审计追踪 API 路由."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.audit import AuditLogResponse, AuditLogListResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["审计追踪"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    resource_type: str | None = None,
    resource_id: str | None = None,
    user_id: str | None = None,
    action: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """查询审计日志 - 只读，不可修改/删除."""
    service = AuditService(db)
    logs, total = await service.query(
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        action=action,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/resource/{resource_type}/{resource_id}", response_model=list[AuditLogResponse])
async def get_resource_audit_trail(
    resource_type: str,
    resource_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取特定资源的审计追踪."""
    service = AuditService(db)
    logs, _ = await service.query(
        resource_type=resource_type,
        resource_id=resource_id,
        page_size=200,
    )
    return [AuditLogResponse.model_validate(log) for log in logs]

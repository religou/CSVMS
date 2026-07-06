"""审计追踪服务."""

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.document import Document


class AuditService:
    """审计追踪服务 - 只可追加."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        action: str,
        resource_type: str,
        user_id: str | None = None,
        username: str = "system",
        resource_id: str | None = None,
        resource_name: str | None = None,
        field_changed: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """写入审计日志（只追加）."""
        entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            field_changed=field_changed,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            ip_address=ip_address,
            timestamp=datetime.now(timezone.utc),
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def query(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        user_id: str | None = None,
        action: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        project_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """查询审计日志."""
        # Build filters once, apply to both queries
        filters = []
        if resource_type:
            filters.append(AuditLog.resource_type == resource_type)
        if resource_id:
            filters.append(AuditLog.resource_id == resource_id)
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        if action:
            filters.append(AuditLog.action == action)
        if start_time:
            filters.append(AuditLog.timestamp >= start_time)
        if end_time:
            filters.append(AuditLog.timestamp <= end_time)
        if project_id:
            # 项目审计日志只包含该项目下文档相关的记录
            filters.append(
                AuditLog.resource_id.in_(
                    select(Document.id).where(Document.project_id == project_id)
                )
            )

        total_result = await self.db.execute(
            select(func.count(AuditLog.id)).where(*filters)
        )
        total = total_result.scalar() or 0

        result = await self.db.execute(
            select(AuditLog)
            .where(*filters)
            .order_by(AuditLog.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

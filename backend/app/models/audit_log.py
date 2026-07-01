"""审计追踪数据模型 - 只可追加，不可修改/删除."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base
from app.models.user import generate_uuid, utcnow


class AuditLog(Base):
    """审计日志记录."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)

    # WHO - 操作人
    user_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(50))  # 冗余存储，防止用户删除后丢失

    # WHAT - 操作内容
    action: Mapped[str] = mapped_column(String(50), index=True)  # CREATE/UPDATE/DELETE/LOGIN/LOGOUT/SIGN/APPROVE/REJECT
    resource_type: Mapped[str] = mapped_column(String(50), index=True)  # document/user/workflow/signature/system
    resource_id: Mapped[str | None] = mapped_column(CHAR(36), nullable=True, index=True)
    resource_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 变更详情
    field_changed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # WHY - 原因
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # WHEN + WHERE
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")

    __table_args__ = (
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_time_range", "timestamp", "action"),
    )

"""被验证系统数据模型."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base
from app.models.user import generate_uuid, utcnow


class System(Base):
    """被验证计算机化系统."""

    __tablename__ = "systems"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    vendor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    gxp_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gamp5_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id], lazy="selectin")


# Avoid circular import
from app.models.user import User  # noqa: E402

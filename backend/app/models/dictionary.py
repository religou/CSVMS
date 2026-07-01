"""字典管理数据模型."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base
from app.models.user import generate_uuid, utcnow


class DictCategory(Base):
    """字典类别."""

    __tablename__ = "dict_categories"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    items: Mapped[list["DictItem"]] = relationship(
        back_populates="category", lazy="selectin", cascade="all, delete-orphan",
        order_by="DictItem.sort_order",
    )


class DictItem(Base):
    """字典选项."""

    __tablename__ = "dict_items"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)
    category_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("dict_categories.id"), index=True)
    code: Mapped[str] = mapped_column(String(50), index=True)
    label: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    extra: Mapped[str | None] = mapped_column(String(200), nullable=True)
    permission_profile: Mapped[str | None] = mapped_column(String(50), nullable=True)
    permission_codes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    category: Mapped["DictCategory"] = relationship(back_populates="items")

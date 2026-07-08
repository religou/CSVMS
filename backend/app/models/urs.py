"""URS 条目与引用数据模型."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base
from app.models.user import generate_uuid, utcnow


class URSItem(Base):
    """URS 条目 - 归属于某一 URS 文档的结构化用户需求条目."""

    __tablename__ = "urs_items"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)

    # 所属 URS 文档
    document_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("documents.id"), index=True)

    item_code: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)

    created_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    document: Mapped["Document"] = relationship("Document", foreign_keys=[document_id], lazy="selectin")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by], lazy="selectin")

    __table_args__ = (
        UniqueConstraint("document_id", "item_code", name="uq_urs_items_document_item_code"),
    )


class URSReference(Base):
    """URS 引用 - Referencing_Document 与其引用的 URS_Item 之间的关联关系."""

    __tablename__ = "urs_references"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)

    # 发起引用的文档（Referencing_Document）
    document_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("documents.id"), index=True)
    urs_item_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("urs_items.id"), index=True)

    created_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Relationships
    document: Mapped["Document"] = relationship("Document", foreign_keys=[document_id], lazy="selectin")
    urs_item: Mapped["URSItem"] = relationship("URSItem", foreign_keys=[urs_item_id], lazy="selectin")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by], lazy="selectin")

    __table_args__ = (
        UniqueConstraint("document_id", "urs_item_id", name="uq_urs_references_document_urs_item"),
    )


# 避免循环导入
from app.models.document import Document  # noqa: E402
from app.models.user import User  # noqa: E402

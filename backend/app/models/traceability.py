"""追溯矩阵数据模型."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base
from app.models.user import generate_uuid, utcnow


class TraceLink(Base):
    """追溯关系 - 文档间的追溯链接."""

    __tablename__ = "trace_links"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)

    # 源文档（上游：需求端）
    source_document_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("documents.id"), index=True)
    source_section: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 章节/条目编号

    # 目标文档（下游：设计/测试端）
    target_document_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("documents.id"), index=True)
    target_section: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 关系描述
    link_type: Mapped[str] = mapped_column(String(50), default="traces_to")  # traces_to / tested_by / designed_by
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 元数据
    created_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Relationships
    source_document: Mapped["Document"] = relationship("Document", foreign_keys=[source_document_id], lazy="selectin")
    target_document: Mapped["Document"] = relationship("Document", foreign_keys=[target_document_id], lazy="selectin")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by], lazy="selectin")

    __table_args__ = (
        Index("ix_trace_links_pair", "source_document_id", "target_document_id"),
    )

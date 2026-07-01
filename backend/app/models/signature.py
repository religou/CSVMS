"""电子签名数据模型 - 符合 21 CFR Part 11."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base
from app.models.user import generate_uuid, utcnow


class ElectronicSignature(Base):
    """电子签名记录 - 不可篡改."""

    __tablename__ = "electronic_signatures"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)

    # 签名人
    user_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), index=True)

    # 签名对象
    document_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("documents.id"), index=True)
    document_version: Mapped[str] = mapped_column(String(20))  # 签名时的文档版本

    # 签名含义（审核/批准/起草）
    meaning: Mapped[str] = mapped_column(String(100))

    # 关联工作流步骤（可选）
    workflow_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("workflows.id"), nullable=True)
    workflow_step_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("workflow_steps.id"), nullable=True)

    # 完整性校验
    content_hash: Mapped[str] = mapped_column(String(128))  # SHA-256(document_content + user_id + timestamp)

    # 签名元数据
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")
    document: Mapped["Document"] = relationship("Document", lazy="selectin")

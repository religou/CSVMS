"""文档与版本数据模型."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base
from app.models.user import generate_uuid, utcnow


class DocumentType(str, enum.Enum):
    """验证文档类型."""

    VMP = "VMP"   # 验证主计划
    VP = "VP"     # 验证计划
    URS = "URS"   # 用户需求规格
    FS = "FS"     # 功能规格
    DS = "DS"     # 设计规格
    IQ = "IQ"     # 安装确认
    OQ = "OQ"     # 运行确认
    PQ = "PQ"     # 性能确认
    TM = "TM"     # 追溯矩阵
    VSR = "VSR"   # 验证总结报告
    DV = "DV"     # 偏差管理
    CC = "CC"     # 变更控制
    PR = "PR"     # 定期回顾
    RET = "RET"   # 系统退役


class DocumentStatus(str, enum.Enum):
    """文档状态."""

    DRAFT = "draft"                 # 草稿
    UNDER_REVIEW = "under_review"   # 审核中
    APPROVED = "approved"           # 已批准
    EFFECTIVE = "effective"         # 已生效
    SUPERSEDED = "superseded"       # 已替代
    RETIRED = "retired"             # 已废止


class Document(Base):
    """验证文档模型."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255))
    doc_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), index=True)
    doc_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.DRAFT, index=True
    )
    version: Mapped[str] = mapped_column(String(20), default="0.1")
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 所属项目
    project_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("projects.id"), nullable=True, index=True
    )

    # 作者与所有者
    author_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"))
    owner_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id], lazy="selectin")
    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document", order_by="DocumentVersion.version_number.desc()"
    )


class DocumentVersion(Base):
    """文档版本快照."""

    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("documents.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    version_label: Mapped[str] = mapped_column(String(20))  # e.g. "1.0", "1.1"
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="versions")


# 避免循环导入
from app.models.user import User  # noqa: E402

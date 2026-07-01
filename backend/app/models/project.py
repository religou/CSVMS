"""验证项目数据模型."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    Column,
    Table,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base
from app.models.user import generate_uuid, utcnow


class ProjectStatus(str, enum.Enum):
    """项目状态."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectRole(str, enum.Enum):
    """项目成员角色."""

    OWNER = "owner"       # 项目负责人
    MANAGER = "manager"   # 项目经理
    MEMBER = "member"     # 普通成员
    VIEWER = "viewer"     # 只读查看


class Project(Base):
    """验证项目模型."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200), index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_name: Mapped[str] = mapped_column(String(100), index=True)
    system_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("systems.id"), nullable=True, index=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), default=ProjectStatus.ACTIVE, index=True
    )
    created_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", lazy="selectin", cascade="all, delete-orphan"
    )
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by], lazy="selectin")


class ProjectMember(Base):
    """项目成员关系."""

    __tablename__ = "project_members"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("projects.id"), index=True)
    user_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(50), default=ProjectRole.MEMBER.value)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship("User", lazy="selectin")


# Avoid circular import
from app.models.user import User  # noqa: E402

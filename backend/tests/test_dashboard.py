"""首页用户维度汇总测试."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.services.dashboard_service import DashboardService


async def _make_user(db: AsyncSession, username: str) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username.upper(),
        password_hash=hash_password("User@1234"),
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def _make_project(db: AsyncSession, code: str, owner: User) -> Project:
    project = Project(
        name=f"项目{code}",
        code=code,
        system_name="系统X",
        created_by=owner.id,
    )
    db.add(project)
    await db.flush()
    db.add(
        ProjectMember(
            project_id=project.id,
            user_id=owner.id,
            role="member",
            joined_at=datetime.now(timezone.utc),
        )
    )
    return project


async def _make_doc(
    db: AsyncSession,
    *,
    author: User,
    project: Project,
    number: str,
    status: DocumentStatus,
) -> Document:
    doc = Document(
        title=f"文档{number}",
        doc_type=DocumentType.URS,
        doc_number=number,
        status=status,
        version="0.1",
        project_id=project.id,
        author_id=author.id,
    )
    db.add(doc)
    await db.flush()
    return doc


@pytest.mark.asyncio
async def test_home_summary_is_user_scoped(db_session: AsyncSession):
    """首页只统计当前用户参与的项目与自己起草的草稿。"""
    alice = await _make_user(db_session, "alice")
    bob = await _make_user(db_session, "bob")

    p_alice = await _make_project(db_session, "PA", alice)
    p_bob = await _make_project(db_session, "PB", bob)

    # alice 的草稿（应计入）
    await _make_doc(
        db_session,
        author=alice,
        project=p_alice,
        number="URS-A-1",
        status=DocumentStatus.DRAFT,
    )
    # alice 的已批准文档（不计入草稿）
    await _make_doc(
        db_session,
        author=alice,
        project=p_alice,
        number="URS-A-2",
        status=DocumentStatus.APPROVED,
    )
    # bob 的草稿（不应计入 alice）
    await _make_doc(
        db_session,
        author=bob,
        project=p_bob,
        number="URS-B-1",
        status=DocumentStatus.DRAFT,
    )
    await db_session.commit()

    summary = await DashboardService(db_session).get_home_summary(alice.id)

    assert summary["project_count"] == 1  # 仅 alice 参与的项目
    assert summary["my_draft_count"] == 1  # 仅 alice 的草稿
    assert [d["doc_number"] for d in summary["my_drafts"]] == ["URS-A-1"]

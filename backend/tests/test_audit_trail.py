"""审计轨迹的覆盖强制与行为验证（ADR-0003、ADR-0006）.

ADR-0003 要求文档全生命周期的每一次跃迁都写审计轨迹。本文件把「有没有漏记」
从人工记忆变成 CI 里的断言：

1. **覆盖**：范围内每个写端点都必须声明它产生哪些审计动作（或显式声明不产生）。
   新增写端点而未登记即报红。
2. **词表无死词**：`AuditAction` 的每个成员都必须真的有端点会产生它 —— 迁移前
   模型注释里的 `LOGIN` / `LOGOUT` 就是声明了却无人产生的死词。
3. **行为**：跑一遍完整文档生命周期，断言实际写出的动作集合与声明一致。
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.audit_log import AuditLog
from app.models.user import Role, User
from app.services.audit_service import AuditAction

from tests.test_transaction_seam import (
    IN_SCOPE_ROUTERS,
    ROUTERS_DIR,
    _write_endpoints,
)

# --------------------------------------------------------------------------- #
# 每个写端点声明它产生哪些审计动作。新增写端点必须在这里登记。
# 空集合表示「刻意不产生审计」，必须给出理由。
# --------------------------------------------------------------------------- #
EXPECTED_AUDIT_BY_ENDPOINT: dict[tuple[str, str], frozenset[AuditAction]] = {
    ("documents.py", "create_document"): frozenset({AuditAction.CREATE}),
    ("documents.py", "update_document"): frozenset({AuditAction.UPDATE}),
    ("documents.py", "delete_document"): frozenset({AuditAction.DELETE}),
    ("documents.py", "revise_document"): frozenset(
        {AuditAction.REVISE, AuditAction.SIGNATURE_VOID}
    ),
    ("documents.py", "create_urs_item"): frozenset({AuditAction.CREATE}),
    ("documents.py", "update_urs_item"): frozenset({AuditAction.UPDATE}),
    ("documents.py", "delete_urs_item"): frozenset({AuditAction.DELETE}),
    ("documents.py", "create_urs_reference"): frozenset({AuditAction.CREATE}),
    ("documents.py", "delete_urs_reference"): frozenset({AuditAction.DELETE}),
    ("workflows.py", "submit_for_review"): frozenset({AuditAction.SUBMIT}),
    ("workflows.py", "approve_workflow"): frozenset(
        {AuditAction.REVIEW, AuditAction.APPROVE}
    ),
    ("workflows.py", "reject_workflow"): frozenset({AuditAction.REJECT}),
    ("workflows.py", "return_workflow"): frozenset({AuditAction.RETURN}),
    ("workflows.py", "withdraw_workflow"): frozenset({AuditAction.WITHDRAW}),
    ("signatures.py", "create_signature"): frozenset({AuditAction.SIGN}),
    # 工作流模板不是文档，其变更不进文档审计轨迹（ADR-0003 把审计统一挂在
    # resource_type="document" 下）。模板本身的审计属于范围外债务，见下。
    ("workflows.py", "create_workflow_template"): frozenset(),
    ("workflows.py", "update_workflow_template"): frozenset(),
}

# --------------------------------------------------------------------------- #
# 已知的审计空白 —— 显式债务，不是遗忘。
# 这些路由没有 service 层，补审计等于顺带补建 service 层（与 ADR-0004 把它们
# 划在事务 seam 范围外是同一个理由）；而且它们需要 resource_type != "document"。
# --------------------------------------------------------------------------- #
KNOWN_AUDIT_GAPS = {
    "auth.py": "登录、登出、注册、刷新令牌均无审计",
    "admin.py": "建用户、删用户、改角色、重置密码均无审计",
    "dictionary.py": "字典类别与字典项的增删改均无审计",
    "systems.py": "受验证系统的增删改均无审计",
    "projects.py": "项目与成员的增删改均无审计",
    "workflows.py": "工作流模板的增改均无审计（模板非文档）",
}


def test_every_write_endpoint_declares_its_audit_events():
    """范围内每个写端点都必须登记它产生的审计动作."""
    actual: set[tuple[str, str]] = set()
    for filename in IN_SCOPE_ROUTERS:
        for func_name in _write_endpoints(ROUTERS_DIR / filename):
            actual.add((filename, func_name))

    undeclared = actual - EXPECTED_AUDIT_BY_ENDPOINT.keys()
    assert not undeclared, (
        f"这些写端点没有登记审计动作: {sorted(undeclared)}\n"
        "新增写端点 → 在 EXPECTED_AUDIT_BY_ENDPOINT 里声明它产生哪些 AuditAction；"
        "确实不产生审计的，登记成空集合并写明理由。"
    )

    stale = EXPECTED_AUDIT_BY_ENDPOINT.keys() - actual
    assert not stale, f"这些登记项已没有对应端点，请删除: {sorted(stale)}"


def test_audit_action_vocabulary_has_no_dead_words():
    """`AuditAction` 的每个成员都必须真的有端点会产生它.

    迁移前模型列注释声明了 `LOGIN` / `LOGOUT` 却没有任何代码产生，同时 ADR-0003
    词表里的 6 个词注释又没提 —— 两份词表都对不上实际写出的动作。
    """
    produced = set().union(*EXPECTED_AUDIT_BY_ENDPOINT.values())
    dead = set(AuditAction) - produced
    assert not dead, (
        f"词表里这些动作没有任何端点会产生: {sorted(a.value for a in dead)}\n"
        "要么补上产生它的端点，要么从 AuditAction 里删掉 —— 不要留死词。"
    )


def test_known_audit_gaps_are_explicit():
    """已知审计空白必须是显式登记的债务，不是沉默的遗忘."""
    assert KNOWN_AUDIT_GAPS, "审计空白清单不该为空 —— 若真已补齐，请删掉此测试"
    for router, reason in KNOWN_AUDIT_GAPS.items():
        assert reason.strip(), f"{router} 的审计空白缺少说明"


# --------------------------------------------------------------------------- #
# 行为：跑一遍完整生命周期，断言实际写出的动作
# --------------------------------------------------------------------------- #


async def _login(client: AsyncClient) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "trailuser",
            "email": "trail@example.com",
            "full_name": "Trail User",
            "password": "Test@1234",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "trailuser", "password": "Test@1234"},
    )
    return resp.json()["access_token"]


async def _promote_to_admin(session, username: str = "trailuser") -> None:
    """给用户挂上 admin 角色.

    全局文档（`project_id=None`）的 URS 条目只有系统管理员可维护，见
    `DocumentService._require_document_manage_permission`。
    """
    role = (
        await session.execute(select(Role).where(Role.name == "admin"))
    ).scalar_one_or_none()
    if role is None:
        role = Role(name="admin", display_name="管理员")
        session.add(role)
        await session.flush()

    user = (
        await session.execute(
            select(User)
            .options(selectinload(User.roles))
            .where(User.username == username)
        )
    ).scalar_one()
    if role not in user.roles:
        user.roles.append(role)
    await session.commit()


async def _actions_for(session, doc_id: str) -> list[str]:
    rows = (
        await session.execute(
            select(AuditLog.action)
            .where(
                AuditLog.resource_type == "document",
                AuditLog.resource_id == doc_id,
            )
            .order_by(AuditLog.timestamp.asc())
        )
    ).scalars().all()
    return list(rows)


@pytest.mark.asyncio
async def test_urs_lifecycle_is_fully_audited(client: AsyncClient, db_session):
    """URS 文档的起草→编辑→条目增改删，每一步都留痕."""
    token = await _login(client)
    await _promote_to_admin(db_session)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/documents",
        json={"title": "原标题", "doc_type": "URS", "content": "原正文"},
        headers=headers,
    )
    doc_id = resp.json()["id"]

    # 迁移前 create_document 一条审计都不写
    assert await _actions_for(db_session, doc_id) == ["CREATE"]

    await client.put(
        f"/api/v1/documents/{doc_id}",
        json={"title": "新标题", "content": "新正文"},
        headers=headers,
    )
    # title 与 content 各一条
    assert await _actions_for(db_session, doc_id) == ["CREATE", "UPDATE", "UPDATE"]

    item_resp = await client.post(
        f"/api/v1/documents/{doc_id}/urs-items",
        json={"description": "条目描述"},
        headers=headers,
    )
    assert item_resp.status_code in (200, 201), item_resp.text
    item_id = item_resp.json()["id"]

    await client.put(
        f"/api/v1/documents/{doc_id}/urs-items/{item_id}",
        json={"description": "修改后的条目描述"},
        headers=headers,
    )
    await client.delete(
        f"/api/v1/documents/{doc_id}/urs-items/{item_id}",
        headers=headers,
    )

    actions = await _actions_for(db_session, doc_id)
    assert actions == [
        "CREATE",  # 起草文档
        "UPDATE",  # title
        "UPDATE",  # content
        "CREATE",  # 新增 URS 条目
        "UPDATE",  # 修改条目描述
        "DELETE",  # 删除 URS 条目
    ], f"实际动作序列: {actions}"


@pytest.mark.asyncio
async def test_update_writes_one_row_per_changed_field(
    client: AsyncClient, db_session
):
    """未变更的字段不产生审计行 —— 差异由 service 计算（ADR-0006）."""
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/documents",
        json={"title": "标题", "doc_type": "URS", "content": "正文"},
        headers=headers,
    )
    doc_id = resp.json()["id"]

    # title 传同值、content 传新值 → 只该有 content 一条
    await client.put(
        f"/api/v1/documents/{doc_id}",
        json={"title": "标题", "content": "改过的正文"},
        headers=headers,
    )

    rows = (
        await db_session.execute(
            select(AuditLog.field_changed).where(
                AuditLog.resource_id == doc_id,
                AuditLog.action == AuditAction.UPDATE.value,
            )
        )
    ).scalars().all()
    assert list(rows) == ["content"], f"实际字段: {list(rows)}"


@pytest.mark.asyncio
async def test_audit_rows_of_one_event_share_a_timestamp(
    client: AsyncClient, db_session
):
    """一次事件展开的多行共用一个时间戳 —— 以便还原「这是一次操作」."""
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/documents",
        json={"title": "标题", "doc_type": "URS", "content": "正文"},
        headers=headers,
    )
    doc_id = resp.json()["id"]

    await client.put(
        f"/api/v1/documents/{doc_id}",
        json={"title": "新标题", "content": "新正文"},
        headers=headers,
    )

    stamps = (
        await db_session.execute(
            select(AuditLog.timestamp).where(
                AuditLog.resource_id == doc_id,
                AuditLog.action == AuditAction.UPDATE.value,
            )
        )
    ).scalars().all()
    assert len(stamps) == 2
    assert len(set(stamps)) == 1, "同一次编辑的两条审计行时间戳应当相同"

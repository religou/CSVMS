"""请求 seam 上的事务归属 —— 强制手段与行为验证（ADR-0004）.

本文件承担三件事：

1. **强制**：service 层不得自行提交。白名单是一份**递减**的清单，每迁移一个方法就
   把对应计数减一，终态只剩 `create_urs_item` 的 savepoint 一处。
2. **强制**：范围内路由的每个写端点，要么带 `@transactional`，要么还在待迁移清单上。
   忘记加装饰器的后果是静默不落库，所以这条断言是必需的。
3. **行为**：审计轨迹与它所记录的状态变更必须同生共死。
"""

import ast
import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.api.transaction import TRANSACTIONAL_MARKER
from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.urs import URSItem
from app.models.user import Role, User
from app.schemas.urs import URSItemCreate
from app.services.audit_service import AuditService
from app.services.document_service import DocumentService

APP_DIR = Path(__file__).resolve().parents[1] / "app"
SERVICES_DIR = APP_DIR / "services"
ROUTERS_DIR = APP_DIR / "api" / "v1"

# --------------------------------------------------------------------------- #
# 递减白名单：service 层残留的自行提交
#
# 起点是 23 处（workflow 7 + document 9 + signature 1 + audit 1 + project 5）。
# 每迁移一个「端点 + 其独占的 service 方法」，就把这里的数字减一。
# 当前 5 处，全部属 project_service —— 它服务范围外的 projects.py，但可从范围内的
# 只读权限检查路径（document_service._require_document_manage_permission）抵达，
# 因此作为显式已知债务留在白名单上，而不是埋着的雷。
# 本次范围（documents / workflows / signatures）已归零。
# --------------------------------------------------------------------------- #
ALLOWED_COMMITS: dict[str, int] = {
    "workflow_service.py": 0,  # 已迁移：全部 7 个方法
    "document_service.py": 0,  # 已迁移：全部 9 个方法
    "signature_service.py": 0,  # 已迁移：sign
    "audit_service.py": 0,  # 已迁移：log
    # 范围外（服务 projects.py），但可从范围内的只读权限检查路径抵达 —— 显式已知债务
    "project_service.py": 5,
}

ALLOWED_ROLLBACKS: dict[str, int] = {
    # 已清零：create_urs_item 的 item_code 冲突重试改用 savepoint(begin_nested)，
    # 只回滚这一次插入，不动本请求已暂存的其余工作。
}

# --------------------------------------------------------------------------- #
# 待迁移的写端点：尚未跨过 seam 的 post/put/delete
# 迁移一个就从这里删一行。清空即本次范围完成。
# --------------------------------------------------------------------------- #
PENDING_WRITE_ENDPOINTS: set[tuple[str, str]] = set()  # 已清空：本次范围迁移完成

IN_SCOPE_ROUTERS = ("documents.py", "workflows.py", "signatures.py")
WRITE_METHODS = {"post", "put", "delete", "patch"}


def _count_session_calls(path: Path, method: str) -> int:
    """数出文件里 `<something>.db.<method>()` 形式的调用次数."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_node = node.func
        if isinstance(func_node, ast.Attribute) and func_node.attr == method:
            count += 1
    return count


def test_services_do_not_commit():
    """service 层不得自行提交；白名单随迁移递减（ADR-0004）."""
    actual = {
        path.name: _count_session_calls(path, "commit")
        for path in sorted(SERVICES_DIR.glob("*_service.py"))
    }
    expected = {name: ALLOWED_COMMITS.get(name, 0) for name in actual}

    assert actual == expected, (
        "service 层的提交数与白名单不符。\n"
        f"实际: {actual}\n期望: {expected}\n"
        "迁移了一个方法 → 把 ALLOWED_COMMITS 里对应的数字减一。\n"
        "新增了提交 → 不要加白名单，把提交交给 @transactional。"
    )


def test_services_do_not_rollback():
    """service 层不得自行回滚 —— 单事务下会抹掉整个请求已暂存的工作."""
    actual = {
        path.name: _count_session_calls(path, "rollback")
        for path in sorted(SERVICES_DIR.glob("*_service.py"))
    }
    expected = {name: ALLOWED_ROLLBACKS.get(name, 0) for name in actual}

    assert actual == expected, (
        "service 层的回滚数与白名单不符。\n"
        f"实际: {actual}\n期望: {expected}\n"
        "需要局部回滚 → 用 savepoint(begin_nested)，不要回滚整个事务。"
    )


def _write_endpoints(path: Path) -> list[str]:
    """取出文件里所有写端点（post/put/delete/patch）的函数名."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        for deco in node.decorator_list:
            target = deco.func if isinstance(deco, ast.Call) else deco
            if (
                isinstance(target, ast.Attribute)
                and target.attr in WRITE_METHODS
                and isinstance(target.value, ast.Name)
                and target.value.id == "router"
            ):
                names.append(node.name)
    return names


def test_every_write_endpoint_is_transactional_or_pending():
    """写端点要么跨过 seam，要么还在待迁移清单上 —— 不允许两者都不是."""
    from app.api.v1 import documents, signatures, workflows

    modules = {
        "documents.py": documents,
        "workflows.py": workflows,
        "signatures.py": signatures,
    }

    undecorated: set[tuple[str, str]] = set()
    for filename in IN_SCOPE_ROUTERS:
        path = ROUTERS_DIR / filename
        for func_name in _write_endpoints(path):
            handler = getattr(modules[filename], func_name)
            if not getattr(handler, TRANSACTIONAL_MARKER, False):
                undecorated.add((filename, func_name))

    unexpected = undecorated - PENDING_WRITE_ENDPOINTS
    assert not unexpected, (
        f"这些写端点既没有 @transactional 也不在待迁移清单上: {sorted(unexpected)}\n"
        "新增写端点 → 加 @transactional（写在 @router.xxx 之下）。"
    )

    already_done = PENDING_WRITE_ENDPOINTS - undecorated
    assert not already_done, (
        f"这些端点已经带上 @transactional，请从 PENDING_WRITE_ENDPOINTS 中删除: "
        f"{sorted(already_done)}"
    )


# --------------------------------------------------------------------------- #
# 行为：审计轨迹与状态变更同生共死
# --------------------------------------------------------------------------- #


async def _login(client) -> str:
    payload = {
        "username": "seamuser",
        "email": "seamuser@example.com",
        "password": "Test@1234",
        "full_name": "事务 seam",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code in (200, 201), resp.text
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "seamuser", "password": "Test@1234"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _create_doc(client, headers) -> str:
    resp = await client.post(
        "/api/v1/documents",
        json={"title": "原标题", "doc_type": "URS", "content": "原正文"},
        headers=headers,
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


async def _count_update_audits(session, doc_id: str) -> int:
    return (
        await session.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.resource_type == "document",
                AuditLog.resource_id == doc_id,
                AuditLog.action == "UPDATE",
            )
        )
    ).scalar() or 0


@pytest.mark.asyncio
async def test_update_writes_document_and_audit_together(client, db_session):
    """正常路径：文档变更与每个变更字段的审计轨迹一并落库."""
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    doc_id = await _create_doc(client, headers)

    resp = await client.put(
        f"/api/v1/documents/{doc_id}",
        json={"title": "新标题", "content": "新正文"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    doc = (
        await db_session.execute(select(Document).where(Document.id == doc_id))
    ).scalar_one()
    assert doc.title == "新标题"
    # title 与 content 各一条
    assert await _count_update_audits(db_session, doc_id) == 2


@pytest.mark.asyncio
async def test_audit_failure_rolls_back_the_document_change(
    client, db_session, monkeypatch
):
    """审计写入失败时，文档变更也不得落库。

    ⚠️ 这个测试是被**故意反转**过的（ADR-0004 / 本次迁移的红绿证据）。
    迁移前它的断言是「文档已改、审计缺失」—— 那时 service 先提交文档变更，随后
    每个变更字段各调一次自行提交的审计写入，最多 4 个事务，崩在中间就破坏
    ADR-0003。迁移后整条请求是一个事务，所以断言翻转为「文档未改、审计未写」。
    看到断言方向和历史记录相反，不是它坏了。
    """
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    doc_id = await _create_doc(client, headers)

    async def boom(self, *args, **kwargs):
        raise RuntimeError("模拟审计写入失败")

    monkeypatch.setattr(AuditService, "record", boom)

    with pytest.raises(RuntimeError, match="模拟审计写入失败"):
        await client.put(
            f"/api/v1/documents/{doc_id}",
            json={"title": "新标题", "content": "新正文"},
            headers=headers,
        )

    doc = (
        await db_session.execute(select(Document).where(Document.id == doc_id))
    ).scalar_one()
    assert doc.title == "原标题", "文档变更随审计失败一起回滚"
    assert await _count_update_audits(db_session, doc_id) == 0


# --------------------------------------------------------------------------- #
# 行为：savepoint 只回滚冲突的那一次插入，不动同事务已暂存的工作
# --------------------------------------------------------------------------- #

STAGED_MARKER = "同事务中的既有工作"


async def _seed_admin_and_urs_doc(session, suffix: str) -> tuple[User, Document]:
    """在当前事务内建出 admin 用户与一份草稿 URS 文档 —— 只 flush，不提交."""
    role = (
        await session.execute(select(Role).where(Role.name == "admin"))
    ).scalar_one_or_none()
    if role is None:
        role = Role(name="admin", display_name="管理员")
        session.add(role)
        await session.flush()

    user = User(
        username=f"savepoint-{suffix}",
        email=f"savepoint-{suffix}@example.com",
        full_name="savepoint",
        password_hash=hash_password("Admin@1234"),
    )
    user.roles = [role]
    session.add(user)
    await session.flush()

    document = Document(
        title="URS 文档",
        doc_type=DocumentType.URS,
        doc_number=f"URS-SAVEPOINT-{suffix}",
        status=DocumentStatus.DRAFT,
        project_id=None,
        author_id=user.id,
    )
    session.add(document)
    await session.flush()
    return user, document


@pytest.mark.asyncio
async def test_item_code_collision_does_not_discard_staged_work(tx_session):
    """item_code 冲突重试只回滚这一次插入（ADR-0004 的 savepoint 契约）.

    迁移前 `create_urs_item` 在 `IntegrityError` 时直接回滚整个事务，会抹掉本请求
    已暂存的其余工作 —— 之所以没炸，只因为它恰好是那个请求里唯一的写操作。改用
    savepoint 后不会。本测试在同一个**未提交**事务里断言这件事，这正是
    `tx_session` fixture 存在的理由。
    """
    suffix = uuid.uuid4().hex[:12]
    user, document = await _seed_admin_and_urs_doc(tx_session, suffix)
    service = DocumentService(tx_session)

    # 同一事务里先暂存一笔无关的工作，它必须在冲突重试之后依然存活
    tx_session.add(
        AuditLog(
            user_id=user.id,
            username=user.username,
            action="CREATE",
            resource_type="document",
            resource_id=document.id,
            resource_name=STAGED_MARKER,
        )
    )
    await tx_session.flush()

    first = await service.create_urs_item(
        document.id, URSItemCreate(description="第一条"), user
    )
    taken_code = first.item_code

    # 让下一次编号生成先撞一次已占用的编号，再回到真实生成逻辑
    real_generate = service._generate_item_code
    calls = {"n": 0}

    async def colliding(document_id: str, doc_number: str) -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            return taken_code
        return await real_generate(document_id, doc_number)

    service._generate_item_code = colliding  # type: ignore[method-assign]

    second = await service.create_urs_item(
        document.id, URSItemCreate(description="第二条"), user
    )

    assert calls["n"] == 2, "应当发生过一次冲突并重试"
    assert second.item_code != taken_code

    staged = (
        await tx_session.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.resource_name == STAGED_MARKER
            )
        )
    ).scalar()
    assert staged == 1, "savepoint 的回滚抹掉了同事务中已暂存的工作"

    codes = (
        (
            await tx_session.execute(
                select(URSItem.item_code).where(URSItem.document_id == document.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(codes) == 2, "冲突的那次插入不得留下痕迹"
    assert sorted(codes) == sorted([taken_code, second.item_code])

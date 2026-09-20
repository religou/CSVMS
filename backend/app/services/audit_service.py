"""审计轨迹服务 - 只可追加（ADR-0003、ADR-0006）.

写入侧的 interface 是「记录一次文档生命周期事件」，而不是「写一条日志」：调用方
描述发生了什么，怎么落成审计行由本 module 决定。`resource_type`、操作人用户名、
`resource_name` 文案、审核步与批准步的区分、以及一次事件展开成多行（字段变更、
签名失效）都在 interface 之后。
"""

import enum
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.user import User
from app.models.workflow import ActionType, StepType

#: 文档全生命周期的每一次跃迁都记在文档自己名下（ADR-0003）。
_RESOURCE_TYPE_DOCUMENT = "document"

#: 操作人无法解析时的兜底用户名。
_SYSTEM_ACTOR = "system"


class AuditAction(str, enum.Enum):
    """ADR-0003 规范的审计动作词表.

    数据库列仍是 `String`：ADR-0003 的「自由文本 String，非枚举」说的是**列类型**，
    目的是让词表可以演进而不必迁移。本枚举只约束写入侧，因此扩充词表依旧免迁移，
    同时把拼错 action 变成类型错误（ADR-0006）。
    """

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SUBMIT = "SUBMIT"
    REVIEW = "REVIEW"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    RETURN = "RETURN"
    WITHDRAW = "WITHDRAW"
    SIGN = "SIGN"
    REVISE = "REVISE"
    SIGNATURE_VOID = "SIGNATURE_VOID"


@dataclass(frozen=True)
class _Row:
    """事件展开后的一条待写入审计行."""

    action: AuditAction
    resource_name: str | None = None
    field_changed: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class DocumentEvent:
    """文档生命周期事件 —— 审计轨迹写入侧的唯一输入.

    子类各自知道要落成哪些审计行。一次事件可以展开成多行，调用方不需要循环。
    """

    document_id: str

    def rows(self) -> list[_Row]:  # pragma: no cover - 抽象方法
        raise NotImplementedError


# ---------- 文档自身 ----------


@dataclass(frozen=True)
class DocumentCreated(DocumentEvent):
    """起草了一份新文档."""

    doc_number: str
    title: str

    def rows(self) -> list[_Row]:
        return [
            _Row(
                AuditAction.CREATE,
                resource_name=f"创建文档 {self.doc_number}：{self.title}",
            )
        ]


@dataclass(frozen=True)
class FieldChange:
    """一个字段的前后值."""

    field: str
    old_value: str | None
    new_value: str | None


@dataclass(frozen=True)
class DocumentFieldsChanged(DocumentEvent):
    """编辑了草稿的若干字段 —— 每个变更字段各一条审计行."""

    title: str
    changes: tuple[FieldChange, ...] = ()

    def rows(self) -> list[_Row]:
        return [
            _Row(
                AuditAction.UPDATE,
                resource_name=self.title,
                field_changed=change.field,
                old_value=change.old_value,
                new_value=change.new_value,
            )
            for change in self.changes
        ]


@dataclass(frozen=True)
class DocumentDeleted(DocumentEvent):
    """删除了草稿文档."""

    doc_number: str
    title: str

    def rows(self) -> list[_Row]:
        return [
            _Row(
                AuditAction.DELETE,
                resource_name=f"删除文档 {self.doc_number}：{self.title}",
            )
        ]


# ---------- 发起变更（ADR-0002） ----------


@dataclass(frozen=True)
class DocumentRevised(DocumentEvent):
    """对已批准文档发起变更：批准状态被破坏，退回草稿."""

    old_status: str
    new_status: str
    change_reason: str

    def rows(self) -> list[_Row]:
        return [
            _Row(
                AuditAction.REVISE,
                resource_name="作废原批准状态，退回草稿",
                field_changed="status",
                old_value=self.old_status,
                new_value=self.new_status,
                reason=self.change_reason,
            )
        ]


@dataclass(frozen=True)
class VoidedSignature:
    """被变更取代的一条电子签名（签名记录本身不销毁）."""

    signature_id: str
    signer_name: str
    meaning: str


@dataclass(frozen=True)
class SignaturesVoided(DocumentEvent):
    """被取代版本上的电子签名不再生效 —— 每条签名各一条审计行."""

    approved_version: str
    change_reason: str
    signatures: tuple[VoidedSignature, ...] = ()

    def rows(self) -> list[_Row]:
        return [
            _Row(
                AuditAction.SIGNATURE_VOID,
                resource_name=(
                    f"电子签名失效：{sig.signer_name}「{sig.meaning}」（签名 {sig.signature_id}）"
                ),
                field_changed="signature",
                old_value=f"有效(批准 {self.approved_version})",
                new_value="被变更取代",
                reason=self.change_reason,
            )
            for sig in self.signatures
        ]


# ---------- 审批工作流 ----------


@dataclass(frozen=True)
class DocumentSubmitted(DocumentEvent):
    """提交文档进入审批流程."""

    workflow_id: str

    def rows(self) -> list[_Row]:
        return [
            _Row(
                AuditAction.SUBMIT,
                resource_name=f"提交文档审批（工作流 {self.workflow_id}）",
            )
        ]


@dataclass(frozen=True)
class StepDecided(DocumentEvent):
    """审核步/批准步上的一次决策动作，已绑定电子签名（ADR-0001）."""

    workflow_id: str
    signature_id: str
    step_type: StepType
    action: ActionType
    comment: str | None = None

    def rows(self) -> list[_Row]:
        if self.action == ActionType.REJECT:
            audit_action, label = AuditAction.REJECT, "审批拒绝"
        elif self.step_type == StepType.REVIEW:
            audit_action, label = AuditAction.REVIEW, "审核通过"
        else:
            audit_action, label = AuditAction.APPROVE, "批准通过，文档生效"
        return [
            _Row(
                audit_action,
                resource_name=(
                    f"{label}（工作流 {self.workflow_id}，电子签名 {self.signature_id}）"
                ),
                reason=self.comment,
            )
        ]


@dataclass(frozen=True)
class WorkflowReturned(DocumentEvent):
    """退回修改."""

    workflow_id: str
    comment: str | None = None

    def rows(self) -> list[_Row]:
        return [
            _Row(
                AuditAction.RETURN,
                resource_name=f"退回修改（工作流 {self.workflow_id}）",
                reason=self.comment,
            )
        ]


@dataclass(frozen=True)
class WorkflowWithdrawn(DocumentEvent):
    """发起人撤回审批."""

    workflow_id: str

    def rows(self) -> list[_Row]:
        return [
            _Row(
                AuditAction.WITHDRAW,
                resource_name=f"撤回审批（工作流 {self.workflow_id}）",
            )
        ]


@dataclass(frozen=True)
class DocumentSigned(DocumentEvent):
    """工作流之外的独立电子签名（ADR-0005）."""

    meaning: str

    def rows(self) -> list[_Row]:
        return [_Row(AuditAction.SIGN, resource_name=f"电子签名: {self.meaning}")]


# ---------- URS 条目与引用 ----------


@dataclass(frozen=True)
class UrsItemAdded(DocumentEvent):
    """新增 URS 条目."""

    item_code: str

    def rows(self) -> list[_Row]:
        return [
            _Row(AuditAction.CREATE, resource_name=f"新增 URS 条目 {self.item_code}")
        ]


@dataclass(frozen=True)
class UrsItemDescriptionChanged(DocumentEvent):
    """修改 URS 条目描述 —— 需求原文的变更，必须留痕."""

    item_code: str
    old_value: str | None
    new_value: str | None

    def rows(self) -> list[_Row]:
        return [
            _Row(
                AuditAction.UPDATE,
                resource_name=f"修改 URS 条目 {self.item_code} 描述",
                field_changed="urs_item.description",
                old_value=self.old_value,
                new_value=self.new_value,
            )
        ]


@dataclass(frozen=True)
class UrsItemRemoved(DocumentEvent):
    """删除 URS 条目."""

    item_code: str

    def rows(self) -> list[_Row]:
        return [
            _Row(AuditAction.DELETE, resource_name=f"删除 URS 条目 {self.item_code}")
        ]


@dataclass(frozen=True)
class UrsReferenceAdded(DocumentEvent):
    """关联 URS 条目."""

    item_code: str

    def rows(self) -> list[_Row]:
        return [
            _Row(AuditAction.CREATE, resource_name=f"关联 URS 条目 {self.item_code}")
        ]


@dataclass(frozen=True)
class UrsReferenceRemoved(DocumentEvent):
    """取消关联 URS 条目."""

    item_code: str

    def rows(self) -> list[_Row]:
        return [
            _Row(AuditAction.DELETE, resource_name=f"取消关联 URS 条目 {self.item_code}")
        ]


class AuditService:
    """审计追踪服务 - 只可追加."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        event: DocumentEvent,
        *,
        actor: User | str | None,
        ip_address: str | None = None,
    ) -> list[AuditLog]:
        """记录一次文档生命周期事件（只 stage 不提交，ADR-0004）.

        `actor` 可以是已加载的 `User`、用户 id，或 `None`（系统动作）。同一事件
        展开出的多行共用一个时间戳，以便还原「这是一次操作」。
        """
        user_id, username = await self._resolve_actor(actor)
        timestamp = datetime.now(timezone.utc)

        entries = [
            AuditLog(
                user_id=user_id,
                username=username,
                action=row.action.value,
                resource_type=_RESOURCE_TYPE_DOCUMENT,
                resource_id=event.document_id,
                resource_name=row.resource_name,
                field_changed=row.field_changed,
                old_value=row.old_value,
                new_value=row.new_value,
                reason=row.reason,
                ip_address=ip_address,
                timestamp=timestamp,
            )
            for row in event.rows()
        ]
        for entry in entries:
            self.db.add(entry)
        await self.db.flush()
        return entries

    async def _resolve_actor(
        self, actor: User | str | None
    ) -> tuple[str | None, str]:
        """解析操作人：用户名冗余存储，用户被删后仍可追溯."""
        if actor is None:
            return None, _SYSTEM_ACTOR
        if isinstance(actor, User):
            return actor.id, actor.username
        user = await self.db.get(User, actor)
        return actor, user.username if user else _SYSTEM_ACTOR

    async def query(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        user_id: str | None = None,
        action: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        project_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """查询审计日志."""
        # Build filters once, apply to both queries
        filters = []
        if resource_type:
            filters.append(AuditLog.resource_type == resource_type)
        if resource_id:
            filters.append(AuditLog.resource_id == resource_id)
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        if action:
            filters.append(AuditLog.action == action)
        if start_time:
            filters.append(AuditLog.timestamp >= start_time)
        if end_time:
            filters.append(AuditLog.timestamp <= end_time)
        if project_id:
            # 项目审计日志只包含该项目下文档相关的记录
            filters.append(
                AuditLog.resource_id.in_(
                    select(Document.id).where(Document.project_id == project_id)
                )
            )

        total_result = await self.db.execute(
            select(func.count(AuditLog.id)).where(*filters)
        )
        total = total_result.scalar() or 0

        result = await self.db.execute(
            select(AuditLog)
            .where(*filters)
            .order_by(AuditLog.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

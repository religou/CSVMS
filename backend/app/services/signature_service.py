"""电子签名服务 - 21 CFR Part 11 合规.

本 module 是**写入一条电子签名的唯一实现**（ADR-0005）。重认证、签名含义推导、
内容哈希与版本绑定都在 interface 之后；调用方只需要说明「谁、为什么签、用什么凭据」，
**无法指定签名含义**。
"""

import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.core.security import verify_password
from app.models.document import Document
from app.models.signature import ElectronicSignature, SignatureType
from app.models.user import User
from app.models.workflow import ActionType, StepType, Workflow, WorkflowStep

# 签名含义是具法律效力的文本，由系统按签署场景固定生成（CONTEXT.md「签名含义」）。
_STEP_MEANING_REJECT = "我已审核此文档，予以退回"
_STEP_MEANING_APPROVE = "我已批准此文档，同意生效"
_STEP_MEANING_REVIEW = "我已审核此文档，内容准确完整"

_STANDALONE_MEANINGS: dict[SignatureType, str] = {
    SignatureType.DRAFT: "我起草了此文档，内容由本人编制",
}


class SignatureService:
    """电子签名服务."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- 签名写入：唯一的两个入口 ----------

    async def sign_for_step(
        self,
        *,
        actor_id: str,
        password: str,
        workflow: Workflow,
        step: WorkflowStep,
        action: ActionType,
        ip_address: str | None = None,
    ) -> ElectronicSignature:
        """审批动作产生的签名：含义由步骤类型与动作推导.

        调用方应在**状态变更之前**调用它 —— 重认证失败时不该留下任何改动。
        只 stage 不提交，事务归属在请求 seam 上（ADR-0004）。
        """
        signer = await self._authenticate(actor_id, password)
        document = await self._require_document(workflow.document_id)
        return await self._record(
            signer=signer,
            document=document,
            meaning=self._meaning_for_step(step.step_type, action),
            ip_address=ip_address,
            workflow=workflow,
            step=step,
        )

    async def sign_standalone(
        self,
        *,
        actor_id: str,
        password: str,
        document_id: str,
        signature_type: SignatureType,
        ip_address: str | None = None,
    ) -> ElectronicSignature:
        """工作流之外的独立签名：含义由签署类型推导.

        不绑定工作流步骤 —— 需要绑定步骤的签名一律走 `sign_for_step`，
        以免调用方把签名挂到任意步骤上。
        """
        signer = await self._authenticate(actor_id, password)
        document = await self._require_document(document_id)
        return await self._record(
            signer=signer,
            document=document,
            meaning=self._meaning_for_type(signature_type),
            ip_address=ip_address,
        )

    # ---------- 查询 ----------

    async def verify_signature(self, signature_id: str) -> bool:
        """返回签名记录的有效标记.

        注意：当前只读取存储的 `is_valid`，并不重算内容哈希。真正的篡改检测需要先
        确定「拿哪一份内容重算」（活动文档还是 `DocumentVersion` 快照），那是压在
        ADR-0002 上的独立议题，不在 ADR-0005 范围内。
        """
        sig = await self.db.get(ElectronicSignature, signature_id)
        if not sig:
            raise BusinessError("签名记录不存在")
        return sig.is_valid

    async def get_signatures_for_document(self, document_id: str) -> list[ElectronicSignature]:
        """获取文档的所有签名."""
        result = await self.db.execute(
            select(ElectronicSignature)
            .where(ElectronicSignature.document_id == document_id)
            .order_by(ElectronicSignature.timestamp.asc())
        )
        return list(result.scalars().all())

    async def get_signature(self, signature_id: str) -> ElectronicSignature:
        """获取签名详情."""
        sig = await self.db.get(ElectronicSignature, signature_id)
        if not sig:
            raise BusinessError("签名记录不存在")
        return sig

    # ---------- 内部 ----------

    @staticmethod
    def _meaning_for_step(step_type: StepType, action: ActionType) -> str:
        """按步骤类型与动作生成固定签名含义."""
        if action == ActionType.REJECT:
            return _STEP_MEANING_REJECT
        if step_type == StepType.APPROVE:
            return _STEP_MEANING_APPROVE
        return _STEP_MEANING_REVIEW

    @staticmethod
    def _meaning_for_type(signature_type: SignatureType) -> str:
        """按签署类型生成固定签名含义."""
        try:
            return _STANDALONE_MEANINGS[signature_type]
        except KeyError:  # pragma: no cover - 枚举新增成员时必须同步补措辞
            raise BusinessError(f"签署类型 {signature_type} 尚未配置签名含义") from None

    async def _authenticate(self, actor_id: str, password: str) -> User:
        """签名前重认证：身份组件取自当前用户，密码为即时重新输入组件.

        §11.200 的双组件要求；用户名不进请求体，避免冒签（ADR-0001）。
        """
        user = await self.db.get(User, actor_id)
        if not user:
            raise BusinessError("用户不存在")
        if not verify_password(password, user.password_hash):
            raise BusinessError("身份验证失败：密码错误")
        if not user.is_active:
            raise BusinessError("账户已禁用")
        return user

    async def _require_document(self, document_id: str) -> Document:
        document = await self.db.get(Document, document_id)
        if not document:
            raise BusinessError("文档不存在")
        return document

    async def _record(
        self,
        *,
        signer: User,
        document: Document,
        meaning: str,
        ip_address: str | None,
        workflow: Workflow | None = None,
        step: WorkflowStep | None = None,
    ) -> ElectronicSignature:
        """构造并暂存签名记录：内容哈希 + 版本绑定（不提交）."""
        timestamp = datetime.now(timezone.utc)
        content_hash = hashlib.sha256(
            f"{document.content or ''}{signer.id}{timestamp.isoformat()}".encode("utf-8")
        ).hexdigest()

        signature = ElectronicSignature(
            # 直接赋关系对象，使 signature.user / .document 在本事务内即可读，
            # 免得响应构造与审计轨迹触发异步 lazy load
            user=signer,
            document=document,
            document_version=document.version,
            meaning=meaning,
            workflow_id=workflow.id if workflow else None,
            workflow_step_id=step.id if step else None,
            content_hash=content_hash,
            ip_address=ip_address,
            timestamp=timestamp,
            is_valid=True,
        )
        self.db.add(signature)
        await self.db.flush()
        return signature

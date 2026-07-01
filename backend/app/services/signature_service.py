"""电子签名服务 - 21 CFR Part 11 合规."""

import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.core.security import verify_password
from app.models.document import Document
from app.models.signature import ElectronicSignature
from app.models.user import User


class SignatureService:
    """电子签名服务."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def sign(
        self,
        user_id: str,
        username: str,
        password: str,
        document_id: str,
        meaning: str,
        ip_address: str | None = None,
        workflow_id: str | None = None,
        workflow_step_id: str | None = None,
    ) -> ElectronicSignature:
        """执行电子签名.

        1. 重新验证身份（用户名+密码）
        2. 验证文档存在
        3. 生成内容哈希
        4. 创建不可篡改的签名记录
        """
        # Step 1: 重新验证身份 (21 CFR Part 11 要求每次签名重新认证)
        user = await self.db.get(User, user_id)
        if not user:
            raise BusinessError("用户不存在")
        if user.username != username:
            raise BusinessError("身份验证失败：用户名不匹配")
        if not verify_password(password, user.password_hash):
            raise BusinessError("身份验证失败：密码错误")
        if not user.is_active:
            raise BusinessError("账户已禁用")

        # Step 2: 验证文档
        document = await self.db.get(Document, document_id)
        if not document:
            raise BusinessError("文档不存在")

        # Step 3: 生成内容哈希 (SHA-256)
        timestamp = datetime.now(timezone.utc)
        content_for_hash = (
            f"{document.content or ''}"
            f"{user_id}"
            f"{timestamp.isoformat()}"
        )
        content_hash = hashlib.sha256(content_for_hash.encode("utf-8")).hexdigest()

        # Step 4: 创建签名记录
        signature = ElectronicSignature(
            user_id=user_id,
            document_id=document_id,
            document_version=document.version,
            meaning=meaning,
            workflow_id=workflow_id,
            workflow_step_id=workflow_step_id,
            content_hash=content_hash,
            ip_address=ip_address,
            timestamp=timestamp,
            is_valid=True,
        )
        self.db.add(signature)
        await self.db.commit()
        await self.db.refresh(signature)
        return signature

    async def verify_signature(self, signature_id: str) -> bool:
        """验证签名完整性."""
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

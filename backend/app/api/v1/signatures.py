"""电子签名 API 路由."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.signature import SignatureRequest, SignatureResponse, SignatureVerifyResponse
from app.services.signature_service import SignatureService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/signatures", tags=["电子签名"])


@router.post("", response_model=SignatureResponse)
async def create_signature(
    data: SignatureRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """执行电子签名 - 需重新验证身份."""
    ip_address = request.client.host if request.client else None

    service = SignatureService(db)
    sig = await service.sign(
        user_id=current_user.id,
        username=data.username,
        password=data.password,
        document_id=data.document_id,
        meaning=data.meaning,
        ip_address=ip_address,
        workflow_id=data.workflow_id,
        workflow_step_id=data.workflow_step_id,
    )

    # 记录审计日志
    audit = AuditService(db)
    await audit.log(
        action="SIGN",
        resource_type="document",
        user_id=current_user.id,
        username=current_user.username,
        resource_id=data.document_id,
        resource_name=f"电子签名: {data.meaning}",
        ip_address=ip_address,
    )

    return SignatureResponse(
        id=sig.id,
        user_id=sig.user_id,
        signer_name=sig.user.full_name if sig.user else None,
        document_id=sig.document_id,
        document_version=sig.document_version,
        meaning=sig.meaning,
        content_hash=sig.content_hash,
        ip_address=sig.ip_address,
        timestamp=sig.timestamp,
        is_valid=sig.is_valid,
    )


@router.get("/document/{document_id}", response_model=list[SignatureResponse])
async def get_document_signatures(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取文档的所有电子签名."""
    service = SignatureService(db)
    sigs = await service.get_signatures_for_document(document_id)
    return [
        SignatureResponse(
            id=s.id,
            user_id=s.user_id,
            signer_name=s.user.full_name if s.user else None,
            document_id=s.document_id,
            document_version=s.document_version,
            meaning=s.meaning,
            content_hash=s.content_hash,
            ip_address=s.ip_address,
            timestamp=s.timestamp,
            is_valid=s.is_valid,
        )
        for s in sigs
    ]


@router.get("/{signature_id}/verify", response_model=SignatureVerifyResponse)
async def verify_signature(
    signature_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """验证签名完整性."""
    service = SignatureService(db)
    sig = await service.get_signature(signature_id)
    return SignatureVerifyResponse(
        signature_id=sig.id,
        is_valid=sig.is_valid,
        signer_name=sig.user.full_name if sig.user else None,
        document_version=sig.document_version,
        meaning=sig.meaning,
        timestamp=sig.timestamp,
    )

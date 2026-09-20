"""电子签名 Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.signature import SignatureType


class SignatureRequest(BaseModel):
    """工作流之外的独立签名请求 - 需重新输入密码.

    不含 `username`：身份组件取自当前登录用户，避免冒签（ADR-0001）。
    不含 `meaning`：签名含义由 `signature_type` 推导，调用方不可指定（ADR-0005）。
    不含工作流字段：绑定步骤的签名一律由审批动作产生。
    """

    password: str = Field(..., description="密码（签名前重新输入）")
    document_id: str
    signature_type: SignatureType = Field(..., description="签署类型，决定签名含义")


class SignatureResponse(BaseModel):
    """电子签名响应."""

    id: str
    user_id: str
    signer_name: str | None = None
    document_id: str
    document_version: str
    meaning: str
    content_hash: str
    ip_address: str | None = None
    timestamp: datetime
    is_valid: bool

    model_config = {"from_attributes": True}


class SignatureVerifyResponse(BaseModel):
    """签名验证结果."""

    signature_id: str
    is_valid: bool
    signer_name: str | None = None
    document_version: str
    meaning: str
    timestamp: datetime

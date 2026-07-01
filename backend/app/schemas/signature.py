"""电子签名 Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class SignatureRequest(BaseModel):
    """电子签名请求 - 需重新验证身份."""

    username: str = Field(..., description="用户名（重新验证）")
    password: str = Field(..., description="密码（重新验证）")
    document_id: str
    meaning: str = Field(..., description="签名含义（如：我审核了此文档）")
    workflow_id: str | None = None
    workflow_step_id: str | None = None


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

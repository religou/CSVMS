"""电子签名 + 审计追踪 API 测试.

签名含义由系统按签署场景推导，调用方不可指定（ADR-0005）；身份组件取自当前登录
用户，请求体不含 username（ADR-0001）。
"""

import pytest
from httpx import AsyncClient

from app.models.signature import SignatureType
from app.models.workflow import ActionType, StepType
from app.services.signature_service import (
    _STANDALONE_MEANINGS,
    _STEP_MEANING_APPROVE,
    _STEP_MEANING_REJECT,
    _STEP_MEANING_REVIEW,
    SignatureService,
)

DRAFT_MEANING = _STANDALONE_MEANINGS[SignatureType.DRAFT]


async def _setup(client: AsyncClient) -> tuple[str, str]:
    """注册登录并创建文档, 返回 (token, doc_id)."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "siguser",
            "email": "sig@example.com",
            "full_name": "Sig User",
            "password": "Test@1234",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "siguser", "password": "Test@1234"},
    )
    token = resp.json()["access_token"]

    doc_resp = await client.post(
        "/api/v1/documents",
        json={"title": "签名测试文档", "doc_type": "URS", "content": "文档正文内容"},
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = doc_resp.json()["id"]
    return token, doc_id


def _payload(doc_id: str, *, password: str = "Test@1234") -> dict:
    return {
        "password": password,
        "document_id": doc_id,
        "signature_type": SignatureType.DRAFT.value,
    }


# ---------- 电子签名测试 ----------


@pytest.mark.asyncio
async def test_sign_document(client: AsyncClient):
    """测试电子签名：含义由签署类型推导."""
    token, doc_id = await _setup(client)

    resp = await client.post(
        "/api/v1/signatures",
        json=_payload(doc_id),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_id"] == doc_id
    assert data["meaning"] == DRAFT_MEANING
    assert data["is_valid"] is True
    assert len(data["content_hash"]) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_sign_wrong_password(client: AsyncClient):
    """测试签名时密码错误."""
    token, doc_id = await _setup(client)

    resp = await client.post(
        "/api/v1/signatures",
        json=_payload(doc_id, password="WrongPass@1"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "密码错误" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_signature_type_is_required_and_closed(client: AsyncClient):
    """签署类型必填且为封闭词表 —— 不能靠自由文本绕过含义推导."""
    token, doc_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}

    # 缺失
    resp = await client.post(
        "/api/v1/signatures",
        json={"password": "Test@1234", "document_id": doc_id},
        headers=headers,
    )
    assert resp.status_code == 422

    # 不在词表内
    resp = await client.post(
        "/api/v1/signatures",
        json={
            "password": "Test@1234",
            "document_id": doc_id,
            "signature_type": "我随便写一个含义",
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_client_cannot_dictate_meaning_or_signer(client: AsyncClient):
    """客户端塞进来的 meaning / username 一律不生效（ADR-0001、ADR-0005）.

    取代了迁移前的 test_sign_wrong_username：用户名已不在请求体里，
    冒签的入口本身被移除，因此不再有「用户名不匹配」这条错误。
    """
    token, doc_id = await _setup(client)

    payload = _payload(doc_id)
    payload["meaning"] = "我只是看了一下，不承担责任"
    payload["username"] = "otheruser"

    resp = await client.post(
        "/api/v1/signatures",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["meaning"] == DRAFT_MEANING, "客户端指定的含义不得生效"
    assert data["signer_name"] == "Sig User", "签名人必须是当前登录用户"


@pytest.mark.asyncio
async def test_get_document_signatures(client: AsyncClient):
    """测试获取文档签名列表."""
    token, doc_id = await _setup(client)

    # 签两次
    for _ in range(2):
        await client.post(
            "/api/v1/signatures",
            json=_payload(doc_id),
            headers={"Authorization": f"Bearer {token}"},
        )

    resp = await client.get(
        f"/api/v1/signatures/document/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_verify_signature(client: AsyncClient):
    """测试验证签名."""
    token, doc_id = await _setup(client)

    sig_resp = await client.post(
        "/api/v1/signatures",
        json=_payload(doc_id),
        headers={"Authorization": f"Bearer {token}"},
    )
    sig_id = sig_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/signatures/{sig_id}/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_valid"] is True
    assert resp.json()["meaning"] == DRAFT_MEANING


# ---------- 签名含义词表（纯函数，无需 DB） ----------


def test_step_meaning_routing():
    """工作流路径选对了哪一句 —— 只验证分支路由，措辞由下面的核准表钉死."""
    meaning_for = SignatureService._meaning_for_step

    # 拒绝优先于步骤类型 —— 批准步上的拒绝也是「予以退回」
    assert meaning_for(StepType.APPROVE, ActionType.REJECT) == _STEP_MEANING_REJECT
    assert meaning_for(StepType.REVIEW, ActionType.REJECT) == _STEP_MEANING_REJECT

    assert meaning_for(StepType.APPROVE, ActionType.APPROVE) == _STEP_MEANING_APPROVE
    assert meaning_for(StepType.REVIEW, ActionType.APPROVE) == _STEP_MEANING_REVIEW


# ⚠️ 以下是**已核准的签名含义措辞**，会原文写进签署记录并具法律效力。
#
# 这份字面量清单是故意与实现重复的：它的唯一作用是让措辞改动**无法静默发生**。
# 本测试报红不代表代码坏了，它代表有人改了法律文本 —— 改动需经质量负责人重新核准，
# 核准后同步更新这里。除本测试外，其余测试都引用实现里的常量，因此一次措辞变更
# 只会打红这一个测试，而不是散落一片。
APPROVED_MEANING_WORDING = {
    "step:reject": "我已审核此文档，予以退回",
    "step:approve": "我已批准此文档，同意生效",
    "step:review": "我已审核此文档，内容准确完整",
    "type:draft": "我起草了此文档，内容由本人编制",
}


def test_approved_signature_meaning_wording():
    """签名含义的措辞必须与已核准的文本逐字一致."""
    actual = {
        "step:reject": _STEP_MEANING_REJECT,
        "step:approve": _STEP_MEANING_APPROVE,
        "step:review": _STEP_MEANING_REVIEW,
        "type:draft": _STANDALONE_MEANINGS[SignatureType.DRAFT],
    }
    assert actual == APPROVED_MEANING_WORDING, (
        "签名含义的措辞与已核准文本不一致。\n"
        "这是写进签署记录的法律文本，改动需经质量负责人重新核准，"
        "核准后同步更新 APPROVED_MEANING_WORDING。"
    )


def test_every_signature_type_is_registered():
    """签署类型枚举的每个成员都必须配好措辞并登记进核准表.

    只管**覆盖**，不管文本内容 —— 文本由上面那个测试独占，这样一次措辞变更
    只会打红一个测试。新增枚举成员而忘记配措辞或忘记登记，在这里报红。
    """
    for signature_type in SignatureType:
        meaning = SignatureService._meaning_for_type(signature_type)
        assert meaning and meaning.strip(), f"{signature_type} 缺少签名含义措辞"

        key = f"type:{signature_type.value}"
        assert key in APPROVED_MEANING_WORDING, (
            f"{signature_type} 未登记进 APPROVED_MEANING_WORDING（缺少键 {key!r}）。\n"
            "新增签署类型时，措辞需经质量负责人核准并登记。"
        )


# ---------- 审计追踪测试 ----------


@pytest.mark.asyncio
async def test_audit_log_created_on_sign(client: AsyncClient):
    """测试签名操作生成审计日志."""
    token, doc_id = await _setup(client)

    await client.post(
        "/api/v1/signatures",
        json=_payload(doc_id),
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/v1/audit-logs",
        params={"resource_type": "document", "resource_id": doc_id, "action": "SIGN"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["items"][0]["action"] == "SIGN"


@pytest.mark.asyncio
async def test_audit_log_list(client: AsyncClient):
    """测试审计日志查询."""
    token, doc_id = await _setup(client)

    # 产生一些审计日志
    await client.post(
        "/api/v1/signatures",
        json=_payload(doc_id),
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_audit_log_resource_trail(client: AsyncClient):
    """测试资源审计追踪."""
    token, doc_id = await _setup(client)

    await client.post(
        "/api/v1/signatures",
        json=_payload(doc_id),
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/v1/audit-logs/resource/document/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

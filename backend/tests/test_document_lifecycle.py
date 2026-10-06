"""文档生命周期跃迁表的穷举测试（ADR-0007）.

这个 module 不碰数据库，所以这里**零 fixture、零 mock、零 HTTP** —— 6 个状态 ×
11 个操作可以整张表穷举。对比一下：同样的规则在散落进 service 的时候，只能通过
HTTP 建文档、建模板、走审批才能间接碰到其中几格。
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.core.exceptions import BusinessError
from app.domain.document_lifecycle import (
    UNREACHABLE_STATUSES,
    DocumentGone,
    DocumentOperation,
    _RULES,
    _VersionRule,
    apply,
    bump_major_version,
    bump_minor_version,
    permitted_operations,
)
from app.models.document import DocumentStatus

ALL_STATUSES = list(DocumentStatus)
ALL_OPERATIONS = list(DocumentOperation)


def test_every_operation_has_a_rule():
    """每个操作都必须在跃迁表里 —— 漏一个就是运行期 KeyError."""
    missing = set(ALL_OPERATIONS) - set(_RULES)
    assert not missing, f"这些操作没有跃迁规则: {sorted(o.value for o in missing)}"

    stale = set(_RULES) - set(ALL_OPERATIONS)
    assert not stale, f"跃迁表里有已不存在的操作: {sorted(stale)}"


@pytest.mark.parametrize("operation", ALL_OPERATIONS, ids=lambda o: o.value)
@pytest.mark.parametrize("status", ALL_STATUSES, ids=lambda s: s.value)
def test_transition_table_is_exhaustively_correct(
    status: DocumentStatus, operation: DocumentOperation
):
    """6 状态 × 11 操作全表：要么按表给出结果，要么按表给出拒绝文案."""
    rule = _RULES[operation]

    if status == rule.allowed_from:
        outcome = apply(operation, status=status, version="1.2")
        assert outcome.status == rule.to_status
    else:
        with pytest.raises(BusinessError) as exc:
            apply(operation, status=status, version="1.2")
        assert exc.value.detail == rule.denial


@pytest.mark.parametrize("operation", ALL_OPERATIONS, ids=lambda o: o.value)
def test_self_loop_operations_change_nothing(operation: DocumentOperation):
    """自环操作只做门控，不改状态也不改版本号."""
    rule = _RULES[operation]
    if rule.to_status is not rule.allowed_from:
        pytest.skip("非自环操作")

    outcome = apply(operation, status=rule.allowed_from, version="3.7")
    assert outcome.status == rule.allowed_from
    assert outcome.version == "3.7"


def test_unreachable_statuses_match_the_table():
    """`UNREACHABLE_STATUSES` 必须恰好等于表里到不了的那些状态.

    补上生效/替代/废止的跃迁时，这个测试会提醒同步更新那份清单。
    """
    reachable = {
        rule.to_status
        for rule in _RULES.values()
        if isinstance(rule.to_status, DocumentStatus)
    }
    # DRAFT 还是起草时的初始状态，本来就可达
    reachable.add(DocumentStatus.DRAFT)

    assert UNREACHABLE_STATUSES == frozenset(set(ALL_STATUSES) - reachable), (
        "UNREACHABLE_STATUSES 与跃迁表不一致。\n"
        f"表里可达: {sorted(s.value for s in reachable)}\n"
        f"清单声明不可达: {sorted(s.value for s in UNREACHABLE_STATUSES)}"
    )


def test_delete_leads_out_of_the_status_space():
    """删除没有「新状态」—— 它的结果是文档不再存在."""
    outcome = apply(
        DocumentOperation.DELETE, status=DocumentStatus.DRAFT, version="0.1"
    )
    assert outcome.status is DocumentGone.GONE
    assert not isinstance(outcome.status, DocumentStatus)


# ---------- 版本号规则（ADR-0002） ----------


def test_only_approve_and_revise_move_the_version():
    """只有批准与发起变更会改版本号，其余操作一律不动."""
    moving = {
        operation
        for operation, rule in _RULES.items()
        if rule.version_rule is not _VersionRule.UNCHANGED
    }
    assert moving == {
        DocumentOperation.APPROVE_FINAL,
        DocumentOperation.REVISE,
    }, f"会改版本号的操作: {sorted(o.value for o in moving)}"


def test_adr_0002_version_sequence():
    """ADR-0002 的版本序列：0.1 起 → 首批 1.0 → 发起变更 1.1 → 再批准 2.0."""
    version = "0.1"

    version = apply(
        DocumentOperation.SUBMIT, status=DocumentStatus.DRAFT, version=version
    ).version
    assert version == "0.1", "提交不改版本号"

    version = apply(
        DocumentOperation.APPROVE_FINAL,
        status=DocumentStatus.UNDER_REVIEW,
        version=version,
    ).version
    assert version == "1.0"

    version = apply(
        DocumentOperation.REVISE, status=DocumentStatus.APPROVED, version=version
    ).version
    assert version == "1.1"

    version = apply(
        DocumentOperation.SUBMIT, status=DocumentStatus.DRAFT, version=version
    ).version
    version = apply(
        DocumentOperation.APPROVE_FINAL,
        status=DocumentStatus.UNDER_REVIEW,
        version=version,
    ).version
    assert version == "2.0"


@given(major=st.integers(min_value=0, max_value=999), minor=st.integers(min_value=0, max_value=999))
def test_version_bumps_are_monotonic(major: int, minor: int):
    """任意 x.y：主版进位后主版严格变大，次版进位后次版严格变大."""
    version = f"{major}.{minor}"

    bumped_major = bump_major_version(version)
    assert bumped_major == f"{major + 1}.0"

    bumped_minor = bump_minor_version(version)
    assert bumped_minor == f"{major}.{minor + 1}"


@pytest.mark.parametrize("malformed", ["", "abc", "1", "1.x", "x.1", "1.2.3"])
def test_version_bumps_degrade_predictably(malformed: str):
    """畸形版本标签不抛异常 —— 主版进位按 0 处理，次版进位原样返回."""
    assert bump_major_version(malformed).endswith(".0")
    minor = bump_minor_version(malformed)
    assert isinstance(minor, str)


# ---------- permitted_operations ----------


@pytest.mark.parametrize("status", ALL_STATUSES, ids=lambda s: s.value)
def test_permitted_operations_agrees_with_apply(status: DocumentStatus):
    """`permitted_operations` 必须与 `apply` 的实际放行结果一致."""
    permitted = permitted_operations(status)

    for operation in ALL_OPERATIONS:
        if operation in permitted:
            apply(operation, status=status, version="1.0")  # 不该抛
        else:
            with pytest.raises(BusinessError):
                apply(operation, status=status, version="1.0")


def test_unreachable_statuses_permit_nothing():
    """到不了的状态自然也做不了任何事 —— 万一被人为写进数据库，行为是全部拒绝."""
    for status in UNREACHABLE_STATUSES:
        assert permitted_operations(status) == frozenset()


def test_approved_document_cannot_be_edited():
    """加深后最该被一眼看到的一格：已批准文档不能直接编辑，只能发起变更."""
    with pytest.raises(BusinessError) as exc:
        apply(
            DocumentOperation.EDIT, status=DocumentStatus.APPROVED, version="1.0"
        )
    assert exc.value.detail == "只有草稿状态的文档可以编辑"

    # 正路：发起变更回到草稿，次版本进位
    outcome = apply(
        DocumentOperation.REVISE, status=DocumentStatus.APPROVED, version="1.0"
    )
    assert outcome.status == DocumentStatus.DRAFT
    assert outcome.version == "1.1"

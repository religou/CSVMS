"""文档生命周期：状态跃迁表与版本号规则（ADR-0007）.

本 module **不碰数据库、不碰 ORM**。它只回答一件事：在当前状态下，这个操作合不
合法；若合法，新状态与新版本号是什么。因此整张表可以被穷举测试，无需 fixture。

表里同时包含两类操作：

* 真正改变状态的跃迁（提交、批准、拒绝、退回、撤回、发起变更、删除）；
* 状态不变、但只在特定状态下才允许的操作（编辑、维护 URS 条目、增删 URS 引用）。
  它们以**自环**形式入表，于是「已批准文档不能编辑」是表里的一个格子，而不是散落
  在 service 里的一句 if。

状态之外的资格 —— 操作人是否作者、文档类型是否 URS、是否流程发起人 —— 不在这里，
它们属于各领域 module 的**业务资格**判断。
"""

import enum
from dataclasses import dataclass

from app.core.exceptions import BusinessError
from app.models.document import DocumentStatus


class DocumentOperation(str, enum.Enum):
    """会被文档状态门控的操作."""

    EDIT = "edit"  # 编辑标题/摘要/正文
    SUBMIT = "submit"  # 提交审批
    APPROVE_FINAL = "approve_final"  # 最终批准步通过
    REJECT = "reject"  # 审批拒绝
    RETURN_TO_AUTHOR = "return_to_author"  # 第一步退回起草人
    WITHDRAW = "withdraw"  # 发起人撤回
    REVISE = "revise"  # 发起变更
    DELETE = "delete"  # 删除文档
    MAINTAIN_URS_ITEM = "maintain_urs_item"  # 维护 URS 条目
    ADD_URS_REFERENCE = "add_urs_reference"  # 关联 URS 条目
    REMOVE_URS_REFERENCE = "remove_urs_reference"  # 删除 URS 引用


class DocumentGone(enum.Enum):
    """删除后的终态：文档不再存在.

    这不是一个 `DocumentStatus` —— 删除没有「新状态」，硬塞一个枚举成员会让
    「文档还在」和「文档已删」无法区分。
    """

    GONE = "gone"


class _VersionRule(enum.Enum):
    """版本号如何跟随跃迁变化（ADR-0002）."""

    UNCHANGED = "unchanged"
    BUMP_MAJOR = "bump_major"  # 批准通过：x.y -> (x+1).0
    BUMP_MINOR = "bump_minor"  # 发起变更退回草稿：x.y -> x.(y+1)


@dataclass(frozen=True)
class _Rule:
    """一个操作的门控规则：允许的来源状态、结果状态、版本规则、拒绝文案."""

    allowed_from: DocumentStatus
    to_status: DocumentStatus | DocumentGone
    version_rule: _VersionRule
    denial: str


#: 唯一的跃迁表。改状态规则只需要改这里。
_RULES: dict[DocumentOperation, _Rule] = {
    DocumentOperation.EDIT: _Rule(
        DocumentStatus.DRAFT,
        DocumentStatus.DRAFT,
        _VersionRule.UNCHANGED,
        "只有草稿状态的文档可以编辑",
    ),
    DocumentOperation.SUBMIT: _Rule(
        DocumentStatus.DRAFT,
        DocumentStatus.UNDER_REVIEW,
        _VersionRule.UNCHANGED,
        "只有草稿状态的文档可以提交审核",
    ),
    DocumentOperation.APPROVE_FINAL: _Rule(
        DocumentStatus.UNDER_REVIEW,
        DocumentStatus.APPROVED,
        _VersionRule.BUMP_MAJOR,
        "只有审核中的文档可以批准",
    ),
    DocumentOperation.REJECT: _Rule(
        DocumentStatus.UNDER_REVIEW,
        DocumentStatus.DRAFT,
        _VersionRule.UNCHANGED,
        "只有审核中的文档可以拒绝",
    ),
    DocumentOperation.RETURN_TO_AUTHOR: _Rule(
        DocumentStatus.UNDER_REVIEW,
        DocumentStatus.DRAFT,
        _VersionRule.UNCHANGED,
        "只有审核中的文档可以退回起草人",
    ),
    DocumentOperation.WITHDRAW: _Rule(
        DocumentStatus.UNDER_REVIEW,
        DocumentStatus.DRAFT,
        _VersionRule.UNCHANGED,
        "只有审核中的文档可以撤回审批",
    ),
    DocumentOperation.REVISE: _Rule(
        DocumentStatus.APPROVED,
        DocumentStatus.DRAFT,
        _VersionRule.BUMP_MINOR,
        "只有已批准的文档可以发起变更",
    ),
    DocumentOperation.DELETE: _Rule(
        DocumentStatus.DRAFT,
        DocumentGone.GONE,
        _VersionRule.UNCHANGED,
        "只有草稿状态的文档可以删除",
    ),
    DocumentOperation.MAINTAIN_URS_ITEM: _Rule(
        DocumentStatus.DRAFT,
        DocumentStatus.DRAFT,
        _VersionRule.UNCHANGED,
        "只有草稿状态的 URS 文档可以维护条目",
    ),
    DocumentOperation.ADD_URS_REFERENCE: _Rule(
        DocumentStatus.DRAFT,
        DocumentStatus.DRAFT,
        _VersionRule.UNCHANGED,
        "只有草稿状态的文档可以关联 URS 条目",
    ),
    DocumentOperation.REMOVE_URS_REFERENCE: _Rule(
        DocumentStatus.DRAFT,
        DocumentStatus.DRAFT,
        _VersionRule.UNCHANGED,
        "只有草稿状态的文档可以删除 URS 引用",
    ),
}

#: 目前没有任何操作能抵达的状态。它们在枚举里存在，但不可达 —— 生效、替代、废止
#: 的跃迁尚未实现。有测试钉住这份清单，避免有人误以为它们已经能用。
#: 注意：前端 Dashboard 把 `approved + effective` 相加当指标，其中 effective 恒为 0。
UNREACHABLE_STATUSES: frozenset[DocumentStatus] = frozenset(
    {
        DocumentStatus.EFFECTIVE,
        DocumentStatus.SUPERSEDED,
        DocumentStatus.RETIRED,
    }
)


@dataclass(frozen=True)
class Outcome:
    """一次操作的结果：新状态与新版本号.

    自环操作（编辑、URS 维护）的 status/version 与输入相同，调用方赋值即为空操作。
    删除操作的 status 是 `DocumentGone.GONE`。
    """

    status: DocumentStatus | DocumentGone
    version: str


def apply(
    operation: DocumentOperation, *, status: DocumentStatus, version: str
) -> Outcome:
    """校验操作在当前状态下合法，返回新状态与新版本号.

    不合法时抛 `BusinessError`，文案取自跃迁表 —— 每个操作一句，保持原有措辞。
    """
    rule = _RULES[operation]
    if status != rule.allowed_from:
        raise BusinessError(rule.denial)
    return Outcome(status=rule.to_status, version=_next_version(version, rule.version_rule))


def permitted_operations(status: DocumentStatus) -> frozenset[DocumentOperation]:
    """当前状态下允许的全部操作.

    供接口向前端暴露「此刻能做什么」，免得前端自己重算状态组合。
    """
    return frozenset(
        operation
        for operation, rule in _RULES.items()
        if rule.allowed_from == status
    )


# ---------- 版本号规则（ADR-0002） ----------


def _next_version(version: str, rule: _VersionRule) -> str:
    if rule is _VersionRule.BUMP_MAJOR:
        return bump_major_version(version)
    if rule is _VersionRule.BUMP_MINOR:
        return bump_minor_version(version)
    return version


def _parse_major(version: str) -> int:
    """从版本标签解析主版本号，无法解析时按 0 处理."""
    try:
        return int(version.split(".")[0])
    except (ValueError, IndexError):
        return 0


def bump_major_version(version: str) -> str:
    """主版本进位：x.y -> (x+1).0（文档批准通过时）."""
    return f"{_parse_major(version) + 1}.0"


def bump_minor_version(version: str) -> str:
    """次版本进位：x.y -> x.(y+1)（已批准文档发起变更回到草稿时）."""
    parts = version.split(".")
    try:
        major, minor = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return version
    return f"{major}.{minor + 1}"

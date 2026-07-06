"""初始化字典数据脚本.

运行方式: python -m app.scripts.seed_dict
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.models.dictionary import DictCategory, DictItem


def _default_project_role_permission_codes(
    permission_profile: str | None,
) -> list[str] | None:
    base_codes = [
        "project.dashboard.menu",
        "project.dashboard.view",
        "project.documents.menu",
        "project.documents.view",
        "project.workflows.menu",
        "project.workflows.view",
        "project.traceability.menu",
        "project.traceability.view",
        "project.audit_log.menu",
        "project.audit_log.view",
        "project.members.menu",
        "project.members.view",
    ]

    if permission_profile in {"owner", "manager"}:
        return base_codes + [
            "project.documents.manage",
            "project.workflows.manage",
            "project.members.manage",
            "project.stage.manage",
        ]

    if permission_profile == "member":
        return base_codes + ["project.documents.manage"]

    if permission_profile == "viewer":
        return base_codes

    return None

SEED_DATA = [
    {
        "code": "doc_type",
        "name": "文档类型",
        "description": "验证文档的类型分类",
        "is_system": True,
        "items": [
            {"code": "VP", "label": "VP（Validation Plan）", "sort_order": 1},
            {"code": "URS", "label": "URS（User Requirement Specification）", "sort_order": 2},
            {"code": "FS", "label": "FS（Functional Specification）", "sort_order": 3},
            {"code": "DS", "label": "DS（Design Specification）", "sort_order": 4},
            {"code": "IQ", "label": "IQ（Installation Qualification）", "sort_order": 5},
            {"code": "OQ", "label": "OQ（Operational Qualification）", "sort_order": 6},
            {"code": "PQ", "label": "PQ（Performance Qualification）", "sort_order": 7},
            {"code": "TM", "label": "TM（Traceability Matrix）", "sort_order": 8},
            {"code": "VSR", "label": "VSR（Validation Summary Report）", "sort_order": 9},
            {"code": "DV", "label": "DV（Deviation）", "sort_order": 10},
            {"code": "CC", "label": "CC（Change Control）", "sort_order": 11},
            {"code": "PR", "label": "PR（Periodic Review）", "sort_order": 12},
            {"code": "RET", "label": "RET（Retirement）", "sort_order": 13},
        ],
    },
    {
        "code": "doc_status",
        "name": "文档状态",
        "description": "文档生命周期状态",
        "is_system": True,
        "items": [
            {"code": "draft", "label": "草稿", "extra": "default", "sort_order": 1},
            {"code": "under_review", "label": "审核中", "extra": "processing", "sort_order": 2},
            {"code": "approved", "label": "已批准", "extra": "success", "sort_order": 3},
            {"code": "effective", "label": "已生效", "extra": "green", "sort_order": 4},
            {"code": "superseded", "label": "已替代", "extra": "warning", "sort_order": 5},
            {"code": "retired", "label": "已废止", "extra": "error", "sort_order": 6},
        ],
    },
    {
        "code": "project_status",
        "name": "项目状态",
        "description": "验证项目的状态",
        "is_system": True,
        "items": [
            {"code": "active", "label": "进行中", "extra": "green", "sort_order": 1},
            {"code": "completed", "label": "已完成", "extra": "blue", "sort_order": 2},
            {"code": "archived", "label": "已归档", "extra": "default", "sort_order": 3},
        ],
    },
    {
        "code": "project_role",
        "name": "项目角色",
        "description": "项目成员的角色类型",
        "is_system": True,
        "items": [
            {
                "code": "owner",
                "label": "负责人",
                "extra": "red",
                "permission_profile": "owner",
                "permission_codes": _default_project_role_permission_codes("owner"),
                "sort_order": 1,
            },
            {
                "code": "manager",
                "label": "项目经理",
                "extra": "orange",
                "permission_profile": "manager",
                "permission_codes": _default_project_role_permission_codes("manager"),
                "sort_order": 2,
            },
            {
                "code": "member",
                "label": "成员",
                "extra": "blue",
                "permission_profile": "member",
                "permission_codes": _default_project_role_permission_codes("member"),
                "sort_order": 3,
            },
            {
                "code": "viewer",
                "label": "只读",
                "extra": "default",
                "permission_profile": "viewer",
                "permission_codes": _default_project_role_permission_codes("viewer"),
                "sort_order": 4,
            },
        ],
    },
    {
        "code": "project_stage",
        "name": "项目阶段",
        "description": "验证项目当前所处的阶段",
        "is_system": True,
        "items": [
            {"code": "requirement", "label": "需求", "extra": "blue", "sort_order": 1},
            {"code": "design", "label": "设计", "extra": "purple", "sort_order": 2},
            {"code": "testing", "label": "测试", "extra": "orange", "sort_order": 3},
            {"code": "live", "label": "上线", "extra": "green", "sort_order": 4},
        ],
    },
    {
        "code": "system_role",
        "name": "系统角色",
        "description": "系统级别的用户角色",
        "is_system": True,
        "items": [
            {"code": "admin", "label": "系统管理员", "sort_order": 1},
            {"code": "validation_admin", "label": "验证管理员", "sort_order": 2},
            {"code": "user", "label": "普通用户", "sort_order": 3},
        ],
    },
]


async def seed_dict() -> None:
    """插入初始字典数据（跳过已存在的）."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        for cat_data in SEED_DATA:
            # 使用副本，避免 pop 修改到模块级 SEED_DATA（否则重复调用会因缺少
            # "items" 键而抛出 KeyError，破坏幂等性）。
            cat_data = dict(cat_data)
            items_data = cat_data.pop("items")
            # 检查是否已存在
            result = await session.execute(
                select(DictCategory).where(DictCategory.code == cat_data["code"])
            )
            category = result.scalar_one_or_none()
            if not category:
                category = DictCategory(**cat_data)
                session.add(category)
                await session.flush()

            # 插入选项
            for item_data in items_data:
                existing = await session.execute(
                    select(DictItem).where(
                        DictItem.category_id == category.id,
                        DictItem.code == item_data["code"],
                    )
                )
                if not existing.scalar_one_or_none():
                    item = DictItem(category_id=category.id, **item_data)
                    session.add(item)

        await session.commit()
        print("字典数据初始化完成")


if __name__ == "__main__":
    asyncio.run(seed_dict())

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
    {
        "code": "regulation",
        "name": "法规",
        "description": "系统需符合的法规/指南",
        "is_system": True,
        "items": [
            {
                "code": "fda_21cfr_part11",
                "label": "FDA 21 CFR Part 11 – Electronic Records; Electronic Signatures（电子记录与电子签名）",
                "description": "US FDA regulation. Sets the criteria under which electronic records and electronic signatures are treated as equal to paper records and handwritten signatures (system controls, audit trails, signature linking).",
                "sort_order": 10,
            },
            {
                "code": "fda_21cfr_part210_211",
                "label": "FDA 21 CFR Parts 210/211 – cGMP for Drugs（药品现行GMP）",
                "description": "US FDA regulations. Part 210 covers general cGMP for drug manufacturing, processing, packing and holding. Part 211 covers cGMP for finished pharmaceuticals, including §211.68 on automatic, mechanical and electronic equipment.",
                "sort_order": 20,
            },
            {
                "code": "fda_21cfr_part58",
                "label": "FDA 21 CFR Part 58 – Good Laboratory Practice for Nonclinical Laboratory Studies（GLP）",
                "description": "US FDA regulation for nonclinical laboratory studies that support research or marketing applications. Covers study conduct, records and archiving, including data generated by computerized systems.",
                "sort_order": 30,
            },
            {
                "code": "fda_21cfr_part820_qmsr",
                "label": "FDA 21 CFR Part 820 – Quality Management System Regulation (QMSR)（医疗器械质量管理体系法规）",
                "description": "US FDA medical device QMS regulation. It replaced the former Quality System Regulation and incorporates ISO 13485:2016 by reference. In effect since 2 February 2026. Software validation for production and quality systems falls under it.",
                "sort_order": 40,
            },
            {
                "code": "fda_csa_guidance",
                "label": "FDA Guidance – Computer Software Assurance for Production and Quality System Software（计算机软件保证 CSA）",
                "description": "Final FDA guidance (September 2025) for medical device manufacturers. Describes a risk-based approach to assuring software used in production or the quality system. Supplements the General Principles of Software Validation guidance.",
                "sort_order": 50,
            },
            {
                "code": "fda_data_integrity_cgmp",
                "label": "FDA Guidance – Data Integrity and Compliance With Drug CGMP: Questions and Answers（数据完整性问答）",
                "description": "Final FDA guidance (December 2018). Explains FDA's data integrity expectations under drug cGMP: ALCOA, audit trails, access control, and validation of computer workflows.",
                "sort_order": 60,
            },
            {
                "code": "eu_gmp_annex11",
                "label": "EU GMP Annex 11 – Computerised Systems（欧盟GMP附录11 计算机化系统）",
                "description": "European Commission, EudraLex Volume 4. Covers the lifecycle, validation, data integrity and security of computerised systems used in GMP activities. The 2011 version is still the one in force. A revised draft (consulted on together with Chapter 4 and new Annex 22 on AI) was open from 7 July to 7 October 2025 and is not yet final.",
                "sort_order": 70,
            },
            {
                "code": "eu_gmp_annex15",
                "label": "EU GMP Annex 15 – Qualification and Validation（欧盟GMP附录15 确认与验证）",
                "description": "European Commission, EudraLex Volume 4. Covers qualification of facilities, equipment and utilities, and validation of processes, cleaning and test methods. In operation since 1 October 2015.",
                "sort_order": 80,
            },
            {
                "code": "ema_ct_computerised_systems",
                "label": "EMA Guideline on Computerised Systems and Electronic Data in Clinical Trials（临床试验计算机化系统与电子数据指南）",
                "description": "EMA GCP Inspectors Working Group guideline (EMA/INS/GCP/112288/2023). Final version adopted March 2023; it came into effect 6 months after publication. Covers validation, audit trails, user management, security, eCOA/ePRO and other systems used in clinical trials.",
                "sort_order": 90,
            },
            {
                "code": "ich_e6_r3",
                "label": "ICH E6(R3) – Guideline for Good Clinical Practice（药物临床试验质量管理规范 GCP）",
                "description": "ICH harmonised GCP guideline. In the EU, the Principles and Annex 1 apply from 23 July 2025. Annex 2 (decentralised, pragmatic and real-world-data trials) reached Step 4 in June 2026 and applies in the EU from 15 January 2027. Includes requirements for computerised systems and data governance.",
                "sort_order": 100,
            },
            {
                "code": "ich_q9_r1",
                "label": "ICH Q9(R1) – Quality Risk Management（质量风险管理）",
                "description": "ICH harmonised guideline on quality risk management principles and tools. It is the basis for the risk-based CSV/CSA approach. In the EU, R1 applies from 26 July 2023.",
                "sort_order": 110,
            },
            {
                "code": "pics_pi_011_3",
                "label": "PIC/S PI 011-3 – Good Practices for Computerised Systems in Regulated GxP Environments（GxP计算机化系统良好实践）",
                "description": "PIC/S guidance document for inspectors on computerised system validation and control in GxP environments. Still listed as current on the PIC/S publications page.",
                "sort_order": 120,
            },
            {
                "code": "pics_pi_041_1",
                "label": "PIC/S PI 041-1 – Good Practices for Data Management and Integrity in Regulated GMP/GDP Environments（数据管理与完整性良好实践）",
                "description": "PIC/S guidance document (2021) on data governance and data integrity for paper-based, hybrid and computerised systems.",
                "sort_order": 130,
            },
            {
                "code": "mhra_gxp_data_integrity",
                "label": "MHRA – Guidance on GxP Data Integrity（GxP数据完整性指南）",
                "description": "UK MHRA guidance covering GLP, GCP, GMP, GDP and GPvP. Defines data governance, ALCOA+ and expectations for computerised systems. First published March 2018; GLP information added September 2021.",
                "sort_order": 140,
            },
            {
                "code": "who_trs1033_annex4",
                "label": "WHO TRS No. 1033 Annex 4 – Guideline on Data Integrity（WHO数据完整性指南）",
                "description": "World Health Organization technical guideline (2021). Covers data integrity principles, risk management and controls for paper and electronic records across GxP.",
                "sort_order": 150,
            },
            {
                "code": "nmpa_gmp_annex_cs",
                "label": "NMPA《药品生产质量管理规范（2010年修订）》附录《计算机化系统》",
                "description": "Chinese GMP annex on computerised systems, issued by the former CFDA (now NMPA) and in effect since 1 December 2015. Covers risk-based validation, access control, audit trails, electronic data and data backup.",
                "sort_order": 160,
            },
            {
                "code": "nmpa_gcp_2020",
                "label": "NMPA《药物临床试验质量管理规范》（2020年第57号公告）",
                "description": "Chinese GCP, issued jointly by NMPA and the National Health Commission (Announcement No. 57 of 2020). In effect since 1 July 2020. Includes requirements for computerised systems and electronic data in clinical trials.",
                "sort_order": 170,
            },
            {
                "code": "ispe_gamp5_2nd",
                "label": "ISPE GAMP® 5 Second Edition – A Risk-Based Approach to Compliant GxP Computerized Systems（GAMP 5 第二版）",
                "description": "ISPE industry good practice guide (not a regulation). Widely used as the framework for risk-based validation of GxP computerised systems. The second edition (2022) adds critical thinking, agile/IT service and CSA-aligned content.",
                "sort_order": 180,
            },
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

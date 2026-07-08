"""追溯矩阵 Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class TraceLinkCreate(BaseModel):
    """创建追溯关系."""

    source_document_id: str
    target_document_id: str
    source_section: str | None = None
    target_section: str | None = None
    link_type: str = "traces_to"
    description: str | None = None


class TraceLinkResponse(BaseModel):
    """追溯关系响应."""

    id: str
    source_document_id: str
    source_doc_number: str | None = None
    source_title: str | None = None
    source_doc_type: str | None = None
    source_section: str | None = None
    target_document_id: str
    target_doc_number: str | None = None
    target_title: str | None = None
    target_doc_type: str | None = None
    target_section: str | None = None
    link_type: str
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CoverageItem(BaseModel):
    """覆盖率条目."""

    total: int
    covered: int
    rate: float
    expected_targets: list[str]


class GapItem(BaseModel):
    """未覆盖条目."""

    document_id: str
    doc_number: str
    title: str
    doc_type: str
    missing_targets: list[str]


class UrsCoverageItem(BaseModel):
    """URS 条目级覆盖率统计."""

    total: int
    covered: int
    uncovered: int
    rate: float


class UncoveredUrsItem(BaseModel):
    """未被任何 Referencing_Document 引用的 URS 条目."""

    id: str
    item_code: str
    description: str
    document_id: str
    doc_number: str


class TraceMatrixResponse(BaseModel):
    """追溯矩阵响应."""

    links: list[TraceLinkResponse]
    coverage: dict[str, CoverageItem]
    gaps: list[GapItem]
    urs_coverage: UrsCoverageItem
    uncovered_urs_items: list[UncoveredUrsItem]


class DashboardResponse(BaseModel):
    """仪表板统计响应."""

    total_documents: int
    status_distribution: dict[str, int]
    type_distribution: dict[str, int]
    workflow_stats: dict[str, int]
    pending_approvals: int
    my_drafts: int
    total_signatures: int

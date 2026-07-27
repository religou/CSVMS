"""追溯矩阵 Pydantic schemas."""

from pydantic import BaseModel


class UncoveredUrsItem(BaseModel):
    """未被任何 Referencing_Document 引用的 URS 条目."""

    id: str
    item_code: str
    description: str


class UrsTraceReference(BaseModel):
    """引用（覆盖）某 URS 条目的下游文档."""

    document_id: str
    doc_number: str
    title: str
    doc_type: str


class UrsTraceRow(BaseModel):
    """URS 条目覆盖追溯矩阵的一行：某个 URS 条目及其被哪些下游文档引用."""

    urs_item_id: str
    item_code: str
    description: str
    source_document_id: str
    source_doc_number: str
    covered: bool
    references: list[UrsTraceReference]


class TraceMatrixResponse(BaseModel):
    """追溯矩阵响应（以 URS 条目覆盖关系为核心）."""

    urs_matrix: list[UrsTraceRow]
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

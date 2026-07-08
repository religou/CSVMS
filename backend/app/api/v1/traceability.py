"""追溯矩阵 API 路由."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.traceability import (
    TraceLinkCreate,
    TraceLinkResponse,
    TraceMatrixResponse,
    CoverageItem,
    GapItem,
    UrsCoverageItem,
    UncoveredUrsItem,
)
from app.services.traceability_service import TraceabilityService

router = APIRouter(prefix="/traceability", tags=["追溯矩阵"])


def _link_to_response(link) -> TraceLinkResponse:
    return TraceLinkResponse(
        id=link.id,
        source_document_id=link.source_document_id,
        source_doc_number=link.source_document.doc_number if link.source_document else None,
        source_title=link.source_document.title if link.source_document else None,
        source_doc_type=(link.source_document.doc_type.value if link.source_document and hasattr(link.source_document.doc_type, 'value') else None),
        source_section=link.source_section,
        target_document_id=link.target_document_id,
        target_doc_number=link.target_document.doc_number if link.target_document else None,
        target_title=link.target_document.title if link.target_document else None,
        target_doc_type=(link.target_document.doc_type.value if link.target_document and hasattr(link.target_document.doc_type, 'value') else None),
        target_section=link.target_section,
        link_type=link.link_type,
        description=link.description,
        created_at=link.created_at,
    )


@router.post("/links", response_model=TraceLinkResponse)
async def create_trace_link(
    data: TraceLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建追溯关系."""
    service = TraceabilityService(db)
    link = await service.create_link(
        source_document_id=data.source_document_id,
        target_document_id=data.target_document_id,
        created_by=current_user.id,
        source_section=data.source_section,
        target_section=data.target_section,
        link_type=data.link_type,
        description=data.description,
    )
    return _link_to_response(link)


@router.delete("/links/{link_id}")
async def delete_trace_link(
    link_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """删除追溯关系."""
    service = TraceabilityService(db)
    await service.delete_link(link_id)
    return {"message": "已删除"}


@router.get("/document/{document_id}")
async def get_document_traces(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取文档的上下游追溯关系."""
    service = TraceabilityService(db)
    result = await service.get_links_for_document(document_id)
    return {
        "upstream": [_link_to_response(l) for l in result["upstream"]],
        "downstream": [_link_to_response(l) for l in result["downstream"]],
    }


@router.get("/matrix", response_model=TraceMatrixResponse)
async def get_trace_matrix(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取完整追溯矩阵（含覆盖率和Gap分析，按项目范围隔离）."""
    service = TraceabilityService(db)
    result = await service.get_matrix(project_id=project_id)
    return TraceMatrixResponse(
        links=[_link_to_response(l) for l in result["links"]],
        coverage={k: CoverageItem(**v) for k, v in result["coverage"].items()},
        gaps=[GapItem(**g) for g in result["gaps"]],
        urs_coverage=UrsCoverageItem(**result["urs_coverage"]),
        uncovered_urs_items=[UncoveredUrsItem(**u) for u in result["uncovered_urs_items"]],
    )

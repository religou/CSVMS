"""追溯矩阵 API 路由."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.traceability import (
    TraceMatrixResponse,
    UncoveredUrsItem,
    UrsTraceRow,
)
from app.services.traceability_service import TraceabilityService

router = APIRouter(prefix="/traceability", tags=["追溯矩阵"])


@router.get("/matrix", response_model=TraceMatrixResponse)
async def get_trace_matrix(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取以 URS 条目覆盖关系为核心的追溯矩阵（含覆盖率统计，按项目范围隔离）."""
    service = TraceabilityService(db)
    result = await service.get_matrix(project_id=project_id)
    return TraceMatrixResponse(
        urs_matrix=[UrsTraceRow(**row) for row in result["urs_matrix"]],
        uncovered_urs_items=[UncoveredUrsItem(**u) for u in result["uncovered_urs_items"]],
    )

"""仪表板 API 路由."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.traceability import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["仪表板"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取仪表板统计数据（按项目范围隔离）."""
    service = DashboardService(db)
    stats = await service.get_stats(user_id=current_user.id, project_id=project_id)
    return DashboardResponse(**stats)

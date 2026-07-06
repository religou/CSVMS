"""验证项目 API 路由."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectDetailResponse,
    ProjectMemberAdd,
    ProjectMemberCandidateListResponse,
    ProjectMemberCandidateResponse,
    ProjectMemberResponse,
    ProjectMemberUpdate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project_service import ProjectService
from app.services.permission_service import user_has_role

router = APIRouter(prefix="/projects", tags=["验证项目"])


def _get_service(db: AsyncSession, user: User) -> ProjectService:
    return ProjectService(db, is_admin=user_has_role(user, "admin"))


def _project_response(project) -> ProjectResponse:
    """Build ProjectResponse from ORM model."""
    return ProjectResponse(
        id=project.id,
        name=project.name,
        code=project.code,
        system_name=project.system_name,
        system_id=project.system_id,
        description=project.description,
        status=project.status,
        stage=project.stage,
        created_by=project.created_by,
        creator_name=project.creator.full_name if project.creator else None,
        member_count=len(project.members) if project.members else 0,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _member_response(member) -> ProjectMemberResponse:
    """Build ProjectMemberResponse from ORM model."""
    return ProjectMemberResponse(
        id=member.id,
        user_id=member.user_id,
        username=member.user.username if member.user else "",
        full_name=member.user.full_name if member.user else "",
        role=member.role,
        joined_at=member.joined_at,
    )


def _member_candidate_response(user) -> ProjectMemberCandidateResponse:
    """Build ProjectMemberCandidateResponse from ORM model."""
    return ProjectMemberCandidateResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        system_roles=[role.name for role in user.roles],
    )


@router.post("", response_model=ProjectResponse)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建验证项目."""
    service = _get_service(db, current_user)
    project = await service.create_project(
        name=data.name,
        system_id=data.system_id,
        description=data.description,
        stage=data.stage,
        created_by=current_user.id,
    )
    return _project_response(project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的项目列表."""
    service = _get_service(db, current_user)
    projects = await service.list_user_projects(
        current_user.id,
        keyword=keyword,
    )
    return [_project_response(p) for p in projects]


@router.get(
    "/{project_id}/member-candidates",
    response_model=ProjectMemberCandidateListResponse,
)
async def list_member_candidates(
    project_id: str,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    system_role: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目成员候选用户列表。"""
    service = _get_service(db, current_user)
    users, total = await service.list_member_candidates(
        project_id,
        current_user.id,
        keyword=keyword,
        page=page,
        page_size=page_size,
        system_role=system_role,
    )
    return ProjectMemberCandidateListResponse(
        items=[_member_candidate_response(user) for user in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目详情."""
    service = _get_service(db, current_user)
    await service.require_membership(project_id, current_user.id)
    project = await service.get_project(project_id)
    current_user_permissions = await service.get_current_user_permissions(
        project_id,
        current_user.id,
    )
    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        code=project.code,
        system_name=project.system_name,
        description=project.description,
        status=project.status,
        stage=project.stage,
        created_by=project.created_by,
        creator_name=project.creator.full_name if project.creator else None,
        member_count=len(project.members) if project.members else 0,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members=[_member_response(m) for m in project.members],
        current_user_permissions=current_user_permissions,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新项目信息."""
    service = _get_service(db, current_user)
    project = await service.update_project(
        project_id,
        current_user.id,
        **data.model_dump(exclude_unset=True),
    )
    return _project_response(project)


@router.post("/{project_id}/members", response_model=ProjectMemberResponse)
async def add_member(
    project_id: str,
    data: ProjectMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加项目成员."""
    service = _get_service(db, current_user)
    member = await service.add_member(
        project_id, data.user_id, data.role, current_user.id
    )
    return _member_response(member)


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
async def update_member_role(
    project_id: str,
    user_id: str,
    data: ProjectMemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新成员角色."""
    service = _get_service(db, current_user)
    member = await service.update_member_role(
        project_id, user_id, data.role, current_user.id
    )
    return _member_response(member)


@router.delete("/{project_id}/members/{user_id}")
async def remove_member(
    project_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """移除项目成员."""
    service = _get_service(db, current_user)
    await service.remove_member(project_id, user_id, current_user.id)
    return {"detail": "成员已移除"}

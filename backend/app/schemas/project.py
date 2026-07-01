"""验证项目相关 Pydantic 模型."""

from datetime import datetime

from pydantic import BaseModel

from app.models.project import ProjectRole, ProjectStatus


class ProjectCreate(BaseModel):
    """创建项目请求."""

    name: str
    system_id: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    """更新项目请求."""

    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None


class ProjectMemberAdd(BaseModel):
    """添加项目成员请求."""

    user_id: str
    role: str = ProjectRole.MEMBER.value


class ProjectMemberUpdate(BaseModel):
    """更新成员角色."""

    role: str


class ProjectMemberResponse(BaseModel):
    """项目成员响应."""

    id: str
    user_id: str
    username: str
    full_name: str
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}


class ProjectMemberCandidateResponse(BaseModel):
    """项目成员候选用户响应."""

    id: str
    username: str
    email: str
    full_name: str
    system_roles: list[str]


class ProjectMemberCandidateListResponse(BaseModel):
    """项目成员候选用户分页响应."""

    items: list[ProjectMemberCandidateResponse]
    total: int
    page: int
    page_size: int


class ProjectResponse(BaseModel):
    """项目响应."""

    id: str
    name: str
    code: str
    system_name: str
    system_id: str | None = None
    description: str | None = None
    status: ProjectStatus
    created_by: str
    creator_name: str | None = None
    member_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectDetailResponse(ProjectResponse):
    """项目详情响应（含成员列表）."""

    members: list[ProjectMemberResponse] = []
    current_user_permissions: list[str] = []

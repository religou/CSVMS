"""验证项目服务."""

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessError, PermissionDeniedError
from app.models.dictionary import DictCategory, DictItem
from app.models.project import Project, ProjectMember, ProjectRole, ProjectStatus
from app.models.user import Role, User


class ProjectService:
    """验证项目管理服务."""

    def __init__(self, db: AsyncSession, *, is_admin: bool = False) -> None:
        self.db = db
        self.is_admin = is_admin

    @staticmethod
    def _default_permission_codes_for_profile(
        permission_profile: ProjectRole,
    ) -> list[str]:
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

        if permission_profile in {ProjectRole.OWNER, ProjectRole.MANAGER}:
            return base_codes + [
                "project.documents.manage",
                "project.workflows.manage",
                "project.members.manage",
                "project.stage.manage",
            ]

        if permission_profile == ProjectRole.MEMBER:
            return base_codes + ["project.documents.manage"]

        return base_codes

    async def _get_role_item(self, role_code: str) -> DictItem:
        """按项目角色编码读取有效字典项。"""
        result = await self.db.execute(
            select(DictItem)
            .join(DictCategory, DictItem.category_id == DictCategory.id)
            .where(
                DictCategory.code == "project_role",
                DictItem.code == role_code,
            )
        )
        role_item = result.scalar_one_or_none()
        if not role_item or not role_item.is_enabled:
            raise BusinessError("项目角色不存在或已禁用")
        return role_item

    async def _resolve_permission_profile(self, role_code: str) -> ProjectRole:
        """根据项目角色字典解析角色的权限档位。"""
        role_item = await self._get_role_item(role_code)
        if not role_item.permission_profile:
            raise BusinessError(f"项目角色 '{role_code}' 未配置权限档位")

        try:
            return ProjectRole(role_item.permission_profile)
        except ValueError as exc:
            raise BusinessError(
                f"项目角色 '{role_code}' 的权限档位无效"
            ) from exc

    async def _resolve_permission_codes(self, role_code: str) -> list[str]:
        """根据项目角色字典解析有效权限编码集合。"""
        role_item = await self._get_role_item(role_code)
        if role_item.permission_codes:
            return list(role_item.permission_codes)

        permission_profile = await self._resolve_permission_profile(role_code)
        return self._default_permission_codes_for_profile(permission_profile)

    async def _generate_code(self) -> str:
        """自动生成项目编号，格式: VAL-YYYYMM-NNN."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        prefix = f"VAL-{now.strftime('%Y%m')}-"
        result = await self.db.execute(
            select(func.count()).where(Project.code.like(f"{prefix}%"))
        )
        count = result.scalar() or 0
        return f"{prefix}{count + 1:03d}"

    async def create_project(
        self,
        name: str,
        system_id: str,
        created_by: str,
        description: str | None = None,
        stage: str | None = None,
    ) -> Project:
        """创建验证项目.

        未指定阶段（stage 为 None）时保存为空值；指定阶段编码时原样保存。
        创建阶段不对阶段编码做字典有效性校验，与设计一致。
        """
        from app.models.system import System

        # 查找关联系统获取 system_name
        result = await self.db.execute(select(System).where(System.id == system_id))
        system = result.scalar_one_or_none()
        if not system:
            raise BusinessError("所选系统不存在")

        code = await self._generate_code()

        project = Project(
            name=name,
            code=code,
            system_id=system_id,
            system_name=system.name,
            description=description,
            stage=stage,
            created_by=created_by,
        )
        self.db.add(project)
        await self.db.flush()

        # 创建者自动成为项目负责人
        member = ProjectMember(
            project_id=project.id,
            user_id=created_by,
            role=ProjectRole.OWNER.value,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def get_project(self, project_id: str) -> Project:
        """获取项目详情."""
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.members))
            .where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise BusinessError("项目不存在")
        return project

    async def list_user_projects(
        self,
        user_id: str,
        *,
        keyword: str | None = None,
    ) -> list[Project]:
        """获取用户有权限的项目列表."""
        if self.is_admin:
            stmt = (
                select(Project)
                .options(selectinload(Project.members))
            )
        else:
            stmt = (
                select(Project)
                .join(ProjectMember)
                .where(ProjectMember.user_id == user_id)
                .options(selectinload(Project.members))
            )

        if keyword:
            like = f"%{keyword}%"
            from sqlalchemy import or_
            stmt = stmt.where(
                or_(
                    Project.name.ilike(like),
                    Project.code.ilike(like),
                    Project.system_name.ilike(like),
                )
            )

        stmt = stmt.order_by(Project.updated_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def list_member_candidates(
        self,
        project_id: str,
        operator_id: str,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
        system_role: str | None = None,
    ) -> tuple[list[User], int]:
        """获取可添加到项目中的系统用户候选人列表。"""
        await self.get_project(project_id)
        await self._require_role(project_id, operator_id, [ProjectRole.OWNER, ProjectRole.MANAGER])

        offset = (page - 1) * page_size
        member_subquery = select(ProjectMember.user_id).where(
            ProjectMember.project_id == project_id
        )

        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(
                User.is_active == True,  # noqa: E712
                User.is_locked == False,  # noqa: E712
                User.id.not_in(member_subquery),
            )
        )

        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    User.username.ilike(like),
                    User.full_name.ilike(like),
                    User.email.ilike(like),
                )
            )

        if system_role:
            stmt = stmt.join(User.roles).where(Role.name == system_role)

        count_stmt = select(func.count()).select_from(stmt.distinct().order_by(None).subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        result = await self.db.execute(
            stmt.distinct()
            .order_by(User.full_name.asc(), User.username.asc())
            .offset(offset)
            .limit(page_size)
        )
        users = list(result.scalars().unique().all())
        return users, total

    async def _validate_stage_code(self, stage: str) -> None:
        """校验阶段编码在 `project_stage` 分类下存在且已启用。"""
        result = await self.db.execute(
            select(DictItem)
            .join(DictCategory, DictItem.category_id == DictCategory.id)
            .where(
                DictCategory.code == "project_stage",
                DictItem.code == stage,
                DictItem.is_enabled == True,  # noqa: E712
            )
        )
        stage_item = result.scalar_one_or_none()
        if not stage_item:
            raise BusinessError("所选阶段不存在或已停用")

    async def update_project(
        self, project_id: str, user_id: str, **kwargs
    ) -> Project:
        """更新项目信息."""
        project = await self.get_project(project_id)
        await self._require_role(project_id, user_id, [ProjectRole.OWNER, ProjectRole.MANAGER])

        stage_provided = "stage" in kwargs
        stage_value = kwargs.pop("stage", None)

        if stage_provided:
            if stage_value is None:
                project.stage = None
            else:
                await self._validate_stage_code(stage_value)
                project.stage = stage_value

        for key, value in kwargs.items():
            if value is not None:
                setattr(project, key, value)

        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def add_member(
        self, project_id: str, user_id: str, role: str, operator_id: str
    ) -> ProjectMember:
        """添加项目成员."""
        await self._require_role(project_id, operator_id, [ProjectRole.OWNER, ProjectRole.MANAGER])
        await self._resolve_permission_profile(role)

        # 检查是否已是成员
        existing = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none():
            raise BusinessError("该用户已是项目成员")

        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove_member(
        self, project_id: str, user_id: str, operator_id: str
    ) -> None:
        """移除项目成员."""
        await self._require_role(project_id, operator_id, [ProjectRole.OWNER, ProjectRole.MANAGER])

        if user_id == operator_id:
            raise BusinessError("不能移除自己")

        result = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise BusinessError("该用户不是项目成员")

        await self.db.delete(member)
        await self.db.commit()

    async def update_member_role(
        self, project_id: str, user_id: str, role: str, operator_id: str
    ) -> ProjectMember:
        """更新成员角色."""
        await self._require_role(project_id, operator_id, [ProjectRole.OWNER])
        await self._resolve_permission_profile(role)

        result = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise BusinessError("该用户不是项目成员")

        member.role = role
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def check_membership(self, project_id: str, user_id: str) -> ProjectMember | None:
        """检查用户是否是项目成员."""
        result = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def require_membership(self, project_id: str, user_id: str) -> ProjectMember:
        """要求用户必须是项目成员，否则抛出异常."""
        if self.is_admin:
            return ProjectMember(
                project_id=project_id,
                user_id=user_id,
                role=ProjectRole.OWNER.value,
            )
        member = await self.check_membership(project_id, user_id)
        if not member:
            raise PermissionDeniedError("您不是该项目的成员")
        return member

    async def get_current_user_permissions(
        self,
        project_id: str,
        user_id: str,
    ) -> list[str]:
        """获取当前用户在项目下的有效权限集合。"""
        member = await self.require_membership(project_id, user_id)
        # 系统管理员拥有项目内的完整权限（包含 project.stage.manage），
        # 直接返回代码内定义的 Owner 默认权限集，避免依赖可被修改的字典数据。
        if self.is_admin:
            return self._default_permission_codes_for_profile(ProjectRole.OWNER)
        return await self._resolve_permission_codes(member.role)

    async def _require_role(
        self, project_id: str, user_id: str, roles: list[ProjectRole]
    ) -> ProjectMember:
        """要求用户具有指定项目角色."""
        if self.is_admin:
            return ProjectMember(
                project_id=project_id,
                user_id=user_id,
                role=ProjectRole.OWNER.value,
            )
        member = await self.check_membership(project_id, user_id)
        if not member:
            raise PermissionDeniedError("权限不足，需要项目管理权限")

        member_profile = await self._resolve_permission_profile(member.role)
        if member_profile not in roles:
            raise PermissionDeniedError("权限不足，需要项目管理权限")
        return member

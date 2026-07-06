"""项目成员与角色来源测试."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.core.exceptions import BusinessError, PermissionDeniedError
from app.core.security import hash_password
from app.models.dictionary import DictCategory, DictItem
from app.models.project import Project, ProjectMember, ProjectStatus
from app.models.system import System
from app.models.user import Role, User
from app.services.project_service import ProjectService


async def _register_and_login(
    client: AsyncClient,
    *,
    username: str,
    email: str,
    full_name: str,
    password: str = "User@1234",
) -> dict[str, str]:
    """注册并登录用户，返回用户信息与 token."""
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "full_name": full_name,
            "password": password,
        },
    )
    assert register_resp.status_code == 200, register_resp.text

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert login_resp.status_code == 200, login_resp.text

    return {
        "id": register_resp.json()["id"],
        "token": login_resp.json()["access_token"],
    }


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _seed_project_role_dict(db: AsyncSession) -> None:
    """写入项目角色字典，包含动态角色和无权限档位角色。"""
    category = DictCategory(
        code="project_role",
        name="项目角色",
        description="项目成员角色",
        is_system=True,
    )
    db.add(category)
    await db.flush()

    db.add_all(
        [
            DictItem(
                category_id=category.id,
                code="owner",
                label="负责人",
                permission_profile="owner",
                sort_order=1,
                is_enabled=True,
            ),
            DictItem(
                category_id=category.id,
                code="manager",
                label="项目经理",
                permission_profile="manager",
                sort_order=2,
                is_enabled=True,
            ),
            DictItem(
                category_id=category.id,
                code="member",
                label="成员",
                permission_profile="member",
                sort_order=3,
                is_enabled=True,
            ),
            DictItem(
                category_id=category.id,
                code="viewer",
                label="只读",
                permission_profile="viewer",
                sort_order=4,
                is_enabled=True,
            ),
            DictItem(
                category_id=category.id,
                code="coordinator",
                label="协调人",
                permission_profile="manager",
                sort_order=5,
                is_enabled=True,
            ),
            DictItem(
                category_id=category.id,
                code="observer",
                label="观察员",
                permission_profile=None,
                sort_order=6,
                is_enabled=True,
            ),
        ]
    )
    await db.commit()


async def _assign_system_roles(
    db: AsyncSession, username: str, role_names: list[str]
) -> None:
    """为指定用户名分配系统角色。"""
    role_objects: list[Role] = []
    for role_name in role_names:
        role_result = await db.execute(select(Role).where(Role.name == role_name))
        role = role_result.scalar_one_or_none()
        if role is None:
            role = Role(name=role_name, display_name=role_name)
            db.add(role)
            await db.flush()
        role_objects.append(role)

    user_result = await db.execute(select(User).where(User.username == username))
    user = user_result.scalar_one()
    user.roles = role_objects
    await db.commit()


async def _set_user_flags(
    db: AsyncSession, username: str, *, is_active: bool | None = None, is_locked: bool | None = None
) -> None:
    """更新用户启用和锁定状态。"""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one()
    if is_active is not None:
        user.is_active = is_active
    if is_locked is not None:
        user.is_locked = is_locked
    await db.commit()


async def _create_system(
    db: AsyncSession, *, code: str = "CSVS", name: str = "CSVS"
) -> str:
    """写入一个系统并返回其 id，供项目创建请求使用。"""
    system = System(code=code, name=name)
    db.add(system)
    await db.flush()
    await db.commit()
    return system.id


@pytest.mark.asyncio
async def test_dynamic_project_role_uses_permission_profile(
    client: AsyncClient, db_session: AsyncSession
):
    """动态项目角色应按其权限档位继承 manager 级操作权限。"""
    await _seed_project_role_dict(db_session)
    owner = await _register_and_login(
        client,
        username="project_owner",
        email="project-owner@example.com",
        full_name="Project Owner",
    )
    coordinator = await _register_and_login(
        client,
        username="project_coordinator",
        email="project-coordinator@example.com",
        full_name="Project Coordinator",
    )
    viewer = await _register_and_login(
        client,
        username="project_viewer",
        email="project-viewer@example.com",
        full_name="Project Viewer",
    )

    system_id = await _create_system(db_session)
    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "动态角色项目", "system_id": system_id, "description": ""},
        headers=_auth_header(owner["token"]),
    )
    assert project_resp.status_code == 200, project_resp.text
    project_id = project_resp.json()["id"]

    add_resp = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": coordinator["id"], "role": "coordinator"},
        headers=_auth_header(owner["token"]),
    )
    assert add_resp.status_code == 200, add_resp.text
    assert add_resp.json()["role"] == "coordinator"

    delegated_resp = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": viewer["id"], "role": "viewer"},
        headers=_auth_header(coordinator["token"]),
    )
    assert delegated_resp.status_code == 200, delegated_resp.text
    assert delegated_resp.json()["role"] == "viewer"


@pytest.mark.asyncio
async def test_project_role_without_permission_profile_is_rejected(
    client: AsyncClient, db_session: AsyncSession
):
    """没有权限档位的项目角色代码不能用于项目成员分配。"""
    await _seed_project_role_dict(db_session)
    owner = await _register_and_login(
        client,
        username="role_owner",
        email="role-owner@example.com",
        full_name="Role Owner",
    )
    observer = await _register_and_login(
        client,
        username="role_observer",
        email="role-observer@example.com",
        full_name="Role Observer",
    )

    system_id = await _create_system(db_session)
    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "无权限档位项目", "system_id": system_id, "description": ""},
        headers=_auth_header(owner["token"]),
    )
    assert project_resp.status_code == 200, project_resp.text
    project_id = project_resp.json()["id"]

    add_resp = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": observer["id"], "role": "observer"},
        headers=_auth_header(owner["token"]),
    )
    assert add_resp.status_code == 400, add_resp.text
    assert "权限档位" in add_resp.json()["detail"]


@pytest.mark.asyncio
async def test_manager_profile_member_can_list_filtered_member_candidates(
    client: AsyncClient, db_session: AsyncSession
):
    """继承 manager 权限档位的动态角色可以读取过滤后的成员候选人列表。"""
    await _seed_project_role_dict(db_session)
    owner = await _register_and_login(
        client,
        username="candidate_owner",
        email="candidate-owner@example.com",
        full_name="Candidate Owner",
    )
    coordinator = await _register_and_login(
        client,
        username="candidate_coordinator",
        email="candidate-coordinator@example.com",
        full_name="Candidate Coordinator",
    )
    eligible = await _register_and_login(
        client,
        username="candidate_validation",
        email="candidate-validation@example.com",
        full_name="Candidate Validation",
    )
    existing_member = await _register_and_login(
        client,
        username="candidate_existing",
        email="candidate-existing@example.com",
        full_name="Candidate Existing",
    )
    disabled_user = await _register_and_login(
        client,
        username="candidate_disabled",
        email="candidate-disabled@example.com",
        full_name="Candidate Disabled",
    )
    locked_user = await _register_and_login(
        client,
        username="candidate_locked",
        email="candidate-locked@example.com",
        full_name="Candidate Locked",
    )

    await _assign_system_roles(db_session, "candidate_validation", ["validation_admin"])
    await _assign_system_roles(db_session, "candidate_existing", ["validation_admin"])
    await _assign_system_roles(db_session, "candidate_disabled", ["validation_admin"])
    await _assign_system_roles(db_session, "candidate_locked", ["validation_admin"])
    await _set_user_flags(db_session, "candidate_disabled", is_active=False)
    await _set_user_flags(db_session, "candidate_locked", is_locked=True)

    system_id = await _create_system(db_session)
    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "候选用户项目", "system_id": system_id, "description": ""},
        headers=_auth_header(owner["token"]),
    )
    assert project_resp.status_code == 200, project_resp.text
    project_id = project_resp.json()["id"]

    coordinator_member_resp = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": coordinator["id"], "role": "coordinator"},
        headers=_auth_header(owner["token"]),
    )
    assert coordinator_member_resp.status_code == 200, coordinator_member_resp.text

    existing_member_resp = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": existing_member["id"], "role": "viewer"},
        headers=_auth_header(owner["token"]),
    )
    assert existing_member_resp.status_code == 200, existing_member_resp.text

    candidates_resp = await client.get(
        f"/api/v1/projects/{project_id}/member-candidates",
        params={
            "keyword": "Candidate",
            "page": 1,
            "page_size": 1,
            "system_role": "validation_admin",
        },
        headers=_auth_header(coordinator["token"]),
    )
    assert candidates_resp.status_code == 200, candidates_resp.text
    payload = candidates_resp.json()
    assert payload["total"] == 1
    assert payload["page"] == 1
    assert payload["page_size"] == 1
    assert [item["username"] for item in payload["items"]] == [
        "candidate_validation"
    ]
    assert payload["items"][0]["system_roles"] == ["validation_admin"]


@pytest.mark.asyncio
async def test_admin_can_list_member_candidates_without_membership(
    client: AsyncClient, db_session: AsyncSession
):
    """系统管理员即使不是项目成员，也可以查看项目成员候选人。"""
    await _seed_project_role_dict(db_session)
    owner = await _register_and_login(
        client,
        username="outsider_owner",
        email="outsider-owner@example.com",
        full_name="Outsider Owner",
    )
    admin_user = await _register_and_login(
        client,
        username="outsider_admin",
        email="outsider-admin@example.com",
        full_name="Outsider Admin",
    )
    eligible = await _register_and_login(
        client,
        username="outsider_candidate",
        email="outsider-candidate@example.com",
        full_name="Outsider Candidate",
    )

    await _assign_system_roles(db_session, "outsider_admin", ["admin"])
    await _assign_system_roles(db_session, "outsider_candidate", ["user"])

    system_id = await _create_system(db_session)
    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "管理员候选项目", "system_id": system_id, "description": ""},
        headers=_auth_header(owner["token"]),
    )
    assert project_resp.status_code == 200, project_resp.text
    project_id = project_resp.json()["id"]

    candidates_resp = await client.get(
        f"/api/v1/projects/{project_id}/member-candidates",
        headers=_auth_header(admin_user["token"]),
    )
    assert candidates_resp.status_code == 200, candidates_resp.text
    usernames = [item["username"] for item in candidates_resp.json()["items"]]
    assert "outsider_candidate" in usernames
    assert "outsider_owner" not in usernames
    assert "outsider_admin" in usernames


@pytest.mark.asyncio
async def test_project_detail_returns_current_user_permissions(
    client: AsyncClient, db_session: AsyncSession
):
    """项目详情应返回当前用户在该项目下的有效权限集合。"""
    await _seed_project_role_dict(db_session)
    owner = await _register_and_login(
        client,
        username="permission_owner",
        email="permission-owner@example.com",
        full_name="Permission Owner",
    )
    coordinator = await _register_and_login(
        client,
        username="permission_coordinator",
        email="permission-coordinator@example.com",
        full_name="Permission Coordinator",
    )

    role_item_result = await db_session.execute(
        select(DictItem)
        .join(DictCategory, DictItem.category_id == DictCategory.id)
        .where(
            DictCategory.code == "project_role",
            DictItem.code == "coordinator",
        )
    )
    coordinator_role = role_item_result.scalar_one()
    coordinator_role.permission_codes = [
        "project.dashboard.menu",
        "project.documents.menu",
        "project.documents.manage",
    ]
    await db_session.commit()

    system_id = await _create_system(db_session)
    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "项目权限详情", "system_id": system_id, "description": ""},
        headers=_auth_header(owner["token"]),
    )
    assert project_resp.status_code == 200, project_resp.text
    project_id = project_resp.json()["id"]

    add_resp = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": coordinator["id"], "role": "coordinator"},
        headers=_auth_header(owner["token"]),
    )
    assert add_resp.status_code == 200, add_resp.text

    detail_resp = await client.get(
        f"/api/v1/projects/{project_id}",
        headers=_auth_header(coordinator["token"]),
    )
    assert detail_resp.status_code == 200, detail_resp.text
    assert detail_resp.json()["current_user_permissions"] == [
        "project.dashboard.menu",
        "project.documents.menu",
        "project.documents.manage",
    ]


async def _create_owner_and_system(
    db: AsyncSession, *, username: str
) -> tuple[str, str]:
    """直接写入一个用户与一个系统，返回 (user_id, system_id)。"""
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username,
        password_hash=hash_password("Owner@1234"),
    )
    db.add(user)
    await db.flush()

    system = System(code=f"SYS-{username}", name=f"系统-{username}")
    db.add(system)
    await db.flush()
    await db.commit()

    return user.id, system.id


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    project_name=st.text(min_size=1, max_size=50),
    stage=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
)
@pytest.mark.asyncio
async def test_property_create_project_stage_lands_as_requested(
    db_session: AsyncSession, project_name: str, stage: str | None
):
    """
    Feature: project-stage-management, Property 4: 项目创建时阶段字段按请求原样落地

    For any 合法的项目创建请求，若请求未指定阶段，新创建项目的 Project_Stage_Field
    SHALL 为空；若请求指定了阶段编码，新创建项目的 Project_Stage_Field SHALL 等于该编码。

    Validates: Requirements 2.3, 2.4
    """
    # 每个样例使用独立的用户名/系统编码，避免唯一性约束冲突
    import uuid

    suffix = uuid.uuid4().hex[:12]
    user_id, system_id = await _create_owner_and_system(
        db_session, username=f"prop4-{suffix}"
    )

    service = ProjectService(db_session)
    project = await service.create_project(
        name=project_name,
        system_id=system_id,
        created_by=user_id,
        stage=stage,
    )

    if stage is None:
        assert project.stage is None
    else:
        assert project.stage == stage

    # 与数据库中持久化的值保持一致
    result = await db_session.execute(select(Project).where(Project.id == project.id))
    persisted = result.scalar_one()
    assert persisted.stage == stage


async def _ensure_project_stage_dict(db: AsyncSession) -> tuple[str, str]:
    """确保 project_stage 字典存在（幂等），返回 (已启用阶段编码, 已禁用阶段编码)。"""
    result = await db.execute(
        select(DictCategory).where(DictCategory.code == "project_stage")
    )
    category = result.scalar_one_or_none()
    if category is None:
        category = DictCategory(
            code="project_stage",
            name="项目阶段",
            description="项目阶段",
            is_system=True,
        )
        db.add(category)
        await db.flush()
        db.add_all(
            [
                DictItem(
                    category_id=category.id,
                    code="prop6_enabled",
                    label="启用阶段",
                    sort_order=1,
                    is_enabled=True,
                ),
                DictItem(
                    category_id=category.id,
                    code="prop6_disabled",
                    label="禁用阶段",
                    sort_order=2,
                    is_enabled=False,
                ),
            ]
        )
        await db.commit()
    return "prop6_enabled", "prop6_disabled"


async def _ensure_project_role_dict(db: AsyncSession) -> None:
    """确保 project_role 字典存在（幂等），复用 _seed_project_role_dict。"""
    result = await db.execute(
        select(DictCategory).where(DictCategory.code == "project_role")
    )
    category = result.scalar_one_or_none()
    if category is None:
        await _seed_project_role_dict(db)


async def _ensure_project_stage_items(
    db: AsyncSession, *, enabled_codes: list[str], disabled_codes: list[str]
) -> None:
    """确保 project_stage 分类下存在指定的启用/禁用字典项（幂等，按需追加）。"""
    result = await db.execute(
        select(DictCategory).where(DictCategory.code == "project_stage")
    )
    category = result.scalar_one_or_none()
    if category is None:
        category = DictCategory(
            code="project_stage",
            name="项目阶段",
            description="项目阶段",
            is_system=True,
        )
        db.add(category)
        await db.flush()

    sort_order = 100
    for code in enabled_codes:
        existing = await db.execute(
            select(DictItem).where(
                DictItem.category_id == category.id, DictItem.code == code
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(
                DictItem(
                    category_id=category.id,
                    code=code,
                    label=f"阶段-{code}",
                    sort_order=sort_order,
                    is_enabled=True,
                )
            )
            sort_order += 1

    for code in disabled_codes:
        existing = await db.execute(
            select(DictItem).where(
                DictItem.category_id == category.id, DictItem.code == code
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(
                DictItem(
                    category_id=category.id,
                    code=code,
                    label=f"阶段-{code}",
                    sort_order=sort_order,
                    is_enabled=False,
                )
            )
            sort_order += 1

    await db.commit()


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    role_kind=st.sampled_from(["owner", "manager"]),
    scenario=st.sampled_from(
        ["valid_enabled", "explicit_none", "invalid_code", "no_stage_field"]
    ),
)
@pytest.mark.asyncio
async def test_property_stage_update_tri_state_semantics(
    client: AsyncClient, db_session: AsyncSession, role_kind: str, scenario: str
):
    """
    Feature: project-stage-management, Property 7: 阶段更新的三态语义

    For any 项目及具备 Owner 或 Manager 角色的用户提交的更新请求：
    (a) 若请求中的阶段编码对应一个已启用字典项，Project_Stage_Field SHALL 被更新为
        该编码，且 API 响应中的阶段字段与之一致；
    (b) 若请求显式将阶段字段设置为空值，Project_Stage_Field SHALL 被更新为空值，
        且 API 响应中的阶段字段与之一致；
    (c) 若请求中的阶段编码非空但不对应任何已启用字典项，更新 SHALL 被拒绝并返回
        描述性错误，Project_Stage_Field 保持不变；
    (d) 若请求中完全不包含阶段字段，Project_Stage_Field SHALL 保持不变，且不因此
        阻塞请求中其他字段的更新。

    Validates: Requirements 3.3, 3.4, 3.5, 3.6, 3.7
    """
    import uuid

    from app.models.system import System

    suffix = uuid.uuid4().hex[:12]
    enabled_a = f"prop7_a_{suffix}"
    enabled_b = f"prop7_b_{suffix}"
    disabled_stage = f"prop7_disabled_{suffix}"

    await _ensure_project_stage_items(
        db_session,
        enabled_codes=[enabled_a, enabled_b],
        disabled_codes=[disabled_stage],
    )
    await _ensure_project_role_dict(db_session)

    owner = await _register_and_login(
        client,
        username=f"prop7_owner_{suffix}",
        email=f"prop7-owner-{suffix}@example.com",
        full_name="Prop7 Owner",
    )

    system = System(code=f"SYS-prop7-{suffix}", name=f"系统-prop7-{suffix}")
    db_session.add(system)
    await db_session.commit()

    initial_stage = enabled_a
    service = ProjectService(db_session)
    project = await service.create_project(
        name=f"prop7-project-{suffix}",
        system_id=system.id,
        created_by=owner["id"],
        stage=initial_stage,
    )

    if role_kind == "owner":
        acting_token = owner["token"]
    else:
        manager = await _register_and_login(
            client,
            username=f"prop7_manager_{suffix}",
            email=f"prop7-manager-{suffix}@example.com",
            full_name="Prop7 Manager",
        )
        add_resp = await client.post(
            f"/api/v1/projects/{project.id}/members",
            json={"user_id": manager["id"], "role": "manager"},
            headers=_auth_header(owner["token"]),
        )
        assert add_resp.status_code == 200, add_resp.text
        acting_token = manager["token"]

    if scenario == "valid_enabled":
        payload: dict = {"stage": enabled_b}
    elif scenario == "explicit_none":
        payload = {"stage": None}
    elif scenario == "invalid_code":
        payload = {"stage": f"nonexistent_{suffix}"}
    else:  # no_stage_field
        payload = {"name": f"prop7-renamed-{suffix}"}

    resp = await client.patch(
        f"/api/v1/projects/{project.id}",
        json=payload,
        headers=_auth_header(acting_token),
    )

    # db_session 的身份映射中仍缓存着创建时的 project 对象，需先清除以便
    # 反映 API 层（不同会话）提交的最新持久化数据。
    db_session.expunge_all()
    result = await db_session.execute(select(Project).where(Project.id == project.id))
    persisted = result.scalar_one()

    if scenario == "valid_enabled":
        assert resp.status_code == 200, resp.text
        assert resp.json()["stage"] == enabled_b
        assert persisted.stage == enabled_b
    elif scenario == "explicit_none":
        assert resp.status_code == 200, resp.text
        assert resp.json()["stage"] is None
        assert persisted.stage is None
    elif scenario == "invalid_code":
        assert resp.status_code == 400, resp.text
        assert resp.json().get("detail")
        assert persisted.stage == initial_stage
    else:  # no_stage_field: 阶段保持不变，且不阻塞其他字段更新
        assert resp.status_code == 200, resp.text
        assert resp.json()["stage"] == initial_stage
        assert resp.json()["name"] == payload["name"]
        assert persisted.stage == initial_stage
        assert persisted.name == payload["name"]


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    initial_stage_kind=st.sampled_from(["none", "a"]),
    initial_status=st.sampled_from(list(ProjectStatus)),
    new_stage_kind=st.sampled_from(["none", "a", "b"]),
    new_status=st.sampled_from(list(ProjectStatus)),
)
@pytest.mark.asyncio
async def test_property_stage_and_status_fields_are_independent(
    db_session: AsyncSession,
    initial_stage_kind: str,
    initial_status: ProjectStatus,
    new_stage_kind: str,
    new_status: ProjectStatus,
):
    """
    Feature: project-stage-management, Property 5: 阶段字段与状态字段相互独立

    For any 具有任意阶段与状态取值组合的项目，仅更新其阶段时状态保持不变；仅更新
    其状态时阶段保持不变。

    Validates: Requirements 2.5, 2.6
    """
    import uuid

    suffix = uuid.uuid4().hex[:12]
    stage_a = f"prop5_a_{suffix}"
    stage_b = f"prop5_b_{suffix}"
    stage_by_kind = {"none": None, "a": stage_a, "b": stage_b}

    await _ensure_project_stage_items(
        db_session, enabled_codes=[stage_a, stage_b], disabled_codes=[]
    )
    await _ensure_project_role_dict(db_session)

    owner_id, system_id = await _create_owner_and_system(
        db_session, username=f"prop5-owner-{suffix}"
    )

    service = ProjectService(db_session)
    initial_stage = stage_by_kind[initial_stage_kind]
    project = await service.create_project(
        name=f"prop5-project-{suffix}",
        system_id=system_id,
        created_by=owner_id,
        stage=initial_stage,
    )

    # 直接设置初始状态，模拟"具有任意阶段与状态取值组合的项目"
    project.status = initial_status
    await db_session.commit()

    # (a) 仅更新阶段，状态应保持不变
    new_stage = stage_by_kind[new_stage_kind]
    await service.update_project(project.id, owner_id, stage=new_stage)

    db_session.expunge_all()
    result = await db_session.execute(select(Project).where(Project.id == project.id))
    after_stage_update = result.scalar_one()
    assert after_stage_update.stage == new_stage
    assert after_stage_update.status == initial_status

    # (b) 仅更新状态，阶段应保持不变（沿用上一步更新后的阶段值）
    await service.update_project(project.id, owner_id, status=new_status)

    db_session.expunge_all()
    result = await db_session.execute(select(Project).where(Project.id == project.id))
    after_status_update = result.scalar_one()
    assert after_status_update.status == new_status
    assert after_status_update.stage == new_stage


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    stage_kind=st.sampled_from(
        ["valid_enabled", "invalid_code", "disabled_code", "explicit_none"]
    ),
    membership_kind=st.sampled_from(["member_role", "viewer_role", "no_membership"]),
)
@pytest.mark.asyncio
async def test_property_stage_update_permission_check_precedes_stage_validation(
    db_session: AsyncSession, stage_kind: str, membership_kind: str
):
    """
    Feature: project-stage-management, Property 6: 权限校验先于阶段编码有效性校验

    For any 项目及任意在该项目中既不具备 Owner 也不具备 Manager 角色的用户，提交
    阶段更新请求（无论所提交的阶段编码是有效已启用编码、无效编码、已禁用编码，还
    是显式空值）SHALL 始终被拒绝并返回权限不足错误，且该项目的 Project_Stage_Field
    保持不变。

    Validates: Requirements 3.2
    """
    import uuid

    suffix = uuid.uuid4().hex[:12]
    enabled_stage, disabled_stage = await _ensure_project_stage_dict(db_session)
    await _ensure_project_role_dict(db_session)

    owner_id, system_id = await _create_owner_and_system(
        db_session, username=f"prop6-owner-{suffix}"
    )

    service = ProjectService(db_session)
    initial_stage = enabled_stage
    project = await service.create_project(
        name=f"prop6-project-{suffix}",
        system_id=system_id,
        created_by=owner_id,
        stage=initial_stage,
    )

    # 创建一个既非 Owner 也非 Manager 的用户
    non_manager = User(
        username=f"prop6-user-{suffix}",
        email=f"prop6-user-{suffix}@example.com",
        full_name=f"prop6-user-{suffix}",
        password_hash=hash_password("User@1234"),
    )
    db_session.add(non_manager)
    await db_session.flush()
    await db_session.commit()

    if membership_kind == "member_role":
        db_session.add(
            ProjectMember(project_id=project.id, user_id=non_manager.id, role="member")
        )
        await db_session.commit()
    elif membership_kind == "viewer_role":
        db_session.add(
            ProjectMember(project_id=project.id, user_id=non_manager.id, role="viewer")
        )
        await db_session.commit()
    # membership_kind == "no_membership": 不添加成员关系

    stage_kwargs: dict[str, str | None] = {}
    if stage_kind == "valid_enabled":
        stage_kwargs["stage"] = enabled_stage
    elif stage_kind == "invalid_code":
        stage_kwargs["stage"] = f"nonexistent-{suffix}"
    elif stage_kind == "disabled_code":
        stage_kwargs["stage"] = disabled_stage
    elif stage_kind == "explicit_none":
        stage_kwargs["stage"] = None

    with pytest.raises(PermissionDeniedError):
        await service.update_project(project.id, non_manager.id, **stage_kwargs)

    # 项目的阶段字段保持不变
    result = await db_session.execute(select(Project).where(Project.id == project.id))
    persisted = result.scalar_one()
    assert persisted.stage == initial_stage


@pytest.mark.asyncio
async def test_update_project_stage_for_nonexistent_project(
    client: AsyncClient, db_session: AsyncSession
):
    """阶段更新请求指向不存在的项目时应返回资源不存在错误，且不产生数据变更.

    Requirements: 3.1
    """
    import uuid

    await _ensure_project_stage_dict(db_session)
    await _ensure_project_role_dict(db_session)

    owner = await _register_and_login(
        client,
        username="stage_notfound_owner",
        email="stage-notfound-owner@example.com",
        full_name="Stage NotFound Owner",
    )

    # 创建一个真实存在的项目，用于确认它不会被无关的失败请求影响
    owner_id, system_id = await _create_owner_and_system(
        db_session, username="stage_notfound_system_owner"
    )
    service_for_setup = ProjectService(db_session)
    existing_project = await service_for_setup.create_project(
        name="存在的项目",
        system_id=system_id,
        created_by=owner["id"],
    )
    existing_project_id = existing_project.id
    existing_project_stage_before = existing_project.stage

    nonexistent_project_id = str(uuid.uuid4())

    # API 层：PATCH 一个不存在的项目 id
    update_resp = await client.patch(
        f"/api/v1/projects/{nonexistent_project_id}",
        json={"stage": "some-stage"},
        headers=_auth_header(owner["token"]),
    )
    assert update_resp.status_code == 400, update_resp.text
    assert "不存在" in update_resp.json()["detail"]

    # Service 层：直接调用 update_project 也应抛出资源不存在错误
    service = ProjectService(db_session)
    with pytest.raises(BusinessError, match="不存在"):
        await service.update_project(
            nonexistent_project_id, owner["id"], stage="some-stage"
        )

    # 不产生数据变更：既有项目的阶段字段保持不变
    result = await db_session.execute(
        select(Project).where(Project.id == existing_project_id)
    )
    persisted = result.scalar_one()
    assert persisted.stage == existing_project_stage_before

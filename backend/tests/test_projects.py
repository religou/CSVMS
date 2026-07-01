"""项目成员与角色来源测试."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.dictionary import DictCategory, DictItem
from app.models.user import Role, User


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

    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "动态角色项目", "system_name": "CSVS", "description": ""},
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

    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "无权限档位项目", "system_name": "CSVS", "description": ""},
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

    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "候选用户项目", "system_name": "CSVS", "description": ""},
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

    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "管理员候选项目", "system_name": "CSVS", "description": ""},
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

    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "项目权限详情", "system_name": "CSVS", "description": ""},
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

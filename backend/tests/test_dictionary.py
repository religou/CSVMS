"""字典管理 API 测试."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from app.models.user import Role, User
from app.models.dictionary import DictCategory, DictItem
from app.core.security import hash_password
from app.scripts import seed_dict as seed_dict_module
from app.scripts.seed_dict import seed_dict

# 字典项编码使用的字符集：小写字母、数字、下划线、连字符
_DICT_ITEM_CODE_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789_-"


async def _create_admin(db: AsyncSession) -> None:
    """创建管理员用户用于字典管理测试."""
    role = Role(name="admin", display_name="管理员")
    db.add(role)
    await db.flush()

    user = User(
        username="dict-admin",
        email="dict-admin@example.com",
        full_name="Dict Admin",
        password_hash=hash_password("Admin@1234"),
    )
    user.roles = [role]
    db.add(user)
    await db.commit()


async def _ensure_admin(db: AsyncSession) -> None:
    """确保管理员用户存在（幂等），避免在属性测试的多个样例间重复创建导致唯一性冲突。"""
    result = await db.execute(select(User).where(User.username == "dict-admin"))
    if result.scalar_one_or_none() is not None:
        return
    await _create_admin(db)


async def _ensure_category(db: AsyncSession, *, code: str, is_system: bool = False) -> str:
    """确保指定编码的字典类别存在（幂等），返回其 id。"""
    result = await db.execute(select(DictCategory).where(DictCategory.code == code))
    category = result.scalar_one_or_none()
    if category is None:
        category = DictCategory(code=code, name=code, is_system=is_system)
        db.add(category)
        await db.commit()
        await db.refresh(category)
    return category.id


async def _ensure_non_admin(db: AsyncSession) -> None:
    """确保一个不具备任何角色（含 admin）的用户存在（幂等）。"""
    result = await db.execute(select(User).where(User.username == "dict-nonadmin"))
    if result.scalar_one_or_none() is not None:
        return
    user = User(
        username="dict-nonadmin",
        email="dict-nonadmin@example.com",
        full_name="Dict NonAdmin",
        password_hash=hash_password("User@1234"),
    )
    db.add(user)
    await db.commit()


async def _ensure_stable_stage_item(db: AsyncSession, *, category_id: str) -> DictItem:
    """确保 project_stage 分类下存在一个用于权限拒绝断言的稳定字典项（幂等），返回该字典项。"""
    result = await db.execute(
        select(DictItem).where(
            DictItem.category_id == category_id, DictItem.code == "prop3-stable-item"
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        item = DictItem(
            category_id=category_id,
            code="prop3-stable-item",
            label="稳定阶段项",
            sort_order=1,
            is_enabled=True,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
    return item


async def _login(client: AsyncClient, username: str, password: str) -> str:
    """登录并返回 access token."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_project_role_item_supports_permission_profile(
    client: AsyncClient, db_session: AsyncSession
):
    """项目角色字典项应支持权限档位字段的创建、读取和更新。"""
    await _create_admin(db_session)
    token = await _login(client, "dict-admin", "Admin@1234")

    category_resp = await client.post(
        "/api/v1/dict/categories",
        json={
            "code": "project_role",
            "name": "项目角色",
            "description": "项目角色字典",
        },
        headers=_auth_header(token),
    )
    assert category_resp.status_code == 200, category_resp.text
    category_id = category_resp.json()["id"]

    create_resp = await client.post(
        f"/api/v1/dict/categories/{category_id}/items",
        json={
            "code": "coordinator",
            "label": "协调人",
            "sort_order": 5,
            "extra": "cyan",
            "permission_profile": "manager",
        },
        headers=_auth_header(token),
    )
    assert create_resp.status_code == 200, create_resp.text
    assert create_resp.json()["permission_profile"] == "manager"

    list_resp = await client.get(
        "/api/v1/dict/categories/project_role/items",
        headers=_auth_header(token),
    )
    assert list_resp.status_code == 200, list_resp.text
    created_item = next(item for item in list_resp.json() if item["code"] == "coordinator")
    assert created_item["permission_profile"] == "manager"

    update_resp = await client.patch(
        f"/api/v1/dict/items/{create_resp.json()['id']}",
        json={"permission_profile": "viewer"},
        headers=_auth_header(token),
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["permission_profile"] == "viewer"


@pytest.mark.asyncio
async def test_project_role_item_supports_permission_codes(
    client: AsyncClient, db_session: AsyncSession
):
    """项目角色字典项应支持独立的权限编码映射字段。"""
    await _create_admin(db_session)
    token = await _login(client, "dict-admin", "Admin@1234")

    category_resp = await client.post(
        "/api/v1/dict/categories",
        json={
            "code": "project_role",
            "name": "项目角色",
            "description": "项目角色字典",
        },
        headers=_auth_header(token),
    )
    assert category_resp.status_code == 200, category_resp.text
    category_id = category_resp.json()["id"]

    create_resp = await client.post(
        f"/api/v1/dict/categories/{category_id}/items",
        json={
            "code": "coordinator",
            "label": "协调人",
            "sort_order": 5,
            "permission_profile": "manager",
            "permission_codes": [
                "project.dashboard.menu",
                "project.documents.menu",
                "project.members.manage",
            ],
        },
        headers=_auth_header(token),
    )
    assert create_resp.status_code == 200, create_resp.text
    assert create_resp.json()["permission_codes"] == [
        "project.dashboard.menu",
        "project.documents.menu",
        "project.members.manage",
    ]

    update_resp = await client.patch(
        f"/api/v1/dict/items/{create_resp.json()['id']}",
        json={"permission_codes": ["project.audit_log.view"]},
        headers=_auth_header(token),
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["permission_codes"] == ["project.audit_log.view"]

    list_resp = await client.get(
        "/api/v1/dict/categories/project_role/items",
        headers=_auth_header(token),
    )
    assert list_resp.status_code == 200, list_resp.text
    created_item = next(item for item in list_resp.json() if item["code"] == "coordinator")
    assert created_item["permission_codes"] == ["project.audit_log.view"]


@pytest.mark.asyncio
async def test_seed_dict_creates_project_stage_category(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """首次运行种子脚本应创建 project_stage 分类（is_system=True）及不少于 3 个字典项。"""
    from tests.conftest import TestSessionLocal

    monkeypatch.setattr(seed_dict_module, "get_session_factory", lambda: TestSessionLocal)

    await seed_dict()

    result = await db_session.execute(
        select(DictCategory).where(DictCategory.code == "project_stage")
    )
    category = result.scalar_one_or_none()
    assert category is not None
    assert category.is_system is True

    items_result = await db_session.execute(
        select(DictItem).where(DictItem.category_id == category.id)
    )
    items = items_result.scalars().all()
    assert len(items) >= 3


@pytest.mark.asyncio
async def test_seed_dict_is_idempotent(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """重复运行种子脚本不应产生重复数据，也不应报错。"""
    from tests.conftest import TestSessionLocal

    monkeypatch.setattr(seed_dict_module, "get_session_factory", lambda: TestSessionLocal)

    await seed_dict()

    category_count_before = (
        await db_session.execute(select(func.count()).select_from(DictCategory))
    ).scalar_one()
    item_count_before = (
        await db_session.execute(select(func.count()).select_from(DictItem))
    ).scalar_one()

    # 第二次运行不应抛出异常
    await seed_dict()

    category_count_after = (
        await db_session.execute(select(func.count()).select_from(DictCategory))
    ).scalar_one()
    item_count_after = (
        await db_session.execute(select(func.count()).select_from(DictItem))
    ).scalar_one()

    assert category_count_after == category_count_before
    assert item_count_after == item_count_before


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    existing_code=st.text(alphabet=_DICT_ITEM_CODE_ALPHABET, min_size=1, max_size=20),
    new_code=st.text(alphabet=_DICT_ITEM_CODE_ALPHABET, min_size=1, max_size=20),
    use_project_stage=st.booleans(),
)
@pytest.mark.asyncio
async def test_property_dict_item_code_unique_within_category(
    client: AsyncClient,
    db_session: AsyncSession,
    existing_code: str,
    new_code: str,
    use_project_stage: bool,
):
    """
    Feature: project-stage-management, Property 1: 字典项类别内编码唯一性

    For any 字典类别（包括 project_stage）及其内已存在的任意字典项编码，在该类别下
    尝试新增一个使用相同编码的字典项，系统 SHALL 拒绝该操作并返回描述性错误，且该
    类别下已有字典项数据保持不变；若使用一个该类别下未被使用的编码新增，系统 SHALL
    成功创建。

    Validates: Requirements 1.4, 1.5
    """
    assume(existing_code != new_code)

    await _ensure_admin(db_session)
    token = await _login(client, "dict-admin", "Admin@1234")

    if use_project_stage:
        category_id = await _ensure_category(
            db_session, code="project_stage", is_system=True
        )
    else:
        suffix = uuid.uuid4().hex[:12]
        category_id = await _ensure_category(
            db_session, code=f"prop1-cat-{suffix}", is_system=False
        )

    # 该类别（尤其是跨样例复用的 project_stage）可能已存在同名编码，遇到时跳过本次样例
    existing_code_check = await db_session.execute(
        select(DictItem).where(
            DictItem.category_id == category_id, DictItem.code == existing_code
        )
    )
    assume(existing_code_check.scalar_one_or_none() is None)
    new_code_check = await db_session.execute(
        select(DictItem).where(
            DictItem.category_id == category_id, DictItem.code == new_code
        )
    )
    assume(new_code_check.scalar_one_or_none() is None)

    # 先创建一个已存在的字典项
    create_existing_resp = await client.post(
        f"/api/v1/dict/categories/{category_id}/items",
        json={"code": existing_code, "label": "已存在选项"},
        headers=_auth_header(token),
    )
    assert create_existing_resp.status_code == 200, create_existing_resp.text

    count_before = (
        await db_session.execute(
            select(func.count())
            .select_from(DictItem)
            .where(DictItem.category_id == category_id)
        )
    ).scalar_one()

    # 使用相同编码新增应被拒绝，且返回描述性错误
    duplicate_resp = await client.post(
        f"/api/v1/dict/categories/{category_id}/items",
        json={"code": existing_code, "label": "重复编码选项"},
        headers=_auth_header(token),
    )
    assert duplicate_resp.status_code == 400, duplicate_resp.text
    assert duplicate_resp.json()["detail"]

    count_after_duplicate = (
        await db_session.execute(
            select(func.count())
            .select_from(DictItem)
            .where(DictItem.category_id == category_id)
        )
    ).scalar_one()
    assert count_after_duplicate == count_before

    # 使用未被使用的编码新增应成功
    new_item_resp = await client.post(
        f"/api/v1/dict/categories/{category_id}/items",
        json={"code": new_code, "label": "新选项"},
        headers=_auth_header(token),
    )
    assert new_item_resp.status_code == 200, new_item_resp.text
    assert new_item_resp.json()["code"] == new_code

    count_after_new = (
        await db_session.execute(
            select(func.count())
            .select_from(DictItem)
            .where(DictItem.category_id == category_id)
        )
    ).scalar_one()
    assert count_after_new == count_before + 1


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    code_fragment=st.text(alphabet=_DICT_ITEM_CODE_ALPHABET, min_size=1, max_size=20),
    is_system=st.booleans(),
    item_count=st.integers(min_value=0, max_value=3),
)
@pytest.mark.asyncio
async def test_property_delete_system_category_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    code_fragment: str,
    is_system: bool,
    item_count: int,
):
    """
    Feature: project-stage-management, Property 2: 系统内置字典类别禁止删除

    For any 字典类别，删除该类别的请求当且仅当其 is_system 为真时被拒绝（返回描述性
    错误，且类别及其字典项数据保持不变）；当 is_system 为假时删除请求应被允许。

    Validates: Requirements 1.6
    """
    await _ensure_admin(db_session)
    token = await _login(client, "dict-admin", "Admin@1234")

    # 使用 uuid 后缀保证跨样例的类别编码唯一，避免与其它样例/既有分类冲突
    suffix = uuid.uuid4().hex[:12]
    code = f"prop2-cat-{code_fragment}-{suffix}"
    category = DictCategory(code=code, name=code, is_system=is_system)
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    category_id = category.id

    for i in range(item_count):
        item = DictItem(category_id=category_id, code=f"item-{i}", label=f"选项{i}")
        db_session.add(item)
    await db_session.commit()

    items_count_before = (
        await db_session.execute(
            select(func.count())
            .select_from(DictItem)
            .where(DictItem.category_id == category_id)
        )
    ).scalar_one()
    assert items_count_before == item_count

    delete_resp = await client.delete(
        f"/api/v1/dict/categories/{category_id}",
        headers=_auth_header(token),
    )

    if is_system:
        # 系统内置类别：删除请求应被拒绝，返回描述性错误，类别及其字典项数据保持不变
        assert delete_resp.status_code == 400, delete_resp.text
        assert delete_resp.json()["detail"]

        category_check = await db_session.execute(
            select(DictCategory).where(DictCategory.id == category_id)
        )
        assert category_check.scalar_one_or_none() is not None

        items_count_after = (
            await db_session.execute(
                select(func.count())
                .select_from(DictItem)
                .where(DictItem.category_id == category_id)
            )
        ).scalar_one()
        assert items_count_after == item_count
    else:
        # 非系统类别：删除请求应被允许
        assert delete_resp.status_code == 200, delete_resp.text

        category_check = await db_session.execute(
            select(DictCategory).where(DictCategory.id == category_id)
        )
        assert category_check.scalar_one_or_none() is None


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    item_count=st.integers(min_value=0, max_value=3),
)
@pytest.mark.asyncio
async def test_property_delete_project_stage_category_always_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    item_count: int,
):
    """
    Feature: project-stage-management, Property 2: 系统内置字典类别禁止删除

    project_stage 分类的 is_system 恒为真，因此对其发起的删除请求应始终被拒绝，
    且分类及其字典项数据保持不变。

    Validates: Requirements 1.6
    """
    await _ensure_admin(db_session)
    token = await _login(client, "dict-admin", "Admin@1234")

    category_id = await _ensure_category(
        db_session, code="project_stage", is_system=True
    )

    # 清空并按需重新填充字典项数量，保证每个样例的初始状态可控
    existing_items = (
        await db_session.execute(
            select(DictItem).where(DictItem.category_id == category_id)
        )
    ).scalars().all()
    for existing_item in existing_items:
        await db_session.delete(existing_item)
    await db_session.commit()

    for i in range(item_count):
        item = DictItem(category_id=category_id, code=f"stage-item-{i}", label=f"阶段{i}")
        db_session.add(item)
    await db_session.commit()

    items_count_before = (
        await db_session.execute(
            select(func.count())
            .select_from(DictItem)
            .where(DictItem.category_id == category_id)
        )
    ).scalar_one()
    assert items_count_before == item_count

    delete_resp = await client.delete(
        f"/api/v1/dict/categories/{category_id}",
        headers=_auth_header(token),
    )

    assert delete_resp.status_code == 400, delete_resp.text
    assert delete_resp.json()["detail"]

    category_check = await db_session.execute(
        select(DictCategory).where(DictCategory.id == category_id)
    )
    assert category_check.scalar_one_or_none() is not None

    items_count_after = (
        await db_session.execute(
            select(func.count())
            .select_from(DictItem)
            .where(DictItem.category_id == category_id)
        )
    ).scalar_one()
    assert items_count_after == item_count


# Property 3 覆盖的针对 project_stage 分类/字典项的写操作类型
_PROP3_WRITE_OPERATIONS = (
    "create_item",
    "update_item",
    "enable_item",
    "disable_item",
    "reorder_item",
    "delete_item",
    "delete_category",
)


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    operation=st.sampled_from(_PROP3_WRITE_OPERATIONS),
    new_code=st.text(alphabet=_DICT_ITEM_CODE_ALPHABET, min_size=1, max_size=20),
    new_sort_order=st.integers(min_value=-100, max_value=100),
)
@pytest.mark.asyncio
async def test_property_non_admin_write_operations_on_dict_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    operation: str,
    new_code: str,
    new_sort_order: int,
):
    """
    Feature: project-stage-management, Property 3: 非管理员对字典的写操作一律被拒绝

    For any 不具备系统管理员角色的用户，及针对 project_stage 字典类别或其字典项的
    任意写操作（新增/修改/启用/禁用/排序/删除），系统 SHALL 拒绝该操作并返回权限
    不足的错误信息，且底层数据保持不变。

    Validates: Requirements 1.7
    """
    await _ensure_non_admin(db_session)
    token = await _login(client, "dict-nonadmin", "User@1234")

    category_id = await _ensure_category(
        db_session, code="project_stage", is_system=True
    )
    stable_item = await _ensure_stable_stage_item(db_session, category_id=category_id)

    # 使用相同编码新增会与既有字典项冲突（唯一性错误码同样是 400），
    # 因此为 create_item 场景生成一个不与既有字典项重复的编码，
    # 确保若权限校验被绕过，也不会因为其它 400 错误而误判为"权限被拒绝"。
    assume(new_code != stable_item.code)

    items_count_before = (
        await db_session.execute(
            select(func.count())
            .select_from(DictItem)
            .where(DictItem.category_id == category_id)
        )
    ).scalar_one()
    stable_item_label_before = stable_item.label
    stable_item_is_enabled_before = stable_item.is_enabled
    stable_item_sort_order_before = stable_item.sort_order

    if operation == "create_item":
        resp = await client.post(
            f"/api/v1/dict/categories/{category_id}/items",
            json={"code": new_code, "label": "非管理员新增选项"},
            headers=_auth_header(token),
        )
    elif operation == "update_item":
        resp = await client.patch(
            f"/api/v1/dict/items/{stable_item.id}",
            json={"label": "非管理员修改后的标签"},
            headers=_auth_header(token),
        )
    elif operation == "enable_item":
        resp = await client.patch(
            f"/api/v1/dict/items/{stable_item.id}",
            json={"is_enabled": True},
            headers=_auth_header(token),
        )
    elif operation == "disable_item":
        resp = await client.patch(
            f"/api/v1/dict/items/{stable_item.id}",
            json={"is_enabled": False},
            headers=_auth_header(token),
        )
    elif operation == "reorder_item":
        resp = await client.patch(
            f"/api/v1/dict/items/{stable_item.id}",
            json={"sort_order": new_sort_order},
            headers=_auth_header(token),
        )
    elif operation == "delete_item":
        resp = await client.delete(
            f"/api/v1/dict/items/{stable_item.id}",
            headers=_auth_header(token),
        )
    else:  # delete_category
        resp = await client.delete(
            f"/api/v1/dict/categories/{category_id}",
            headers=_auth_header(token),
        )

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"]

    # 底层数据保持不变：类别仍存在，字典项数量与稳定字典项字段均未改变
    category_check = await db_session.execute(
        select(DictCategory).where(DictCategory.id == category_id)
    )
    assert category_check.scalar_one_or_none() is not None

    items_count_after = (
        await db_session.execute(
            select(func.count())
            .select_from(DictItem)
            .where(DictItem.category_id == category_id)
        )
    ).scalar_one()
    assert items_count_after == items_count_before

    stable_item_check = await db_session.execute(
        select(DictItem).where(DictItem.id == stable_item.id)
    )
    stable_item_after = stable_item_check.scalar_one_or_none()
    assert stable_item_after is not None
    assert stable_item_after.label == stable_item_label_before
    assert stable_item_after.is_enabled == stable_item_is_enabled_before
    assert stable_item_after.sort_order == stable_item_sort_order_before

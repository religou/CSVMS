"""字典管理 API 路由."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import BusinessError
from app.api.deps import get_current_user, require_roles
from app.models.user import User, Role
from app.models.dictionary import DictCategory, DictItem
from app.schemas.dictionary import (
    DictCategoryCreate,
    DictCategoryResponse,
    DictCategoryUpdate,
    DictItemCreate,
    DictItemResponse,
    DictItemUpdate,
)

router = APIRouter(prefix="/dict", tags=["字典管理"])


@router.get("/categories", response_model=list[DictCategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取所有字典类别及其选项."""
    result = await db.execute(
        select(DictCategory)
        .options(selectinload(DictCategory.items))
        .order_by(DictCategory.code)
    )
    return list(result.scalars().unique().all())


@router.get("/categories/{category_code}/items", response_model=list[DictItemResponse])
async def list_items_by_category(
    category_code: str,
    enabled_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """按类别编码获取字典项列表."""
    result = await db.execute(
        select(DictCategory).where(DictCategory.code == category_code)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise BusinessError(f"字典类别 '{category_code}' 不存在")

    stmt = (
        select(DictItem)
        .where(DictItem.category_id == category.id)
        .order_by(DictItem.sort_order)
    )
    if enabled_only:
        stmt = stmt.where(DictItem.is_enabled == True)  # noqa: E712
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/categories", response_model=DictCategoryResponse)
async def create_category(
    data: DictCategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    """创建字典类别."""
    existing = await db.execute(
        select(DictCategory).where(DictCategory.code == data.code)
    )
    if existing.scalar_one_or_none():
        raise BusinessError("类别编码已存在")

    category = DictCategory(code=data.code, name=data.name, description=data.description)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.patch("/categories/{category_id}", response_model=DictCategoryResponse)
async def update_category(
    category_id: str,
    data: DictCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    """更新字典类别."""
    result = await db.execute(
        select(DictCategory)
        .options(selectinload(DictCategory.items))
        .where(DictCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise BusinessError("字典类别不存在")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    """删除字典类别（仅非系统类别）."""
    result = await db.execute(
        select(DictCategory).where(DictCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise BusinessError("字典类别不存在")
    if category.is_system:
        raise BusinessError("系统内置类别不可删除")

    await db.delete(category)
    await db.commit()
    return {"detail": "已删除"}


@router.post("/categories/{category_id}/items", response_model=DictItemResponse)
async def create_item(
    category_id: str,
    data: DictItemCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    """在指定类别下新增字典项."""
    result = await db.execute(
        select(DictCategory).where(DictCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise BusinessError("字典类别不存在")

    # 同类别下 code 唯一
    existing = await db.execute(
        select(DictItem).where(
            DictItem.category_id == category_id,
            DictItem.code == data.code,
        )
    )
    if existing.scalar_one_or_none():
        raise BusinessError("该类别下选项编码已存在")

    item = DictItem(category_id=category_id, **data.model_dump())
    db.add(item)

    # 自动同步：system_role 类别新增条目时自动创建对应 Role 实体
    if category.code == "system_role":
        existing_role = await db.execute(
            select(Role).where(Role.name == data.code)
        )
        if not existing_role.scalar_one_or_none():
            role = Role(
                name=data.code,
                display_name=data.label,
                description=data.description,
            )
            db.add(role)

    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/items/{item_id}", response_model=DictItemResponse)
async def update_item(
    item_id: str,
    data: DictItemUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    """更新字典项."""
    result = await db.execute(select(DictItem).where(DictItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise BusinessError("字典项不存在")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    """删除字典项."""
    result = await db.execute(select(DictItem).where(DictItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise BusinessError("字典项不存在")

    await db.delete(item)
    await db.commit()
    return {"detail": "已删除"}

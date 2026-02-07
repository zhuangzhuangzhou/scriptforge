from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.ai_configuration import AIConfiguration
from app.schemas.ai_configuration import (
    AIConfiguration as AIConfigSchema,
    AIConfigurationCreate,
    AIConfigurationUpdate
)

router = APIRouter()

@router.get("", response_model=List[AIConfigSchema])
async def list_configurations(
    category: Optional[str] = None,
    merge: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取配置列表
    - merge=True (默认): 返回生效配置（用户配置覆盖系统配置），用于 Agent 调用
    - merge=False: 返回所有可见配置（包含系统默认和用户自定义），用于管理界面
    """
    # 1. 查询系统默认配置 (user_id IS NULL)
    system_stmt = select(AIConfiguration).where(AIConfiguration.user_id == None)
    if category:
        system_stmt = system_stmt.where(AIConfiguration.category == category)

    # 2. 查询当前用户的自定义配置
    user_stmt = select(AIConfiguration).where(AIConfiguration.user_id == current_user.id)
    if category:
        user_stmt = user_stmt.where(AIConfiguration.category == category)

    system_results = await db.execute(system_stmt)
    user_results = await db.execute(user_stmt)

    system_configs = system_results.scalars().all()
    user_configs = user_results.scalars().all()

    if merge:
        # 转换为字典以便合并，Key 为配置键
        sys_dict = {c.key: c for c in system_configs}
        usr_dict = {c.key: c for c in user_configs}
        # 合并：用户配置覆盖系统配置
        merged = {**sys_dict, **usr_dict}
        return sorted(merged.values(), key=lambda x: x.key)
    else:
        # 返回原始列表
        # 确保明确转换为列表
        all_configs = list(system_configs) + list(user_configs)
        # 按 Key 排序，同 Key 的系统配置在前(user_id=None)，用户配置在后
        return sorted(all_configs, key=lambda x: (x.key, 0 if x.user_id is None else 1))

@router.get("/{key}", response_model=AIConfigSchema)
async def get_configuration(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取特定 Key 的配置 (用户自定义优先)"""
    result = await db.execute(
        select(AIConfiguration)
        .where(AIConfiguration.key == key)
        .where((AIConfiguration.user_id == current_user.id) | (AIConfiguration.user_id == None))
        .order_by(AIConfiguration.user_id.desc().nulls_last()) # 用户 ID 非空排在前面
        .limit(1)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return config

@router.post("", response_model=AIConfigSchema)
async def upsert_configuration(
    config_in: AIConfigurationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建或更新用户自己的配置"""
    # 永远只操作当前用户的配置，不允许修改系统默认配置 (user_id=None)
    result = await db.execute(
        select(AIConfiguration)
        .where(AIConfiguration.key == config_in.key)
        .where(AIConfiguration.user_id == current_user.id)
    )
    existing_config = result.scalar_one_or_none()

    if existing_config:
        # 更新现有用户配置
        existing_config.value = config_in.value
        existing_config.category = config_in.category
        existing_config.is_active = config_in.is_active
        existing_config.description = config_in.description
        db.add(existing_config)
    else:
        # 创建新的用户配置
        new_config = AIConfiguration(
            key=config_in.key,
            value=config_in.value,
            category=config_in.category,
            is_active=config_in.is_active,
            description=config_in.description,
            user_id=current_user.id
        )
        db.add(new_config)

    await db.commit()
    # 重新查询以确保获取完整对象
    result = await db.execute(
        select(AIConfiguration)
        .where(AIConfiguration.key == config_in.key)
        .where(AIConfiguration.user_id == current_user.id)
    )
    return result.scalar_one()

@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除特定配置 (仅限删除用户自己的配置)"""
    # 只能查找并删除归属于当前用户的配置
    result = await db.execute(
        select(AIConfiguration)
        .where(AIConfiguration.key == key)
        .where(AIConfiguration.user_id == current_user.id)
    )
    config = result.scalar_one_or_none()

    if not config:
        # 如果用户想删除系统配置，或者配置不存在，都返回 404 或 403
        # 这里为了安全，统称为"未找到可删除的配置"
        raise HTTPException(status_code=404, detail="未找到可删除的用户配置 (无法删除系统默认配置)")

    await db.delete(config)
    await db.commit()
    return None

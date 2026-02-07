from typing import List, Any
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有配置列表"""
    result = await db.execute(select(AIConfiguration).order_by(AIConfiguration.key))
    return result.scalars().all()

@router.get("/{key}", response_model=AIConfigSchema)
async def get_configuration(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取特定 Key 的配置"""
    result = await db.execute(select(AIConfiguration).where(AIConfiguration.key == key))
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
    """创建或更新配置 (根据 Key)"""
    # 检查是否已存在
    result = await db.execute(select(AIConfiguration).where(AIConfiguration.key == config_in.key))
    existing_config = result.scalar_one_or_none()

    if existing_config:
        # 更新
        existing_config.value = config_in.value
        existing_config.description = config_in.description
        db.add(existing_config)
        await db.commit()
        await db.refresh(existing_config)
        return existing_config
    else:
        # 创建
        new_config = AIConfiguration(
            key=config_in.key,
            value=config_in.value,
            description=config_in.description
        )
        db.add(new_config)
        await db.commit()
        await db.refresh(new_config)
        return new_config

@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除特定配置"""
    result = await db.execute(select(AIConfiguration).where(AIConfiguration.key == key))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    await db.delete(config)
    await db.commit()
    return None

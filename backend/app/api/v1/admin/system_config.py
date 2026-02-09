"""系统配置管理 API"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.system_model_config import SystemModelConfig
from app.schemas.system_config import (
    SystemConfigUpdate,
    SystemConfigResponse
)
from app.api.v1.admin import check_admin

router = APIRouter()


@router.get("", response_model=List[SystemConfigResponse])
async def get_system_configs(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """获取所有系统配置"""
    result = await db.execute(
        select(SystemModelConfig).order_by(SystemModelConfig.config_key)
    )
    configs = result.scalars().all()

    return [
        {
            "id": str(config.id),
            "config_key": config.config_key,
            "config_value": config.config_value,
            "value_type": config.value_type,
            "description": config.description,
            "is_editable": config.is_editable,
            "created_at": config.created_at,
            "updated_at": config.updated_at
        }
        for config in configs
    ]


@router.get("/{config_key}", response_model=SystemConfigResponse)
async def get_system_config(
    config_key: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """获取单个系统配置"""
    result = await db.execute(
        select(SystemModelConfig).where(SystemModelConfig.config_key == config_key)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="配置项不存在")

    return {
        "id": str(config.id),
        "config_key": config.config_key,
        "config_value": config.config_value,
        "value_type": config.value_type,
        "description": config.description,
        "is_editable": config.is_editable,
        "created_at": config.created_at,
        "updated_at": config.updated_at
    }


@router.put("/{config_key}", response_model=SystemConfigResponse)
async def update_system_config(
    config_key: str,
    config_data: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """更新系统配置"""
    # 查询配置项
    result = await db.execute(
        select(SystemModelConfig).where(SystemModelConfig.config_key == config_key)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="配置项不存在")

    # 检查是否可编辑
    if not config.is_editable:
        raise HTTPException(status_code=400, detail="该配置项不可编辑")

    # 更新配置值
    config.config_value = config_data.config_value
    await db.commit()
    await db.refresh(config)

    return {
        "id": str(config.id),
        "config_key": config.config_key,
        "config_value": config.config_value,
        "value_type": config.value_type,
        "description": config.description,
        "is_editable": config.is_editable,
        "created_at": config.created_at,
        "updated_at": config.updated_at
    }

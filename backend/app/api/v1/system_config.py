"""系统配置 API

端点：
- GET /system/configs - 获取所有配置
- GET /system/configs/credits - 获取积分相关配置
- PUT /system/configs - 批量更新配置（管理员）
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Dict, Optional, Any
import json

from app.core.database import get_db
from app.api.v1.auth import get_current_user, require_admin
from app.models.user import User
from app.models.system_config import SystemConfig

router = APIRouter()


# 默认配置
DEFAULT_CONFIGS = {
    "credits_breakdown": {"value": "100", "description": "剧情拆解基础费（积分）"},
    "credits_script": {"value": "50", "description": "剧本生成基础费（积分）"},
    "credits_qa": {"value": "30", "description": "质检校验基础费（积分）"},
    "credits_retry": {"value": "50", "description": "任务重试基础费（积分）"},
    "token_billing_enabled": {"value": "false", "description": "是否启用 Token 计费"},
    "token_input_per_1k": {"value": "1", "description": "输入 Token 默认价格（积分/1K）"},
    "token_output_per_1k": {"value": "2", "description": "输出 Token 默认价格（积分/1K）"},
}


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    configs: Dict[str, str]


class CreditsConfigResponse(BaseModel):
    """积分配置响应"""
    base: Dict[str, int]
    token: Dict[str, Any]


async def get_config_value(db: AsyncSession, key: str) -> Optional[str]:
    """获取单个配置值"""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == key)
    )
    config = result.scalar_one_or_none()
    if config:
        return config.value
    return DEFAULT_CONFIGS.get(key, {}).get("value")


async def get_all_configs(db: AsyncSession) -> Dict[str, str]:
    """获取所有配置"""
    result = await db.execute(select(SystemConfig))
    configs = result.scalars().all()

    # 合并默认配置和数据库配置
    all_configs = {k: v["value"] for k, v in DEFAULT_CONFIGS.items()}
    for config in configs:
        all_configs[config.key] = config.value

    return all_configs


@router.get("/configs")
async def list_configs(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取所有系统配置（管理员）"""
    result = await db.execute(select(SystemConfig))
    db_configs = result.scalars().all()

    # 构建响应，包含默认值和描述
    configs = []
    db_config_map = {c.key: c for c in db_configs}

    for key, default in DEFAULT_CONFIGS.items():
        db_config = db_config_map.get(key)
        configs.append({
            "key": key,
            "value": db_config.value if db_config else default["value"],
            "description": default["description"],
            "is_default": db_config is None
        })

    return {"configs": configs}


@router.get("/configs/credits")
async def get_credits_config(
    db: AsyncSession = Depends(get_db)
):
    """获取积分配置（公开）"""
    all_configs = await get_all_configs(db)

    return {
        "base": {
            "breakdown": int(all_configs.get("credits_breakdown", "100")),
            "script": int(all_configs.get("credits_script", "50")),
            "qa": int(all_configs.get("credits_qa", "30")),
            "retry": int(all_configs.get("credits_retry", "50")),
        },
        "token": {
            "enabled": all_configs.get("token_billing_enabled", "false").lower() == "true",
            "input_per_1k": int(all_configs.get("token_input_per_1k", "1")),
            "output_per_1k": int(all_configs.get("token_output_per_1k", "2")),
        }
    }


@router.put("/configs")
async def update_configs(
    request: ConfigUpdateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """批量更新配置（管理员）"""
    updated = []

    for key, value in request.configs.items():
        if key not in DEFAULT_CONFIGS:
            continue

        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        config = result.scalar_one_or_none()

        if config:
            config.value = value
        else:
            config = SystemConfig(
                key=key,
                value=value,
                description=DEFAULT_CONFIGS[key]["description"]
            )
            db.add(config)

        updated.append(key)

    await db.commit()

    return {"message": f"已更新 {len(updated)} 项配置", "updated": updated}

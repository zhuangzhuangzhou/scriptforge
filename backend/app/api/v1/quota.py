"""用户配额管理 API

端点：
- GET /quota - 获取用户配额摘要
- GET /quota/tiers - 获取所有等级配置
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.quota import QuotaService, TIER_CONFIGS, get_tier_config
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()


class QuotaInfo(BaseModel):
    """配额信息"""
    allowed: bool
    remaining: int
    limit: Optional[int] = None
    used: Optional[int] = None


class PricingInfo(BaseModel):
    """积分定价"""
    breakdown: int = 100
    script: int = 50
    qa: int = 30
    retry: int = 50


class QuotaSummary(BaseModel):
    """配额摘要（纯积分制）"""
    tier: str
    tier_display: str
    credits: int
    monthly_credits: int = 0
    monthly_credits_granted: int = 0
    projects: QuotaInfo
    can_use_custom_api: bool
    reset_at: Optional[str] = None
    pricing: Optional[PricingInfo] = None


class TierInfo(BaseModel):
    """等级信息"""
    name: str
    display_name: str
    max_projects: int
    monthly_credits: int
    can_use_custom_api: bool
    price_monthly: int


@router.get("/quota", response_model=QuotaSummary)
async def get_user_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户配额摘要"""
    service = QuotaService(db)
    summary = await service.get_user_quota_summary(current_user)
    return summary


@router.get("/quota/tiers")
async def get_all_tiers():
    """获取所有等级配置"""
    tiers = []
    for tier_name, config in TIER_CONFIGS.items():
        tiers.append({
            "name": config.name,
            "display_name": config.display_name,
            "max_projects": config.max_projects,
            "monthly_credits": config.monthly_credits,
            "can_use_custom_api": config.can_use_custom_api,
            "price_monthly": config.price_monthly
        })
    return {"tiers": tiers}


@router.get("/quota/tier/{tier_name}")
async def get_tier_info(tier_name: str):
    """获取指定等级配置"""
    config = get_tier_config(tier_name)
    return {
        "name": config.name,
        "display_name": config.display_name,
        "max_projects": config.max_projects,
        "monthly_credits": config.monthly_credits,
        "can_use_custom_api": config.can_use_custom_api,
        "price_monthly": config.price_monthly
    }

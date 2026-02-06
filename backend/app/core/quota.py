"""用户等级和配额管理服务

等级配置：
- free: 免费版 - 1个项目，3集/月
- creator: 创作者版 - 5个项目，30集/月
- studio: 工作室版 - 20个项目，150集/月
- enterprise: 企业版 - 无限项目，无限产出
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func


@dataclass
class TierConfig:
    """等级配置"""
    name: str
    display_name: str
    max_projects: int          # 最大项目数，-1 表示无限
    monthly_episodes: int      # 每月剧集配额，-1 表示无限
    can_use_custom_api: bool   # 是否可使用自定义 API Key
    price_monthly: int         # 月费（分）


# 等级配置表
TIER_CONFIGS = {
    "free": TierConfig(
        name="free",
        display_name="免费版",
        max_projects=1,
        monthly_episodes=3,
        can_use_custom_api=False,
        price_monthly=0
    ),
    "creator": TierConfig(
        name="creator",
        display_name="创作者版",
        max_projects=5,
        monthly_episodes=30,
        can_use_custom_api=False,
        price_monthly=4900  # ¥49
    ),
    "studio": TierConfig(
        name="studio",
        display_name="工作室版",
        max_projects=20,
        monthly_episodes=150,
        can_use_custom_api=False,
        price_monthly=19900  # ¥199
    ),
    "enterprise": TierConfig(
        name="enterprise",
        display_name="企业版",
        max_projects=-1,
        monthly_episodes=-1,
        can_use_custom_api=True,
        price_monthly=99900  # ¥999
    ),
}


def get_tier_config(tier: str) -> TierConfig:
    """获取等级配置（大小写不敏感）"""
    if not tier:
        return TIER_CONFIGS["free"]
    # 统一转为小写进行匹配
    normalized_tier = tier.lower()
    config = TIER_CONFIGS.get(normalized_tier)
    if config is None:
        return TIER_CONFIGS["free"]
    return config


class QuotaService:
    """配额检查服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_project_quota(self, user) -> dict:
        """检查项目配额"""
        from app.models.project import Project

        config = get_tier_config(user.tier)

        # 无限配额
        if config.max_projects == -1:
            return {"allowed": True, "remaining": -1}

        # 统计用户项目数
        result = await self.db.execute(
            select(func.count(Project.id)).where(Project.user_id == user.id)
        )
        current_count = result.scalar() or 0

        remaining = config.max_projects - current_count
        return {
            "allowed": remaining > 0,
            "remaining": remaining,
            "limit": config.max_projects,
            "used": current_count
        }

    async def check_episode_quota(self, user) -> dict:
        """检查剧集配额"""
        config = get_tier_config(user.tier)

        # 无限配额
        if config.monthly_episodes == -1:
            return {"allowed": True, "remaining": -1}

        # 检查是否需要重置月度配额
        await self._maybe_reset_monthly_quota(user)

        remaining = config.monthly_episodes - user.monthly_episodes_used
        return {
            "allowed": remaining > 0,
            "remaining": remaining,
            "limit": config.monthly_episodes,
            "used": user.monthly_episodes_used
        }

    async def consume_episode_quota(self, user, count: int = 1) -> bool:
        """消耗剧集配额，返回是否成功"""
        quota = await self.check_episode_quota(user)

        if not quota["allowed"]:
            return False

        if quota["remaining"] != -1 and quota["remaining"] < count:
            return False

        # 无限配额不需要扣减
        if quota["remaining"] != -1:
            user.monthly_episodes_used += count

        return True

    async def refund_episode_quota(self, user, count: int = 1) -> None:
        """回滚剧集配额（失败回滚或撤销预占）"""
        if count <= 0:
            return

        # 无限配额不需要回滚
        config = get_tier_config(user.tier)
        if config.monthly_episodes == -1:
            return

        # 确保不会减成负数
        user.monthly_episodes_used = max(user.monthly_episodes_used - count, 0)

    async def _maybe_reset_monthly_quota(self, user):
        """检查并重置月度配额"""
        now = datetime.now(timezone.utc)

        if user.monthly_reset_at is None:
            # 首次使用，设置下月1号重置
            user.monthly_reset_at = self._get_next_month_start(now)
            user.monthly_episodes_used = 0
        elif now >= user.monthly_reset_at:
            # 已过重置时间，重置配额
            user.monthly_episodes_used = 0
            user.monthly_reset_at = self._get_next_month_start(now)

    @staticmethod
    def _get_next_month_start(dt: datetime) -> datetime:
        """获取下月1号零点"""
        if dt.month == 12:
            return datetime(dt.year + 1, 1, 1, tzinfo=timezone.utc)
        return datetime(dt.year, dt.month + 1, 1, tzinfo=timezone.utc)

    async def get_user_quota_summary(self, user) -> dict:
        """获取用户配额摘要"""
        config = get_tier_config(user.tier)
        project_quota = await self.check_project_quota(user)
        episode_quota = await self.check_episode_quota(user)

        return {
            "tier": user.tier,
            "tier_display": config.display_name,
            "credits": user.credits,
            "projects": project_quota,
            "episodes": episode_quota,
            "can_use_custom_api": config.can_use_custom_api,
            "reset_at": user.monthly_reset_at.isoformat() if user.monthly_reset_at else None
        }

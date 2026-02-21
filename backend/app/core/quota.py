"""用户等级和配额管理服务

纯积分制：
- 取消配额概念，统一使用积分
- 等级权益：每月自动赠送积分
- 积分定价：从数据库读取，默认剧情拆解 100 积分，剧本生成 50 积分，质检 30 积分
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, func
import logging

logger = logging.getLogger(__name__)


# 默认积分消费定价（可被数据库配置覆盖）
DEFAULT_CREDITS_PRICING = {
    "breakdown": 100,      # 剧情拆解
    "script": 50,          # 剧本生成
    "qa": 30,              # 质检校验
    "retry": 50,           # 重试（半价）
}


async def get_credits_pricing(db: AsyncSession) -> dict:
    """从数据库获取积分定价配置"""
    from app.core.credits import get_credits_config
    config = await get_credits_config(db)
    return config["base"]


@dataclass
class TierConfig:
    """等级配置"""
    name: str
    display_name: str
    max_projects: int          # 最大项目数，-1 表示无限
    monthly_credits: int       # 每月赠送积分
    can_use_custom_api: bool   # 是否可使用自定义 API Key
    price_monthly: int         # 月费（分）


# 等级配置表
TIER_CONFIGS = {
    "free": TierConfig(
        name="free",
        display_name="免费版",
        max_projects=1,
        monthly_credits=300,
        can_use_custom_api=False,
        price_monthly=0
    ),
    "creator": TierConfig(
        name="creator",
        display_name="创作者版",
        max_projects=5,
        monthly_credits=3000,
        can_use_custom_api=False,
        price_monthly=4900  # ¥49
    ),
    "studio": TierConfig(
        name="studio",
        display_name="工作室版",
        max_projects=20,
        monthly_credits=15000,
        can_use_custom_api=False,
        price_monthly=19900  # ¥199
    ),
    "enterprise": TierConfig(
        name="enterprise",
        display_name="企业版",
        max_projects=-1,
        monthly_credits=100000,
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
    """配额检查服务（纯积分制）

    所有配额检查已转换为积分检查。
    """

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

    async def check_and_grant_monthly_credits(self, user) -> int:
        """检查并发放月度积分

        Returns:
            int: 本次发放的积分数量，0 表示无需发放
        """
        config = get_tier_config(user.tier)
        now = datetime.now(timezone.utc)

        # 检查是否需要重置（每月1号或首次）
        if self._should_reset_monthly(user, now):
            granted = config.monthly_credits
            user.credits += granted
            user.monthly_credits_granted = granted
            user.credits_reset_at = now
            return granted
        return 0

    def _should_reset_monthly(self, user, now: datetime) -> bool:
        """判断是否需要重置月度积分"""
        if user.credits_reset_at is None:
            # 首次使用
            return True

        # 检查是否跨月
        reset_at = user.credits_reset_at
        if reset_at.year < now.year:
            return True
        if reset_at.year == now.year and reset_at.month < now.month:
            return True
        return False

    async def check_credits(self, user, task_type: str) -> dict:
        """检查积分是否足够

        Args:
            user: 用户对象
            task_type: 任务类型（breakdown/script/qa/retry）

        Returns:
            dict: {allowed, cost, balance, shortfall}
        """
        # 先尝试发放月度积分
        await self.check_and_grant_monthly_credits(user)

        # 从数据库读取定价配置
        pricing = await get_credits_pricing(self.db)
        cost = pricing.get(task_type, DEFAULT_CREDITS_PRICING.get(task_type, 0))

        return {
            "allowed": user.credits >= cost,
            "cost": cost,
            "balance": user.credits,
            "shortfall": max(0, cost - user.credits)
        }

    async def consume_credits(self, user, task_type: str, description: str = None) -> bool:
        """消耗积分

        Args:
            user: 用户对象
            task_type: 任务类型
            description: 消费描述

        Returns:
            bool: 是否成功
        """
        # 从数据库读取定价配置
        pricing = await get_credits_pricing(self.db)
        cost = pricing.get(task_type, DEFAULT_CREDITS_PRICING.get(task_type, 0))

        if user.credits < cost:
            return False

        user.credits -= cost

        # 记录账单
        from app.models.billing import BillingRecord
        from uuid import UUID

        record = BillingRecord(
            user_id=user.id if not isinstance(user.id, str) else UUID(user.id),
            type="consume",
            credits=-cost,
            balance_after=user.credits,
            description=description or f"{task_type} 任务消费",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(record)
        return True

    async def check_episode_quota(self, user) -> dict:
        """检查剧集配额（兼容旧接口，转为积分检查）"""
        return await self.check_credits(user, "breakdown")

    async def consume_episode_quota(self, user, count: int = 1) -> bool:
        """消耗剧集配额（兼容旧接口，转为积分消费）"""
        for _ in range(count):
            if not await self.consume_credits(user, "breakdown", "剧情拆解"):
                return False
        return True

    async def refund_episode_quota(self, user, count: int = 1) -> None:
        """回滚剧集配额（兼容旧接口，转为积分返还）"""
        if count <= 0:
            return

        # 从数据库读取定价配置
        pricing = await get_credits_pricing(self.db)
        refund_amount = pricing.get("breakdown", DEFAULT_CREDITS_PRICING.get("breakdown", 100)) * count

        user.credits += refund_amount

        # 记录账单
        from app.models.billing import BillingRecord
        from uuid import UUID

        record = BillingRecord(
            user_id=user.id if not isinstance(user.id, str) else UUID(user.id),
            type="refund",
            credits=refund_amount,
            balance_after=user.credits,
            description=f"任务失败返还积分 x{count}",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(record)

    async def get_user_quota_summary(self, user) -> dict:
        """获取用户配额摘要（纯积分制）"""
        config = get_tier_config(user.tier)
        project_quota = await self.check_project_quota(user)

        # 先尝试发放月度积分
        await self.check_and_grant_monthly_credits(user)

        # 从数据库读取定价配置
        pricing = await get_credits_pricing(self.db)

        return {
            "tier": user.tier,
            "tier_display": config.display_name,
            "credits": user.credits,
            "monthly_credits": config.monthly_credits,
            "monthly_credits_granted": user.monthly_credits_granted or 0,
            "projects": project_quota,
            "can_use_custom_api": config.can_use_custom_api,
            "reset_at": user.credits_reset_at.isoformat() if user.credits_reset_at else None,
            "pricing": pricing
        }


def refund_episode_quota_sync(db: Session, user_id: str, amount: int = 1, auto_commit: bool = True) -> None:
    """同步版本：返还积分（纯积分制）

    用于 Celery worker 中的积分回滚操作。当任务失败时，需要将预扣的积分返还给用户。

    Args:
        db: 同步数据库会话
        user_id: 用户ID（UUID字符串）
        amount: 返还任务数量，默认为1
        auto_commit: 是否自动提交事务，默认为 True。设为 False 时由调用方统一管理事务。

    Raises:
        无异常抛出。积分回滚失败不应阻止错误信息的记录。
    """
    from app.models.user import User
    from app.models.billing import BillingRecord
    from uuid import UUID

    if amount <= 0:
        logger.warning(f"积分回滚数量无效: user_id={user_id}, amount={amount}")
        return

    try:
        # 查询用户
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            logger.error(f"积分回滚失败: 用户不存在 user_id={user_id}")
            return

        # 计算返还积分（同步函数使用默认值，无法异步查询数据库）
        refund_credits = DEFAULT_CREDITS_PRICING.get("breakdown", 100) * amount
        old_balance = user.credits
        user.credits += refund_credits
        new_balance = user.credits

        # 记录账单
        record = BillingRecord(
            user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
            type="refund",
            credits=refund_credits,
            balance_after=new_balance,
            description=f"任务失败返还积分 x{amount}",
            created_at=datetime.now(timezone.utc)
        )
        db.add(record)

        # 根据参数决定是否提交事务
        if auto_commit:
            db.commit()

        logger.info(
            f"积分回滚成功: user_id={user_id}, amount={amount}, "
            f"refund_credits={refund_credits}, old_balance={old_balance}, new_balance={new_balance}"
        )

    except Exception as e:
        # 积分回滚失败不应阻止错误传播
        logger.error(f"积分回滚失败: user_id={user_id}, amount={amount}, error={str(e)}")
        if auto_commit:
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"积分回滚事务回滚失败: {str(rollback_error)}")

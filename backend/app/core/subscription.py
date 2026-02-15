from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.billing import BillingRecord, Subscription
from app.core.quota import get_tier_config


# 积分兑换比例：1 元 = 100 积分
YUAN_TO_CREDITS = 100


class SubscriptionService:
    """订阅管理服务（积分制）

    使用积分购买订阅。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_subscription(self, user_id: str, tier: str, months: int = 1) -> dict:
        """创建订阅（积分制）

        使用积分购买订阅。

        Args:
            user_id: 用户ID
            tier: 订阅等级 (free, creator, studio, enterprise)
            months: 订阅月数

        Returns:
            创建的订阅对象信息
        """
        if months < 1:
            raise ValueError("订阅时长必须至少为1个月")

        # 获取等级配置
        tier_config = get_tier_config(tier)
        if tier_config.name == "free":
            raise ValueError("无法手动订阅免费版")

        # 获取用户
        user = await self._get_user(user_id)
        if not user:
            raise ValueError("用户不存在")

        # 计算费用（转换为积分：1元 = 100积分）
        total_amount_yuan = tier_config.price_monthly / 100.0  # 转为元
        total_credits = int(total_amount_yuan * YUAN_TO_CREDITS)  # 转为积分

        # 检查积分余额
        if user.credits < total_credits:
            raise ValueError(f"积分不足，需要 {total_credits} 积分，当前余额 {user.credits} 积分")

        # 获取当前有效的同等级订阅以确定开始时间
        current_sub = await self._get_latest_active_subscription(user_id, tier)

        now = datetime.now(timezone.utc)

        if current_sub and current_sub.expires_at > now:
            started_at = current_sub.expires_at
        else:
            started_at = now

        # 计算过期时间
        expires_at = started_at + timedelta(days=30 * months)

        # 扣除积分
        user.credits -= total_credits

        # 更新用户等级
        user.tier = tier

        # 1. 创建订阅记录
        subscription = Subscription(
            user_id=user.id,
            tier=tier,
            status="active",
            amount=tier_config.price_monthly * months,  # 金额（分）
            started_at=started_at,
            expires_at=expires_at,
            created_at=now
        )
        self.db.add(subscription)

        # 2. 创建账单记录
        billing_record = BillingRecord(
            user_id=user.id,
            type="subscription",
            amount=-tier_config.price_monthly * months,  # 金额变动（分）
            credits=-total_credits,  # 积分变动
            balance_after=user.credits,  # 变动后积分余额
            description=f"订阅 {tier_config.display_name} {months} 个月（消耗 {total_credits} 积分）",
            created_at=now
        )
        self.db.add(billing_record)

        await self.db.flush()

        return {
            "id": str(subscription.id),
            "tier": subscription.tier,
            "started_at": subscription.started_at.isoformat(),
            "expires_at": subscription.expires_at.isoformat(),
            "status": subscription.status,
            "amount": subscription.amount,  # 金额（分）
            "credits_used": total_credits,  # 消耗积分
            "created_at": subscription.created_at.isoformat()
        }

    async def check_and_sync_tier(self, user: User) -> dict:
        """检查并同步用户等级

        检查用户当前订阅是否过期。
        如果过期且等级非 free，将其回退到 free。
        """
        # 获取当前时间
        now = datetime.now(timezone.utc)

        # 获取用户当前的活跃订阅
        active_sub = await self.get_active_subscription(str(user.id))

        current_tier = user.tier
        new_tier = current_tier

        if active_sub:
            # 有活跃订阅，确保用户等级与订阅一致
            if current_tier != active_sub.tier:
                new_tier = active_sub.tier
        else:
            # 无活跃订阅（或已过期），如果当前不是 free，降级为 free
            if current_tier != "free":
                new_tier = "free"

        if new_tier != current_tier:
            user.tier = new_tier

        return {
            "previous_tier": current_tier,
            "current_tier": new_tier,
            "synced": new_tier != current_tier
        }

    async def get_active_subscription(self, user_id: str) -> Optional[Subscription]:
        """获取用户当前处于 active 状态且未过期的订阅"""
        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        now = datetime.now(timezone.utc)

        # 查询条件：用户ID + 状态active + 开始时间<=当前 + 过期时间>当前
        stmt = (
            select(Subscription)
            .where(
                and_(
                    Subscription.user_id == uid,
                    Subscription.status == "active",
                    Subscription.started_at <= now,
                    Subscription.expires_at > now
                )
            )
            .order_by(desc(Subscription.expires_at))
            .limit(1)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_user(self, user_id: str) -> Optional[User]:
        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        result = await self.db.execute(select(User).where(User.id == uid))
        return result.scalar_one_or_none()

    async def _get_latest_active_subscription(self, user_id: str, tier: str) -> Optional[Subscription]:
        """获取用户指定等级的最新活跃订阅（包括未来的）"""
        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        now = datetime.now(timezone.utc)

        # 查找该等级的 active 订阅，且过期时间 > now
        stmt = (
            select(Subscription)
            .where(
                and_(
                    Subscription.user_id == uid,
                    Subscription.tier == tier,
                    Subscription.status == "active",
                    Subscription.expires_at > now
                )
            )
            .order_by(desc(Subscription.expires_at))
            .limit(1)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_subscriptions(self, user_id: str, limit: int = 20, offset: int = 0) -> list[Subscription]:
        """获取用户订阅历史记录"""
        uid = UUID(user_id) if isinstance(user_id, str) else user_id

        stmt = (
            select(Subscription)
            .where(Subscription.user_id == uid)
            .order_by(desc(Subscription.created_at))
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

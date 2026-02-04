from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.billing import BillingRecord, Subscription
from app.core.quota import get_tier_config


class SubscriptionService:
    """订阅管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_subscription(self, user_id: str, tier: str, months: int = 1) -> dict:
        """创建订阅

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

        # 计算费用 (分)
        total_amount = tier_config.price_monthly * months
        total_amount_yuan = total_amount / 100.0

        # 检查余额 (这里假设是使用余额支付，如果是外部支付回调，逻辑可能不同，但根据题目要求记录BillingRecord，推测涉及余额变动)
        # 注意：如果设计为外部支付直接调用，这里可能需要调整。
        # 但既然是在 core service 层，通常处理业务逻辑。如果是外部支付，通常会先充值到余额再消费，或者有专门的 callback 处理。
        # 按照题目要求 "Record a BillingRecord"，我们假设这是扣费订阅。
        if user.balance < total_amount_yuan:
            raise ValueError(f"余额不足，需要 {total_amount_yuan} 元，当前余额 {user.balance} 元")

        # 获取当前有效的同等级订阅以确定开始时间
        # 如果用户已有同等级订阅且未过期，则续期
        current_sub = await self._get_latest_active_subscription(user_id, tier)

        now = datetime.now(timezone.utc)

        if current_sub and current_sub.expires_at > now:
            started_at = current_sub.expires_at
        else:
            started_at = now

        # 计算过期时间
        # 简单按30天/月计算，或者使用库处理日期
        # 这里为了准确性，建议使用 relativedelta，但为了减少依赖，使用 timedelta(days=30 * months) 也可以接受，
        # 或者简单的月份加法逻辑。
        # 考虑到 Python datetime 处理月份比较麻烦，这里使用简单的 30天/月 标准，或者循环加月。
        # 实际上商业系统通常按自然月或30天。这里采用 timedelta(days=30 * months) 简化实现。
        expires_at = started_at + timedelta(days=30 * months)

        # 扣除余额
        user.balance = float(user.balance) - total_amount_yuan

        # 更新用户等级
        # 注意：如果是续期（started_at > now），且用户当前等级低于新等级，是否立即生效？
        # 通常：升级立即生效（并处理旧订阅剩余价值），续期同级保持不变。
        # 题目要求简单："Update User.tier to new tier"。
        # 我们假设用户购买即生效（如果是升级），或者是同级续期。
        # 如果是降级（购买了低级订阅），通常等待当前高级订阅过期。
        # 但为了符合 "Update User.tier" 的指令，强制更新。
        user.tier = tier

        # 1. 创建订阅记录
        subscription = Subscription(
            user_id=user.id,
            tier=tier,
            status="active",
            amount=total_amount,
            started_at=started_at,
            expires_at=expires_at,
            created_at=now
        )
        self.db.add(subscription)

        # 2. 创建账单记录
        billing_record = BillingRecord(
            user_id=user.id,
            type="subscription",
            amount=-total_amount,  # 支出为负
            credits=0,
            balance_after=int(user.balance * 100), # 记录分为单位的余额可能不准确，因为balance是Decimal元。BillingRecord定义balance_after是Integer?
            # 检查 models/billing.py: balance_after = Column(Integer)
            # 这暗示 BillingRecord 可能期望 balance_after 也是分？或者 credits 后的积分余额？
            # 检查 credits.py: balance_after = user.credits (积分).
            # BillingRecord 复用了 balance_after 字段。
            # 如果是资金变动，这里存什么？
            # BillingRecord 定义： credits = Column(Integer, default=0) # 积分变动
            # balance_after = Column(Integer) # 变动后余额
            # 在 CreditsService 中，balance_after 存的是积分余额。
            # 这里是资金变动。如果复用该表，balance_after 可能产生歧义。
            # 但 BillingRecord 也有 `amount` (金额)。
            # 让我们看 credits.py 的 consume_credits: record.credits = -amount. record.balance_after = user.credits.
            # 也就是说 balance_after 似乎是指积分余额？
            # 如果是订阅消费，amount 变动了，但 credits 没变（除非送积分）。
            # 我们保持 balance_after 为积分余额以保持一致性。
            description=f"订阅 {tier_config.display_name} {months} 个月",
            created_at=now
        )
        # 修正：balance_after 应该是积分余额，因为该字段主要用于积分流水？
        # 或者如果 BillingRecord 既记钱也记分，那 balance_after 到底指哪个？
        # 通常设计会有 amount_balance_after 和 credits_balance_after。
        # 既然只有一个，且 CreditsService 用它存积分余额。那我也存积分余额。
        billing_record.balance_after = user.credits

        self.db.add(billing_record)

        await self.db.flush()

        return {
            "id": str(subscription.id),
            "tier": subscription.tier,
            "started_at": subscription.started_at.isoformat(),
            "expires_at": subscription.expires_at.isoformat(),
            "status": subscription.status,
            "amount": subscription.amount,
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
            # 不需要 flush，调用者可能会 commit，或者在这里 flush 也可以
            # 为了确保变更生效，这里不执行 commit，由上层控制事务

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
        # 按过期时间倒序，取最晚过期的那个（处理重叠情况）
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

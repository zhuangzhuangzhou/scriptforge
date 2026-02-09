"""积分服务

提供积分的消耗、充值、查询等功能。

Token 计费常量：
- CREDITS_PER_1K_TOKENS: 每1000 token消耗1积分（默认值，可被数据库配置覆盖）
- BREAKDOWN_BASE_CREDITS: 剧情拆解基础消耗10积分
- SCRIPT_BASE_CREDITS: 剧本生成基础消耗5积分
"""
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from uuid import UUID
from decimal import Decimal

from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.billing import BillingRecord
from app.models.ai_model import AIModel
from app.models.ai_model_pricing import AIModelPricing


# 积分消耗标准
CREDITS_PER_1K_TOKENS = 1  # 每1000 token消耗1积分
BREAKDOWN_BASE_CREDITS = 10  # 剧情拆解基础消耗
SCRIPT_BASE_CREDITS = 5  # 剧本生成基础消耗


def calculate_token_credits(token_count: int) -> int:
    """根据 token 数量计算积分消耗

    Args:
        token_count: token 数量

    Returns:
        需要消耗的积分数
    """
    return (token_count + 999) // 1000 * CREDITS_PER_1K_TOKENS


class CreditsService:
    """积分服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def consume_credits(
        self,
        user_id: str,
        amount: int,
        description: str,
        reference_id: Optional[str] = None
    ) -> dict:
        """消耗积分

        Args:
            user_id: 用户ID
            amount: 消耗积分数量（正数）
            description: 消费描述
            reference_id: 关联ID（如任务ID）

        Returns:
            {success: bool, balance: int, message: str}
        """
        if amount <= 0:
            return {
                "success": False,
                "balance": 0,
                "message": "消耗积分数量必须大于0"
            }

        # 获取用户
        user = await self._get_user(user_id)
        if not user:
            return {
                "success": False,
                "balance": 0,
                "message": "用户不存在"
            }

        # 检查余额是否足够
        if user.credits < amount:
            return {
                "success": False,
                "balance": user.credits,
                "message": f"积分不足，当前余额: {user.credits}，需要: {amount}"
            }

        # 扣减积分
        user.credits -= amount
        balance_after = user.credits

        # 创建账单记录
        record = BillingRecord(
            user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
            type="consume",
            credits=-amount,  # 消费为负数
            balance_after=balance_after,
            description=description,
            reference_id=reference_id,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(record)

        return {
            "success": True,
            "balance": balance_after,
            "message": "积分消耗成功"
        }

    async def add_credits(
        self,
        user_id: str,
        amount: int,
        description: str,
        reference_id: Optional[str] = None
    ) -> dict:
        """充值积分

        Args:
            user_id: 用户ID
            amount: 充值积分数量（正数）
            description: 充值描述
            reference_id: 关联ID（如订单号）

        Returns:
            {success: bool, balance: int, message: str}
        """
        if amount <= 0:
            return {
                "success": False,
                "balance": 0,
                "message": "充值积分数量必须大于0"
            }

        # 获取用户
        user = await self._get_user(user_id)
        if not user:
            return {
                "success": False,
                "balance": 0,
                "message": "用户不存在"
            }

        # 增加积分
        user.credits += amount
        balance_after = user.credits

        # 创建账单记录
        record = BillingRecord(
            user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
            type="recharge",
            credits=amount,  # 充值为正数
            balance_after=balance_after,
            description=description,
            reference_id=reference_id,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(record)

        return {
            "success": True,
            "balance": balance_after,
            "message": "积分充值成功"
        }

    async def get_balance(self, user_id: str) -> int:
        """查询余额

        Args:
            user_id: 用户ID

        Returns:
            积分余额，用户不存在返回0
        """
        user = await self._get_user(user_id)
        if not user:
            return 0
        return user.credits

    async def get_records(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[dict]:
        """获取账单记录

        Args:
            user_id: 用户ID
            limit: 返回记录数量限制
            offset: 偏移量

        Returns:
            账单记录列表
        """
        uid = UUID(user_id) if isinstance(user_id, str) else user_id

        result = await self.db.execute(
            select(BillingRecord)
            .where(BillingRecord.user_id == uid)
            .order_by(desc(BillingRecord.created_at))
            .limit(limit)
            .offset(offset)
        )
        records = result.scalars().all()

        return [
            {
                "id": str(record.id),
                "type": record.type,
                "credits": record.credits,
                "balance_after": record.balance_after,
                "description": record.description,
                "reference_id": record.reference_id,
                "created_at": record.created_at.isoformat() if record.created_at else None
            }
            for record in records
        ]

    async def _get_user(self, user_id: str) -> Optional[User]:
        """获取用户对象

        Args:
            user_id: 用户ID

        Returns:
            用户对象或None
        """
        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        result = await self.db.execute(
            select(User).where(User.id == uid)
        )
        return result.scalar_one_or_none()

    async def get_pricing_rule(
        self,
        model_id: Optional[str] = None
    ) -> Tuple[Decimal, Decimal]:
        """获取模型的计费规则

        Args:
            model_id: 模型ID（UUID），如果为 None 则使用默认计费规则

        Returns:
            (input_credits_per_1k, output_credits_per_1k) 元组
        """
        if not model_id:
            # 使用默认计费规则
            return (Decimal(str(CREDITS_PER_1K_TOKENS)), Decimal(str(CREDITS_PER_1K_TOKENS)))

        # 查询当前生效的计费规则
        now = datetime.utcnow()
        result = await self.db.execute(
            select(AIModelPricing)
            .where(AIModelPricing.model_id == UUID(model_id) if isinstance(model_id, str) else model_id)
            .where(AIModelPricing.is_active == True)
            .where(AIModelPricing.effective_from <= now)
            .where(
                and_(
                    AIModelPricing.effective_until.is_(None) |
                    (AIModelPricing.effective_until > now)
                )
            )
            .order_by(AIModelPricing.effective_from.desc())
            .limit(1)
        )
        pricing = result.scalar_one_or_none()

        if pricing:
            return (pricing.input_credits_per_1k_tokens, pricing.output_credits_per_1k_tokens)
        else:
            # 如果没有找到计费规则，使用默认值
            return (Decimal(str(CREDITS_PER_1K_TOKENS)), Decimal(str(CREDITS_PER_1K_TOKENS)))

    async def calculate_model_credits(
        self,
        input_tokens: int,
        output_tokens: int,
        model_id: Optional[str] = None
    ) -> int:
        """根据模型和 token 数量计算积分消耗

        Args:
            input_tokens: 输入 token 数量
            output_tokens: 输出 token 数量
            model_id: 模型ID（UUID），如果为 None 则使用默认计费规则

        Returns:
            需要消耗的积分数（向上取整）
        """
        # 获取计费规则
        input_price, output_price = await self.get_pricing_rule(model_id)

        # 计算积分消耗
        input_credits = (Decimal(input_tokens) / Decimal('1000')) * input_price
        output_credits = (Decimal(output_tokens) / Decimal('1000')) * output_price
        total_credits = input_credits + output_credits

        # 向上取整
        return int(total_credits.to_integral_value(rounding='ROUND_UP'))


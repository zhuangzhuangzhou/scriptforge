"""积分服务

提供积分的消耗、充值、查询等功能。

Token 计费常量：
- CREDITS_PER_1K_TOKENS: 每1000 token消耗1积分
- BREAKDOWN_BASE_CREDITS: 剧情拆解基础消耗10积分
- SCRIPT_BASE_CREDITS: 剧本生成基础消耗5积分
"""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.billing import BillingRecord


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

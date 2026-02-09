"""
积分服务改造示例

这个文件展示了如何改造现有的 CreditsService 以支持数据库计费规则。

使用方法：
1. 将这些方法添加到你的 backend/app/core/credits.py 中
2. 或者参考这个示例改造你现有的积分计算逻辑
"""
from typing import Optional, Tuple
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.ai_model_pricing import AIModelPricing


class CreditsServiceExtension:
    """
    积分服务扩展 - 支持数据库计费规则

    将这些方法添加到你现有的 CreditsService 类中
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        """
        初始化积分服务

        Args:
            db: 数据库会话（可选）
        """
        self.db = db

    async def get_pricing_rule(
        self,
        model_id: Optional[str] = None
    ) -> Tuple[Decimal, Decimal]:
        """
        从数据库获取计费规则

        Args:
            model_id: 模型ID（UUID字符串）

        Returns:
            (input_price, output_price) 元组
            - input_price: 输入 Token 价格（每1K tokens的积分）
            - output_price: 输出 Token 价格（每1K tokens的积分）

        如果未找到规则，返回默认值 (1.0, 1.0)
        """
        if not self.db or not model_id:
            # 降级到默认值
            return (Decimal('1.0'), Decimal('1.0'))

        try:
            now = datetime.utcnow()

            # 查询当前生效的计费规则
            result = await self.db.execute(
                select(AIModelPricing)
                .where(
                    and_(
                        AIModelPricing.model_id == model_id,
                        AIModelPricing.is_active == True,
                        AIModelPricing.effective_from <= now,
                        (AIModelPricing.effective_until == None) |
                        (AIModelPricing.effective_until > now)
                    )
                )
                .order_by(AIModelPricing.effective_from.desc())
            )

            pricing = result.scalars().first()

            if pricing:
                return (
                    pricing.input_credits_per_1k_tokens,
                    pricing.output_credits_per_1k_tokens
                )

        except Exception as e:
            print(f"获取计费规则失败: {e}")

        # 降级到默认值
        return (Decimal('1.0'), Decimal('1.0'))

    async def calculate_model_credits(
        self,
        input_tokens: int,
        output_tokens: int,
        model_id: Optional[str] = None
    ) -> int:
        """
        根据模型计费规则计算积分消耗

        Args:
            input_tokens: 输入 Token 数量
            output_tokens: 输出 Token 数量
            model_id: 模型ID（可选）

        Returns:
            消耗的积分数量

        示例：
            # 使用数据库计费规则
            credits = await service.calculate_model_credits(
                input_tokens=1000,
                output_tokens=500,
                model_id="model-uuid"
            )

            # 使用默认规则
            credits = await service.calculate_model_credits(
                input_tokens=1000,
                output_tokens=500
            )
        """
        # 获取计费规则
        input_price, output_price = await self.get_pricing_rule(model_id)

        # 计算积分
        # 输入 Token 积分 = (input_tokens / 1000) * input_price
        input_credits = (Decimal(input_tokens) / Decimal('1000')) * input_price

        # 输出 Token 积分 = (output_tokens / 1000) * output_price
        output_credits = (Decimal(output_tokens) / Decimal('1000')) * output_price

        # 总积分（向上取整）
        total_credits = int((input_credits + output_credits).to_integral_value())

        return total_credits

    def calculate_credits_legacy(
        self,
        total_tokens: int,
        credits_per_1k_tokens: float = 1.0
    ) -> int:
        """
        传统的积分计算方法（向后兼容）

        Args:
            total_tokens: 总 Token 数量
            credits_per_1k_tokens: 每1K tokens的积分

        Returns:
            消耗的积分数量
        """
        credits = (total_tokens / 1000) * credits_per_1k_tokens
        return int(credits)


# ==================== 使用示例 ====================

async def example_usage():
    """使用示例"""
    from app.core.database import get_db

    # 示例1：使用数据库计费规则
    async for db in get_db():
        service = CreditsServiceExtension(db=db)

        # 计算积分（使用数据库规则）
        credits = await service.calculate_model_credits(
            input_tokens=1000,
            output_tokens=500,
            model_id="your-model-uuid"
        )
        print(f"消耗积分: {credits}")
        break

    # 示例2：使用默认规则
    service = CreditsServiceExtension()
    credits = await service.calculate_model_credits(
        input_tokens=1000,
        output_tokens=500
    )
    print(f"消耗积分（默认规则）: {credits}")

    # 示例3：传统方法（向后兼容）
    credits = service.calculate_credits_legacy(
        total_tokens=1500,
        credits_per_1k_tokens=1.0
    )
    print(f"消耗积分（传统方法）: {credits}")


# ==================== 集成到现有任务的示例 ====================

async def example_task_integration(db: AsyncSession, model_id: str):
    """
    展示如何在现有任务中集成新的计费系统

    原有代码：
        credits = calculate_credits(total_tokens)

    改造后：
        service = CreditsServiceExtension(db=db)
        credits = await service.calculate_model_credits(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_id=model_id
        )
    """
    # 创建积分服务
    service = CreditsServiceExtension(db=db)

    # 假设 AI 调用返回了 token 使用情况
    input_tokens = 1000
    output_tokens = 500

    # 计算积分
    credits = await service.calculate_model_credits(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model_id=model_id
    )

    print(f"本次调用消耗积分: {credits}")

    # 扣除用户积分
    # await deduct_user_credits(user_id, credits)

    return credits


# ==================== 价格对比工具 ====================

async def compare_pricing(db: AsyncSession):
    """
    对比不同模型的价格

    这个工具可以帮助用户选择最经济的模型
    """
    service = CreditsServiceExtension(db=db)

    models = [
        ("gpt-4-turbo-uuid", "GPT-4 Turbo"),
        ("gpt-3.5-turbo-uuid", "GPT-3.5 Turbo"),
        ("claude-3-opus-uuid", "Claude 3 Opus"),
    ]

    print("价格对比（1000 输入 + 500 输出 tokens）:")
    print("-" * 60)

    for model_id, model_name in models:
        credits = await service.calculate_model_credits(
            input_tokens=1000,
            output_tokens=500,
            model_id=model_id
        )
        print(f"{model_name:20s}: {credits:6d} 积分")

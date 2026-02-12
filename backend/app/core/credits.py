"""积分服务

提供积分的消耗、充值、查询等功能。

纯积分制定价（双重计费，可配置）：
- 基础费：从数据库 system_configs 读取，默认 breakdown 100、script 50、qa 30
- Token 费：可配置开关，从数据库读取
- 充值比例: 1 元 = 100 积分
"""
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from uuid import UUID
from decimal import Decimal
import os
import time
import logging

from sqlalchemy import select, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.billing import BillingRecord
from app.models.ai_model import AIModel
from app.models.ai_model_pricing import AIModelPricing

logger = logging.getLogger(__name__)


# 默认基础费定价（可被数据库配置覆盖）
CREDITS_PRICING = {
    "breakdown": 100,
    "script": 50,
    "qa": 30,
    "retry": 50,
}

# 默认 Token 计费配置（可被数据库配置覆盖）
TOKEN_BILLING_ENABLED = os.getenv("TOKEN_BILLING_ENABLED", "false").lower() == "true"
TOKEN_CREDITS_INPUT = int(os.getenv("TOKEN_CREDITS_INPUT", "1"))
TOKEN_CREDITS_OUTPUT = int(os.getenv("TOKEN_CREDITS_OUTPUT", "2"))

# 兼容旧常量
CREDITS_PER_1K_TOKENS = TOKEN_CREDITS_INPUT
BREAKDOWN_BASE_CREDITS = CREDITS_PRICING["breakdown"]
SCRIPT_BASE_CREDITS = CREDITS_PRICING["script"]

# 配置缓存（TTL 60 秒，减少数据库查询）
_config_cache: Optional[dict] = None
_config_cache_ts: float = 0
_CONFIG_CACHE_TTL = 60  # 秒

_DEFAULT_CONFIG = {
    "base": {
        "breakdown": CREDITS_PRICING["breakdown"],
        "script": CREDITS_PRICING["script"],
        "qa": CREDITS_PRICING["qa"],
        "retry": CREDITS_PRICING["retry"],
    },
    "token": {
        "enabled": TOKEN_BILLING_ENABLED,
        "input_per_1k": TOKEN_CREDITS_INPUT,
        "output_per_1k": TOKEN_CREDITS_OUTPUT,
    }
}


def _parse_config_rows(configs: dict) -> dict:
    """将数据库配置行解析为结构化字典"""
    return {
        "base": {
            "breakdown": int(configs.get("credits_breakdown", "100")),
            "script": int(configs.get("credits_script", "50")),
            "qa": int(configs.get("credits_qa", "30")),
            "retry": int(configs.get("credits_retry", "50")),
        },
        "token": {
            "enabled": configs.get("token_billing_enabled", "false").lower() == "true",
            "input_per_1k": int(configs.get("token_input_per_1k", "1")),
            "output_per_1k": int(configs.get("token_output_per_1k", "2")),
        }
    }


async def get_credits_config(db: AsyncSession) -> dict:
    """从数据库获取积分配置（带缓存，TTL 60 秒）"""
    global _config_cache, _config_cache_ts

    now = time.monotonic()
    if _config_cache is not None and (now - _config_cache_ts) < _CONFIG_CACHE_TTL:
        return _config_cache

    try:
        from app.models.system_config import SystemConfig
        result = await db.execute(select(SystemConfig))
        configs = {c.key: c.value for c in result.scalars().all()}
        parsed = _parse_config_rows(configs)
        _config_cache = parsed
        _config_cache_ts = now
        return parsed
    except Exception as e:
        logger.warning(f"读取系统配置失败，使用默认值: {e}")
        return _DEFAULT_CONFIG


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

    async def check_and_grant_monthly_credits(self, user: User) -> int:
        """检查并发放月度积分

        Args:
            user: 用户对象

        Returns:
            int: 本次发放的积分数量，0 表示无需发放
        """
        from app.core.quota import get_tier_config

        config = get_tier_config(user.tier)
        now = datetime.now(timezone.utc)

        # 检查是否需要重置（每月1号或首次）
        if self._should_reset_monthly(user, now):
            granted = config.monthly_credits
            user.credits += granted
            user.monthly_credits_granted = granted
            user.credits_reset_at = now

            # 记录账单
            record = BillingRecord(
                user_id=user.id if not isinstance(user.id, str) else UUID(user.id),
                type="grant",
                credits=granted,
                balance_after=user.credits,
                description=f"月度积分赠送 ({config.display_name})",
                created_at=now
            )
            self.db.add(record)
            return granted
        return 0

    def _should_reset_monthly(self, user: User, now: datetime) -> bool:
        """判断是否需要重置月度积分"""
        if user.credits_reset_at is None:
            return True

        reset_at = user.credits_reset_at
        if reset_at.year < now.year:
            return True
        if reset_at.year == now.year and reset_at.month < now.month:
            return True
        return False

    async def check_credits_for_task(self, user: User, task_type: str) -> dict:
        """检查积分是否足够执行任务

        Args:
            user: 用户对象
            task_type: 任务类型（breakdown/script/qa/retry）

        Returns:
            dict: {allowed, cost, balance, shortfall}
        """
        # 先尝试发放月度积分
        await self.check_and_grant_monthly_credits(user)

        # 从数据库读取配置
        config = await get_credits_config(self.db)
        cost = config["base"].get(task_type, CREDITS_PRICING.get(task_type, 0))

        return {
            "allowed": user.credits >= cost,
            "cost": cost,
            "balance": user.credits,
            "shortfall": max(0, cost - user.credits)
        }

    async def consume_credits_for_task(
        self,
        user: User,
        task_type: str,
        reference_id: Optional[str] = None
    ) -> dict:
        """消耗任务积分

        Args:
            user: 用户对象
            task_type: 任务类型
            reference_id: 关联ID（如任务ID）

        Returns:
            {success: bool, balance: int, message: str}
        """
        # 从数据库读取配置
        config = await get_credits_config(self.db)
        cost = config["base"].get(task_type, CREDITS_PRICING.get(task_type, 0))

        if cost <= 0:
            return {
                "success": False,
                "balance": user.credits,
                "message": f"未知任务类型: {task_type}"
            }

        if user.credits < cost:
            return {
                "success": False,
                "balance": user.credits,
                "message": f"积分不足: 需要 {cost}，余额 {user.credits}"
            }

        user.credits -= cost
        balance_after = user.credits

        # 任务类型描述映射
        task_desc = {
            "breakdown": "剧情拆解",
            "script": "剧本生成",
            "qa": "质检校验",
            "retry": "任务重试"
        }

        record = BillingRecord(
            user_id=user.id if not isinstance(user.id, str) else UUID(user.id),
            type="consume",
            credits=-cost,
            balance_after=balance_after,
            description=f"{task_desc.get(task_type, task_type)}（基础费）",
            reference_id=reference_id,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(record)

        return {
            "success": True,
            "balance": balance_after,
            "message": "基础费扣除成功"
        }

    async def consume_token_credits(
        self,
        user: User,
        input_tokens: int,
        output_tokens: int,
        task_type: str,
        reference_id: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> dict:
        """消耗 token 积分（任务完成后调用）

        注意：需要数据库配置 token_billing_enabled=true 才会实际扣费

        Args:
            user: 用户对象
            input_tokens: 输入 token 数量
            output_tokens: 输出 token 数量
            task_type: 任务类型（用于描述）
            reference_id: 关联ID（如任务ID）
            model_id: 模型ID（用于查询自定义计费规则）

        Returns:
            {success: bool, balance: int, token_credits: int, message: str}
        """
        # 从数据库读取 token 计费配置
        config = await get_credits_config(self.db)
        token_billing_enabled = config["token"]["enabled"]

        # 检查 token 计费是否启用
        if not token_billing_enabled:
            return {
                "success": True,
                "balance": user.credits,
                "token_credits": 0,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "enabled": False,
                "message": "Token 计费未启用"
            }

        # 计算 token 积分
        token_credits = await self.calculate_token_credits(
            input_tokens, output_tokens, model_id
        )

        if token_credits <= 0:
            return {
                "success": True,
                "balance": user.credits,
                "token_credits": 0,
                "message": "无 token 消耗"
            }

        # 检查余额（允许透支，因为基础费已预扣）
        if user.credits < token_credits:
            # 余额不足时扣到 0，记录欠费
            actual_deduct = user.credits
            user.credits = 0
            shortfall = token_credits - actual_deduct
        else:
            actual_deduct = token_credits
            user.credits -= token_credits
            shortfall = 0

        balance_after = user.credits

        # 任务类型描述
        task_desc = {
            "breakdown": "剧情拆解",
            "script": "剧本生成",
            "qa": "质检校验",
            "retry": "任务重试"
        }

        record = BillingRecord(
            user_id=user.id if not isinstance(user.id, str) else UUID(user.id),
            type="consume",
            credits=-actual_deduct,
            balance_after=balance_after,
            description=f"{task_desc.get(task_type, task_type)}（Token: {input_tokens}+{output_tokens}）",
            reference_id=reference_id,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(record)

        return {
            "success": True,
            "balance": balance_after,
            "token_credits": token_credits,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "shortfall": shortfall,
            "message": f"Token 费用 {token_credits} 积分" + (f"（欠费 {shortfall}）" if shortfall > 0 else "")
        }

    async def calculate_token_credits(
        self,
        input_tokens: int,
        output_tokens: int,
        model_id: Optional[str] = None
    ) -> int:
        """计算 token 积分消耗

        Args:
            input_tokens: 输入 token 数量
            output_tokens: 输出 token 数量
            model_id: 模型ID（用于查询自定义计费规则）

        Returns:
            int: 需要消耗的积分数（向上取整）
        """
        # 获取计费规则
        input_price, output_price = await self.get_pricing_rule(model_id)

        # 计算积分消耗
        input_credits = (Decimal(input_tokens) / Decimal('1000')) * input_price
        output_credits = (Decimal(output_tokens) / Decimal('1000')) * output_price
        total_credits = input_credits + output_credits

        # 向上取整
        return int(total_credits.to_integral_value(rounding='ROUND_UP'))

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

    async def get_credits_info(self, user_id: str) -> dict:
        """获取用户积分详情（纯积分制）

        Args:
            user_id: 用户ID

        Returns:
            dict: 积分详情
        """
        from app.core.quota import get_tier_config

        # 从数据库读取配置
        credits_config = await get_credits_config(self.db)

        user = await self._get_user(user_id)
        if not user:
            return {
                "balance": 0,
                "monthly_granted": 0,
                "next_grant_at": None,
                "tier": "free",
                "pricing": credits_config
            }

        # 先尝试发放月度积分
        await self.check_and_grant_monthly_credits(user)

        config = get_tier_config(user.tier)

        # 计算下次发放时间（下月1号）
        now = datetime.now(timezone.utc)
        if now.month == 12:
            next_grant = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_grant = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

        # 计算本月消耗总额
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        consumed_result = await self.db.execute(
            select(func.coalesce(func.sum(func.abs(BillingRecord.credits)), 0))
            .where(BillingRecord.user_id == uid)
            .where(BillingRecord.type == "consume")
            .where(BillingRecord.created_at >= month_start)
        )
        monthly_consumed = int(consumed_result.scalar() or 0)

        return {
            "balance": user.credits,
            "monthly_granted": user.monthly_credits_granted or 0,
            "monthly_credits": config.monthly_credits,
            "monthly_consumed": monthly_consumed,
            "next_grant_at": next_grant.isoformat(),
            "tier": user.tier,
            "tier_display": config.display_name,
            "pricing": credits_config
        }

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
            # 使用默认计费规则：输入 1 积分/1K，输出 2 积分/1K
            return (Decimal(str(TOKEN_CREDITS_INPUT)), Decimal(str(TOKEN_CREDITS_OUTPUT)))

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


# ============ 同步版本函数（用于 Celery worker）============

def get_credits_config_sync(db: "Session") -> dict:
    """从数据库获取积分配置（同步版本，带缓存）

    用于 Celery worker 中的同步操作。

    Args:
        db: 同步数据库会话

    Returns:
        dict: 包含 base 和 token 配置的字典
    """
    global _config_cache, _config_cache_ts

    now = time.monotonic()
    if _config_cache is not None and (now - _config_cache_ts) < _CONFIG_CACHE_TTL:
        return _config_cache

    try:
        from app.models.system_config import SystemConfig
        result = db.query(SystemConfig).all()
        configs = {c.key: c.value for c in result}
        parsed = _parse_config_rows(configs)
        _config_cache = parsed
        _config_cache_ts = now
        return parsed
    except Exception as e:
        logger.warning(f"读取系统配置失败，使用默认值: {e}")
        return _DEFAULT_CONFIG


def consume_credits_for_task_sync(db: "Session", user_id: str, task_type: str, reference_id: Optional[str] = None) -> dict:
    """消耗任务积分（同步版本）

    用于 Celery worker 中的同步操作。
    注意：不会自行 commit，由调用方统一管理事务。

    Args:
        db: 同步数据库会话
        user_id: 用户ID
        task_type: 任务类型（breakdown/script/qa/retry）
        reference_id: 关联ID（如任务ID）

    Returns:
        {success: bool, balance: int, cost: int, message: str}
    """
    from app.models.user import User

    # 从数据库读取配置
    config = get_credits_config_sync(db)
    cost = config["base"].get(task_type, CREDITS_PRICING.get(task_type, 0))

    if cost <= 0:
        return {
            "success": False,
            "balance": 0,
            "cost": 0,
            "message": f"未知任务类型: {task_type}"
        }

    # 获取用户
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {
            "success": False,
            "balance": 0,
            "cost": cost,
            "message": "用户不存在"
        }

    if user.credits < cost:
        return {
            "success": False,
            "balance": user.credits,
            "cost": cost,
            "message": f"积分不足: 需要 {cost}，余额 {user.credits}"
        }

    user.credits -= cost
    balance_after = user.credits

    # 任务类型描述映射
    task_desc = {
        "breakdown": "剧情拆解",
        "script": "剧本生成",
        "qa": "质检校验",
        "retry": "任务重试"
    }

    record = BillingRecord(
        user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
        type="consume",
        credits=-cost,
        balance_after=balance_after,
        description=f"{task_desc.get(task_type, task_type)}（基础费）",
        reference_id=reference_id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(record)

    return {
        "success": True,
        "balance": balance_after,
        "cost": cost,
        "message": "基础费扣除成功"
    }


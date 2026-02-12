"""计费管理 API（纯积分制）

端点：
- GET /billing/balance - 查询余额
- GET /billing/credits - 查询积分详情（含定价）
- GET /billing/records - 账单记录
- POST /billing/recharge - 充值积分（模拟）
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from app.core.database import get_db
from app.core.credits import CreditsService, CREDITS_PRICING
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()


# Pydantic 模型
class BalanceResponse(BaseModel):
    """余额响应"""
    credits: int


class TokenPricing(BaseModel):
    """Token 定价"""
    enabled: bool
    input_per_1k: int
    output_per_1k: int


class PricingInfo(BaseModel):
    """定价信息"""
    base: Dict[str, int]
    token: TokenPricing


class CreditsInfoResponse(BaseModel):
    """积分详情响应（纯积分制 + Token 计费）"""
    balance: int
    monthly_granted: int
    monthly_credits: int
    next_grant_at: Optional[str] = None
    tier: str
    tier_display: str
    pricing: PricingInfo


class BillingRecordItem(BaseModel):
    """账单记录项"""
    id: str
    type: str
    credits: int
    balance_after: int
    description: str
    reference_id: Optional[str] = None
    created_at: Optional[str] = None


class RecordsResponse(BaseModel):
    """账单记录响应"""
    records: List[BillingRecordItem]
    limit: int
    offset: int


class RechargeRequest(BaseModel):
    """充值请求"""
    amount: int = Field(..., gt=0, description="充值金额（元），1元=100积分")
    payment_method: str = Field(..., description="支付方式")


class RechargeResponse(BaseModel):
    """充值响应"""
    success: bool
    balance: int
    credits_added: int
    message: str


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """查询当前用户积分余额"""
    service = CreditsService(db)
    balance = await service.get_balance(str(current_user.id))
    return {"credits": balance}


@router.get("/credits", response_model=CreditsInfoResponse)
async def get_credits_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """查询积分详情（纯积分制）

    返回：
    - balance: 当前积分余额
    - monthly_granted: 本月已赠送积分
    - monthly_credits: 等级每月赠送额度
    - next_grant_at: 下次赠送时间
    - tier: 用户等级
    - tier_display: 等级显示名称
    - pricing: 任务积分定价
    """
    service = CreditsService(db)
    info = await service.get_credits_info(str(current_user.id))
    return info


@router.get("/records", response_model=RecordsResponse)
async def get_records(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户账单记录

    Args:
        limit: 返回记录数量限制，默认20
        offset: 偏移量，默认0
    """
    # 参数校验
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit 必须在 1-100 之间"
        )
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="offset 不能为负数"
        )

    service = CreditsService(db)
    records = await service.get_records(str(current_user.id), limit, offset)
    return {"records": records, "limit": limit, "offset": offset}


@router.post("/recharge", response_model=RechargeResponse)
async def recharge_credits(
    request: RechargeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """充值积分（模拟接口）

    注意：这是一个模拟接口，实际生产环境应由支付回调触发充值。
    当前仅用于测试和演示目的。

    充值比例：1 元 = 100 积分

    Args:
        request: 充值请求，包含 amount（金额，元）和 payment_method（支付方式）
    """
    # 模拟支付验证（实际应由支付网关回调）
    valid_payment_methods = ["alipay", "wechat", "test"]
    if request.payment_method not in valid_payment_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的支付方式，支持: {', '.join(valid_payment_methods)}"
        )

    # 计算积分（1元 = 100积分）
    credits_to_add = request.amount * 100

    # 执行充值
    service = CreditsService(db)
    result = await service.add_credits(
        user_id=str(current_user.id),
        amount=credits_to_add,
        description=f"充值 ¥{request.amount} - {request.payment_method}",
        reference_id=None  # 实际应为支付订单号
    )

    if result["success"]:
        await db.commit()

    return RechargeResponse(
        success=result["success"],
        balance=result["balance"],
        credits_added=credits_to_add if result["success"] else 0,
        message=result["message"]
    )

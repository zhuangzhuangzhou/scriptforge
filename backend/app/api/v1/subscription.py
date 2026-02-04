"""订阅管理 API

端点：
- GET /subscription/me - 获取当前订阅
- POST /subscription/upgrade - 升级/续费订阅
- GET /subscription/history - 订阅历史
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.subscription import SubscriptionService
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()


# Pydantic 模型
class SubscriptionInfo(BaseModel):
    """订阅信息"""
    id: str
    tier: str
    status: str
    amount: int
    started_at: datetime
    expires_at: datetime
    created_at: datetime


class CurrentSubscriptionResponse(BaseModel):
    """当前订阅状态响应"""
    current_tier: str
    subscription: Optional[SubscriptionInfo] = None
    is_active: bool


class UpgradeRequest(BaseModel):
    """升级请求"""
    tier: str = Field(..., description="目标等级 (creator, studio, enterprise)")
    months: int = Field(..., gt=0, description="订阅月数")


class UpgradeResponse(BaseModel):
    """升级响应"""
    success: bool
    subscription: SubscriptionInfo
    message: str


class HistoryResponse(BaseModel):
    """订阅历史响应"""
    records: List[SubscriptionInfo]
    limit: int
    offset: int


@router.get("/me", response_model=CurrentSubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的活跃订阅详情及等级"""
    service = SubscriptionService(db)

    # 获取活跃订阅
    active_sub = await service.get_active_subscription(str(current_user.id))

    # 转换为响应模型
    sub_info = None
    if active_sub:
        sub_info = SubscriptionInfo(
            id=str(active_sub.id),
            tier=active_sub.tier,
            status=active_sub.status,
            amount=active_sub.amount,
            started_at=active_sub.started_at,
            expires_at=active_sub.expires_at,
            created_at=active_sub.created_at
        )

    return CurrentSubscriptionResponse(
        current_tier=current_user.tier,
        subscription=sub_info,
        is_active=active_sub is not None
    )


@router.post("/upgrade", response_model=UpgradeResponse)
async def upgrade_subscription(
    request: UpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """升级或续费订阅"""
    service = SubscriptionService(db)

    try:
        # 调用核心服务创建订阅
        # 注意：create_subscription 会处理余额扣除和记录创建
        result = await service.create_subscription(
            user_id=str(current_user.id),
            tier=request.tier,
            months=request.months
        )

        # 提交事务
        await db.commit()

        # 构造响应
        # create_subscription 返回的是 dict，这里为了方便直接构造模型，
        # 但通常 create_subscription 返回 dict 包含 ISO 格式时间字符串，
        # Pydantic 会自动尝试转换。

        # 重新获取刚才创建的订阅以确保格式一致性（或者直接使用返回结果）
        # 这里直接使用返回结果
        return UpgradeResponse(
            success=True,
            subscription=SubscriptionInfo(
                id=result["id"],
                tier=result["tier"],
                status=result["status"],
                amount=result["amount"],
                started_at=datetime.fromisoformat(result["started_at"]),
                expires_at=datetime.fromisoformat(result["expires_at"]),
                created_at=datetime.fromisoformat(result["created_at"])
            ),
            message="订阅成功"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # 其他错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"订阅失败: {str(e)}"
        )


@router.get("/history", response_model=HistoryResponse)
async def get_subscription_history(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户所有的订阅记录"""
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

    service = SubscriptionService(db)
    subscriptions = await service.get_subscriptions(str(current_user.id), limit, offset)

    records = [
        SubscriptionInfo(
            id=str(sub.id),
            tier=sub.tier,
            status=sub.status,
            amount=sub.amount,
            started_at=sub.started_at,
            expires_at=sub.expires_at,
            created_at=sub.created_at
        ) for sub in subscriptions
    ]

    return HistoryResponse(
        records=records,
        limit=limit,
        offset=offset
    )

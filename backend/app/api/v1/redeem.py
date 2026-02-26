"""兑换码 API"""
import secrets
import string
from datetime import datetime, timezone
from typing import Optional, List, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.api.v1.admin import check_admin
from app.models.user import User
from app.models.redeem_code import RedeemCode, RedeemRecord
from app.models.billing import BillingRecord

router = APIRouter()


def generate_redeem_code(length: int = 12) -> str:
    """生成随机兑换码（大写字母+数字，排除易混淆字符）"""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 排除 I, O, 0, 1
    return "".join(secrets.choice(chars) for _ in range(length))


# ==================== 用户端 API ====================

class UseRedeemCodeRequest(BaseModel):
    """使用兑换码请求"""
    code: str = Field(..., min_length=4, max_length=32, description="兑换码")


@router.post("/redeem/use")
async def use_redeem_code(
    request: UseRedeemCodeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """用户使用兑换码"""
    code = request.code.strip().upper()

    # 查找兑换码
    result = await db.execute(
        select(RedeemCode).where(RedeemCode.code == code)
    )
    redeem_code = result.scalar_one_or_none()

    if not redeem_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="兑换码不存在"
        )

    # 检查是否启用
    if not redeem_code.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="兑换码已停用"
        )

    # 检查是否过期
    if redeem_code.expires_at and redeem_code.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="兑换码已过期"
        )

    # 检查使用次数
    if redeem_code.max_uses > 0 and redeem_code.used_count >= redeem_code.max_uses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="兑换码已达到使用上限"
        )

    # 检查用户是否已使用过此兑换码
    existing_record = await db.execute(
        select(RedeemRecord).where(
            RedeemRecord.redeem_code_id == redeem_code.id,
            RedeemRecord.user_id == user.id
        )
    )
    if existing_record.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已使用过此兑换码"
        )

    # 执行兑换
    credits_granted = 0
    tier_before = user.tier
    tier_after = user.tier

    if redeem_code.type == "credits":
        # 积分充值
        credits_granted = redeem_code.credits
        user.credits += credits_granted

        # 创建账单记录
        billing_record = BillingRecord(
            user_id=user.id,
            type="redeem",
            credits=credits_granted,
            balance_after=user.credits,
            description=f"兑换码充值（{code}）",
            reference_id=str(redeem_code.id),
            created_at=datetime.now(timezone.utc)
        )
        db.add(billing_record)

    elif redeem_code.type == "tier_upgrade":
        # 等级升级
        if redeem_code.tier:
            tier_after = redeem_code.tier
            user.tier = tier_after
            # TODO: 如果需要记录升级有效期，可以在 Subscription 表中创建记录

    # 更新兑换码使用次数
    redeem_code.used_count += 1

    # 创建兑换记录
    redeem_record = RedeemRecord(
        redeem_code_id=redeem_code.id,
        user_id=user.id,
        code=code,
        type=redeem_code.type,
        credits_granted=credits_granted,
        tier_before=tier_before,
        tier_after=tier_after,
        created_at=datetime.now(timezone.utc)
    )
    db.add(redeem_record)

    await db.commit()

    return {
        "success": True,
        "type": redeem_code.type,
        "credits_granted": credits_granted,
        "tier_before": tier_before,
        "tier_after": tier_after,
        "new_balance": user.credits,
        "message": f"兑换成功！获得 {credits_granted} 积分" if redeem_code.type == "credits" else f"兑换成功！已升级到 {tier_after}"
    }


# ==================== 管理端 API ====================

class CreateRedeemCodeRequest(BaseModel):
    """创建兑换码请求"""
    model_config = {"extra": "forbid"}

    type: Literal["credits", "tier_upgrade"] = Field(default="credits", description="兑换类型")
    credits: int = Field(default=0, ge=0, description="积分数量（type=credits 时有效）")
    tier: Optional[str] = Field(default=None, description="升级到的等级（type=tier_upgrade 时有效）")
    tier_days: int = Field(default=30, ge=1, description="升级有效天数")
    max_uses: int = Field(default=1, ge=0, description="最大使用次数（0=无限）")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")
    note: Optional[str] = Field(default=None, max_length=500, description="备注")
    code: Optional[str] = Field(default=None, min_length=4, max_length=32, description="自定义兑换码（留空自动生成）")
    count: int = Field(default=1, ge=1, le=100, description="批量生成数量")


@router.post("/admin/redeem")
async def create_redeem_codes(
    request: CreateRedeemCodeRequest,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员创建兑换码"""
    # 验证参数
    if request.type == "credits" and request.credits <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="积分类型兑换码必须设置积分数量"
        )

    if request.type == "tier_upgrade" and not request.tier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="升级类型兑换码必须设置目标等级"
        )

    created_codes = []

    for i in range(request.count):
        # 生成或使用自定义兑换码
        if request.code and request.count == 1:
            code = request.code.strip().upper()
            # 检查是否已存在
            existing = await db.execute(
                select(RedeemCode).where(RedeemCode.code == code)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"兑换码 {code} 已存在"
                )
        else:
            # 自动生成唯一兑换码
            for _ in range(10):  # 最多尝试 10 次
                code = generate_redeem_code()
                existing = await db.execute(
                    select(RedeemCode).where(RedeemCode.code == code)
                )
                if not existing.scalar_one_or_none():
                    break
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="生成兑换码失败，请重试"
                )

        redeem_code = RedeemCode(
            code=code,
            type=request.type,
            credits=request.credits if request.type == "credits" else 0,
            tier=request.tier if request.type == "tier_upgrade" else None,
            tier_days=request.tier_days,
            max_uses=request.max_uses,
            expires_at=request.expires_at,
            note=request.note,
            created_by=admin.id,
            is_active=True
        )
        db.add(redeem_code)
        created_codes.append(code)

    await db.commit()

    return {
        "success": True,
        "codes": created_codes,
        "count": len(created_codes),
        "type": request.type,
        "credits": request.credits if request.type == "credits" else None,
        "tier": request.tier if request.type == "tier_upgrade" else None,
        "message": f"成功创建 {len(created_codes)} 个兑换码"
    }


@router.get("/admin/redeem")
async def list_redeem_codes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None, description="兑换类型筛选"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员获取兑换码列表"""
    query = select(RedeemCode)

    if type:
        query = query.where(RedeemCode.type == type)
    if is_active is not None:
        query = query.where(RedeemCode.is_active == is_active)

    # 统计总数
    count_query = select(func.count(RedeemCode.id))
    if type:
        count_query = count_query.where(RedeemCode.type == type)
    if is_active is not None:
        count_query = count_query.where(RedeemCode.is_active == is_active)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(RedeemCode.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    codes = result.scalars().all()

    return {
        "items": [
            {
                "id": str(code.id),
                "code": code.code,
                "type": code.type,
                "credits": code.credits,
                "tier": code.tier,
                "tier_days": code.tier_days,
                "max_uses": code.max_uses,
                "used_count": code.used_count,
                "is_active": code.is_active,
                "expires_at": code.expires_at.isoformat() if code.expires_at else None,
                "note": code.note,
                "created_at": code.created_at.isoformat() if code.created_at else None
            }
            for code in codes
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/admin/redeem/{code_id}")
async def get_redeem_code(
    code_id: str,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员获取兑换码详情"""
    result = await db.execute(
        select(RedeemCode).where(RedeemCode.id == code_id)
    )
    code = result.scalar_one_or_none()

    if not code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="兑换码不存在"
        )

    # 获取使用记录
    records_result = await db.execute(
        select(RedeemRecord, User)
        .join(User, RedeemRecord.user_id == User.id)
        .where(RedeemRecord.redeem_code_id == code.id)
        .order_by(RedeemRecord.created_at.desc())
        .limit(50)
    )
    records = records_result.all()

    return {
        "id": str(code.id),
        "code": code.code,
        "type": code.type,
        "credits": code.credits,
        "tier": code.tier,
        "tier_days": code.tier_days,
        "max_uses": code.max_uses,
        "used_count": code.used_count,
        "is_active": code.is_active,
        "expires_at": code.expires_at.isoformat() if code.expires_at else None,
        "note": code.note,
        "created_at": code.created_at.isoformat() if code.created_at else None,
        "records": [
            {
                "id": str(record.id),
                "user_id": str(record.user_id),
                "username": user.username,
                "type": record.type,
                "credits_granted": record.credits_granted,
                "tier_before": record.tier_before,
                "tier_after": record.tier_after,
                "created_at": record.created_at.isoformat() if record.created_at else None
            }
            for record, user in records
        ]
    }


class UpdateRedeemCodeRequest(BaseModel):
    """更新兑换码请求"""
    model_config = {"extra": "forbid"}

    is_active: Optional[bool] = None
    max_uses: Optional[int] = Field(None, ge=0)
    expires_at: Optional[datetime] = None
    note: Optional[str] = Field(None, max_length=500)


@router.put("/admin/redeem/{code_id}")
async def update_redeem_code(
    code_id: str,
    request: UpdateRedeemCodeRequest,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员更新兑换码"""
    result = await db.execute(
        select(RedeemCode).where(RedeemCode.id == code_id)
    )
    code = result.scalar_one_or_none()

    if not code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="兑换码不存在"
        )

    if request.is_active is not None:
        code.is_active = request.is_active
    if request.max_uses is not None:
        code.max_uses = request.max_uses
    if request.expires_at is not None:
        code.expires_at = request.expires_at
    if request.note is not None:
        code.note = request.note

    await db.commit()
    await db.refresh(code)

    return {
        "success": True,
        "id": str(code.id),
        "code": code.code,
        "is_active": code.is_active,
        "max_uses": code.max_uses,
        "expires_at": code.expires_at.isoformat() if code.expires_at else None,
        "note": code.note
    }


@router.delete("/admin/redeem/{code_id}")
async def delete_redeem_code(
    code_id: str,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员删除兑换码"""
    result = await db.execute(
        select(RedeemCode).where(RedeemCode.id == code_id)
    )
    code = result.scalar_one_or_none()

    if not code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="兑换码不存在"
        )

    # 检查是否有使用记录
    if code.used_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"兑换码已被使用 {code.used_count} 次，无法删除。建议停用而非删除。"
        )

    await db.delete(code)
    await db.commit()

    return {
        "success": True,
        "message": f"兑换码 {code.code} 已删除"
    }

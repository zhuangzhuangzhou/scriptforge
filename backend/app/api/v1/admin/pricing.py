"""计费规则管理 API"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.core.database import get_db
from app.models.ai_model_pricing import AIModelPricing
from app.models.ai_model import AIModel
from app.schemas.pricing import (
    PricingCreate,
    PricingUpdate,
    PricingResponse
)
from app.api.v1.admin import check_admin

router = APIRouter()


@router.get("", response_model=List[PricingResponse])
async def get_pricing_rules(
    model_id: str = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """获取计费规则列表

    Args:
        model_id: 可选，按模型筛选
    """
    # 构建查询
    query = select(AIModelPricing, AIModel).join(
        AIModel,
        AIModelPricing.model_id == AIModel.id
    ).order_by(AIModelPricing.created_at.desc())

    # 如果指定了模型，添加筛选条件
    if model_id:
        query = query.where(AIModelPricing.model_id == model_id)

    result = await db.execute(query)

    pricing_rules = []
    for pricing, model in result:
        pricing_dict = {
            "id": str(pricing.id),
            "model": {
                "id": str(model.id),
                "model_key": model.model_key,
                "display_name": model.display_name
            },
            "input_credits_per_1k_tokens": pricing.input_credits_per_1k_tokens,
            "output_credits_per_1k_tokens": pricing.output_credits_per_1k_tokens,
            "min_credits_per_request": pricing.min_credits_per_request,
            "effective_from": pricing.effective_from,
            "effective_until": pricing.effective_until,
            "is_active": pricing.is_active,
            "created_at": pricing.created_at,
            "updated_at": pricing.updated_at
        }
        pricing_rules.append(pricing_dict)

    return pricing_rules


@router.get("/{pricing_id}", response_model=PricingResponse)
async def get_pricing_rule(
    pricing_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """获取计费规则详情"""
    # 查询计费规则及其模型
    result = await db.execute(
        select(AIModelPricing, AIModel)
        .join(AIModel, AIModelPricing.model_id == AIModel.id)
        .where(AIModelPricing.id == pricing_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="计费规则不存在")

    pricing, model = row

    return {
        "id": str(pricing.id),
        "model": {
            "id": str(model.id),
            "model_key": model.model_key,
            "display_name": model.display_name
        },
        "input_credits_per_1k_tokens": pricing.input_credits_per_1k_tokens,
        "output_credits_per_1k_tokens": pricing.output_credits_per_1k_tokens,
        "min_credits_per_request": pricing.min_credits_per_request,
        "effective_from": pricing.effective_from,
        "effective_until": pricing.effective_until,
        "is_active": pricing.is_active,
        "created_at": pricing.created_at,
        "updated_at": pricing.updated_at
    }


@router.post("", response_model=PricingResponse)
async def create_pricing_rule(
    pricing_data: PricingCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """创建计费规则"""
    # 检查模型是否存在
    result = await db.execute(
        select(AIModel).where(AIModel.id == pricing_data.model_id)
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")

    # 创建计费规则
    pricing = AIModelPricing(
        model_id=pricing_data.model_id,
        input_credits_per_1k_tokens=pricing_data.input_credits_per_1k_tokens,
        output_credits_per_1k_tokens=pricing_data.output_credits_per_1k_tokens,
        min_credits_per_request=pricing_data.min_credits_per_request,
        effective_from=pricing_data.effective_from,
        effective_until=pricing_data.effective_until
    )
    db.add(pricing)
    await db.commit()
    await db.refresh(pricing)

    return {
        "id": str(pricing.id),
        "model": {
            "id": str(model.id),
            "model_key": model.model_key,
            "display_name": model.display_name
        },
        "input_credits_per_1k_tokens": pricing.input_credits_per_1k_tokens,
        "output_credits_per_1k_tokens": pricing.output_credits_per_1k_tokens,
        "min_credits_per_request": pricing.min_credits_per_request,
        "effective_from": pricing.effective_from,
        "effective_until": pricing.effective_until,
        "is_active": pricing.is_active,
        "created_at": pricing.created_at,
        "updated_at": pricing.updated_at
    }


@router.put("/{pricing_id}", response_model=PricingResponse)
async def update_pricing_rule(
    pricing_id: str,
    pricing_data: PricingUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """更新计费规则"""
    # 查询计费规则及其模型
    result = await db.execute(
        select(AIModelPricing, AIModel)
        .join(AIModel, AIModelPricing.model_id == AIModel.id)
        .where(AIModelPricing.id == pricing_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="计费规则不存在")

    pricing, model = row

    # 更新字段
    update_data = pricing_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pricing, field, value)

    await db.commit()
    await db.refresh(pricing)

    return {
        "id": str(pricing.id),
        "model": {
            "id": str(model.id),
            "model_key": model.model_key,
            "display_name": model.display_name
        },
        "input_credits_per_1k_tokens": pricing.input_credits_per_1k_tokens,
        "output_credits_per_1k_tokens": pricing.output_credits_per_1k_tokens,
        "min_credits_per_request": pricing.min_credits_per_request,
        "effective_from": pricing.effective_from,
        "effective_until": pricing.effective_until,
        "is_active": pricing.is_active,
        "created_at": pricing.created_at,
        "updated_at": pricing.updated_at
    }


@router.delete("/{pricing_id}")
async def delete_pricing_rule(
    pricing_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """删除计费规则"""
    # 查询计费规则
    result = await db.execute(
        select(AIModelPricing).where(AIModelPricing.id == pricing_id)
    )
    pricing = result.scalar_one_or_none()

    if not pricing:
        raise HTTPException(status_code=404, detail="计费规则不存在")

    # 删除计费规则
    await db.delete(pricing)
    await db.commit()

    return {"message": "计费规则已删除"}


@router.get("/model/{model_id}", response_model=PricingResponse)
async def get_model_current_pricing(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """获取模型当前生效的计费规则"""
    # 查询模型
    result = await db.execute(
        select(AIModel).where(AIModel.id == model_id)
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")

    # 查询当前生效的计费规则
    now = datetime.utcnow()
    result = await db.execute(
        select(AIModelPricing)
        .where(
            AIModelPricing.model_id == model_id,
            AIModelPricing.is_active == True,
            AIModelPricing.effective_from <= now,
            (AIModelPricing.effective_until == None) | (AIModelPricing.effective_until > now)
        )
        .order_by(AIModelPricing.effective_from.desc())
        .limit(1)
    )
    pricing = result.scalar_one_or_none()

    if not pricing:
        raise HTTPException(status_code=404, detail="该模型没有生效的计费规则")

    return {
        "id": str(pricing.id),
        "model": {
            "id": str(model.id),
            "model_key": model.model_key,
            "display_name": model.display_name
        },
        "input_credits_per_1k_tokens": pricing.input_credits_per_1k_tokens,
        "output_credits_per_1k_tokens": pricing.output_credits_per_1k_tokens,
        "min_credits_per_request": pricing.min_credits_per_request,
        "effective_from": pricing.effective_from,
        "effective_until": pricing.effective_until,
        "is_active": pricing.is_active,
        "created_at": pricing.created_at,
        "updated_at": pricing.updated_at
    }

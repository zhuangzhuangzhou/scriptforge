from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.ai_model import AIModel
from app.models.ai_model_provider import AIModelProvider
from app.models.ai_model_pricing import AIModelPricing
from app.schemas.ai_model import AIModelResponse

router = APIRouter()

@router.get("", response_model=List[dict])
async def list_available_models(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户可用的 AI 模型列表（包含计费信息）"""
    # 查询所有启用的模型及其提供商信息
    stmt = (
        select(AIModel, AIModelProvider.display_name.label("provider_name"))
        .join(AIModelProvider, AIModel.provider_id == AIModelProvider.id)
        .where(AIModel.is_enabled == True)
        .where(AIModelProvider.is_enabled == True)
    )

    result = await db.execute(stmt)
    models_with_providers = result.all()

    output = []
    for model, provider_name in models_with_providers:
        # 查询当前生效的计费规则
        pricing_stmt = (
            select(AIModelPricing)
            .where(AIModelPricing.model_id == model.id)
            .where(AIModelPricing.is_active == True)
            .order_by(AIModelPricing.effective_from.desc())
            .limit(1)
        )
        pricing_result = await db.execute(pricing_stmt)
        pricing = pricing_result.scalar_one_or_none()

        output.append({
            "id": str(model.id),
            "model_key": model.model_key,
            "display_name": model.display_name,
            "provider_name": provider_name,
            "model_type": model.model_type,
            "description": model.description,
            "is_default": model.is_default,
            "pricing": {
                "input_credits_per_1k": float(pricing.input_credits_per_1k_tokens) if pricing else 1.0,
                "output_credits_per_1k": float(pricing.output_credits_per_1k_tokens) if pricing else 1.0,
            } if pricing else None
        })

    return output

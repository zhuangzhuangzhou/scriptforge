"""模型提供商管理 API"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.ai_model_provider import AIModelProvider
from app.models.ai_model import AIModel
from app.schemas.model_provider import (
    ProviderCreate,
    ProviderUpdate,
    ProviderResponse
)
from app.api.v1.admin import check_admin

router = APIRouter()


@router.get("", response_model=List[ProviderResponse])
async def get_providers(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """获取提供商列表"""
    # 查询提供商及其模型数量
    result = await db.execute(
        select(
            AIModelProvider,
            func.count(AIModel.id).label("models_count")
        )
        .outerjoin(AIModel, AIModelProvider.id == AIModel.provider_id)
        .group_by(AIModelProvider.id)
        .order_by(AIModelProvider.created_at.desc())
    )

    providers = []
    for provider, models_count in result:
        provider_dict = {
            "id": str(provider.id),
            "provider_key": provider.provider_key,
            "display_name": provider.display_name,
            "provider_type": provider.provider_type,
            "api_endpoint": provider.api_endpoint,
            "icon_url": provider.icon_url,
            "description": provider.description,
            "is_enabled": provider.is_enabled,
            "is_system_default": provider.is_system_default,
            "models_count": models_count,
            "created_at": provider.created_at,
            "updated_at": provider.updated_at
        }
        providers.append(provider_dict)

    return providers


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """获取提供商详情"""
    # 查询提供商
    result = await db.execute(
        select(AIModelProvider).where(AIModelProvider.id == provider_id)
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")

    # 查询模型数量
    result = await db.execute(
        select(func.count(AIModel.id)).where(AIModel.provider_id == provider_id)
    )
    models_count = result.scalar() or 0

    return {
        "id": str(provider.id),
        "provider_key": provider.provider_key,
        "display_name": provider.display_name,
        "provider_type": provider.provider_type,
        "api_endpoint": provider.api_endpoint,
        "icon_url": provider.icon_url,
        "description": provider.description,
        "is_enabled": provider.is_enabled,
        "is_system_default": provider.is_system_default,
        "models_count": models_count,
        "created_at": provider.created_at,
        "updated_at": provider.updated_at
    }


@router.delete("/{provider_id}")
async def delete_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """删除提供商"""
    # 查询提供商
    result = await db.execute(
        select(AIModelProvider).where(AIModelProvider.id == provider_id)
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")

    # 检查是否有关联的模型
    result = await db.execute(
        select(func.count(AIModel.id)).where(AIModel.provider_id == provider_id)
    )
    models_count = result.scalar() or 0

    if models_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"无法删除提供商，还有 {models_count} 个关联的模型"
        )

    # 删除提供商
    await db.delete(provider)
    await db.commit()

    return {"message": "提供商已删除"}


@router.post("/{provider_id}/toggle", response_model=ProviderResponse)
async def toggle_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """启用/禁用提供商"""
    # 查询提供商
    result = await db.execute(
        select(AIModelProvider).where(AIModelProvider.id == provider_id)
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")

    # 切换状态
    provider.is_enabled = not provider.is_enabled
    await db.commit()
    await db.refresh(provider)

    # 查询模型数量
    result = await db.execute(
        select(func.count(AIModel.id)).where(AIModel.provider_id == provider_id)
    )
    models_count = result.scalar() or 0

    return {
        "id": str(provider.id),
        "provider_key": provider.provider_key,
        "display_name": provider.display_name,
        "provider_type": provider.provider_type,
        "api_endpoint": provider.api_endpoint,
        "icon_url": provider.icon_url,
        "description": provider.description,
        "is_enabled": provider.is_enabled,
        "is_system_default": provider.is_system_default,
        "models_count": models_count,
        "created_at": provider.created_at,
        "updated_at": provider.updated_at
    }


@router.post("", response_model=ProviderResponse)
async def create_provider(
    provider_data: ProviderCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """创建提供商"""
    # 检查 provider_key 是否已存在
    result = await db.execute(
        select(AIModelProvider).where(
            AIModelProvider.provider_key == provider_data.provider_key
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="提供商标识已存在")

    # 创建提供商
    provider = AIModelProvider(
        provider_key=provider_data.provider_key,
        display_name=provider_data.display_name,
        provider_type=provider_data.provider_type,
        api_endpoint=provider_data.api_endpoint,
        icon_url=provider_data.icon_url,
        description=provider_data.description
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)

    return {
        "id": str(provider.id),
        "provider_key": provider.provider_key,
        "display_name": provider.display_name,
        "provider_type": provider.provider_type,
        "api_endpoint": provider.api_endpoint,
        "icon_url": provider.icon_url,
        "description": provider.description,
        "is_enabled": provider.is_enabled,
        "is_system_default": provider.is_system_default,
        "models_count": 0,
        "created_at": provider.created_at,
        "updated_at": provider.updated_at
    }


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: str,
    provider_data: ProviderUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """更新提供商"""
    # 查询提供商
    result = await db.execute(
        select(AIModelProvider).where(AIModelProvider.id == provider_id)
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")

    # 更新字段
    update_data = provider_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(provider, field, value)

    await db.commit()
    await db.refresh(provider)

    # 查询模型数量
    result = await db.execute(
        select(func.count(AIModel.id)).where(AIModel.provider_id == provider_id)
    )
    models_count = result.scalar() or 0

    return {
        "id": str(provider.id),
        "provider_key": provider.provider_key,
        "display_name": provider.display_name,
        "provider_type": provider.provider_type,
        "api_endpoint": provider.api_endpoint,
        "icon_url": provider.icon_url,
        "description": provider.description,
        "is_enabled": provider.is_enabled,
        "is_system_default": provider.is_system_default,
        "models_count": models_count,
        "created_at": provider.created_at,
        "updated_at": provider.updated_at
    }


@router.delete("/{provider_id}")
async def delete_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """删除提供商"""
    # 查询提供商
    result = await db.execute(
        select(AIModelProvider).where(AIModelProvider.id == provider_id)
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")

    # 检查是否有关联的模型
    result = await db.execute(
        select(func.count(AIModel.id)).where(AIModel.provider_id == provider_id)
    )
    models_count = result.scalar() or 0

    if models_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"无法删除提供商，还有 {models_count} 个关联的模型"
        )

    # 删除提供商
    await db.delete(provider)
    await db.commit()

    return {"message": "提供商已删除"}


@router.post("/{provider_id}/toggle", response_model=ProviderResponse)
async def toggle_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """启用/禁用提供商"""
    # 查询提供商
    result = await db.execute(
        select(AIModelProvider).where(AIModelProvider.id == provider_id)
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")

    # 切换状态
    provider.is_enabled = not provider.is_enabled
    await db.commit()
    await db.refresh(provider)

    # 查询模型数量
    result = await db.execute(
        select(func.count(AIModel.id)).where(AIModel.provider_id == provider_id)
    )
    models_count = result.scalar() or 0

    return {
        "id": str(provider.id),
        "provider_key": provider.provider_key,
        "display_name": provider.display_name,
        "provider_type": provider.provider_type,
        "api_endpoint": provider.api_endpoint,
        "icon_url": provider.icon_url,
        "description": provider.description,
        "is_enabled": provider.is_enabled,
        "is_system_default": provider.is_system_default,
        "models_count": models_count,
        "created_at": provider.created_at,
        "updated_at": provider.updated_at
    }

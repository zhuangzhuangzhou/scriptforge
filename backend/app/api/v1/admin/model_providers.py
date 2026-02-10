"""模型提供商管理 API"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.ai_model_provider import AIModelProvider
from app.models.ai_model import AIModel
from app.schemas.model_provider import (
    ProviderCreate,
    ProviderUpdate,
    ProviderResponse
)
from app.schemas.common import (
    PaginationParams,
    PaginatedResponse,
    BatchOperationRequest,
    BatchOperationResponse,
    SuccessResponse
)
from app.api.v1.admin import check_admin
from app.api.v1.admin.helpers import (
    build_provider_response,
    get_provider_models_count,
    apply_pagination,
    calculate_total_pages
)

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[ProviderResponse],
    summary="获取提供商列表",
    description="获取所有 AI 模型提供商的列表，支持分页、排序和搜索"
)
async def get_providers(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    search: Optional[str] = Query(None, description="搜索关键词（提供商名称或标识）"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """获取提供商列表（支持分页、排序、搜索）"""
    
    # 构建基础查询
    query = select(
        AIModelProvider,
        func.count(AIModel.id).label("models_count")
    ).outerjoin(
        AIModel, AIModelProvider.id == AIModel.provider_id
    ).group_by(AIModelProvider.id)
    
    # 添加搜索条件
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                AIModelProvider.provider_key.ilike(search_pattern),
                AIModelProvider.display_name.ilike(search_pattern)
            )
        )
    
    # 获取总数
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 添加排序
    if hasattr(AIModelProvider, sort_by):
        order_column = getattr(AIModelProvider, sort_by)
        if sort_order == "desc":
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())
    else:
        query = query.order_by(AIModelProvider.created_at.desc())
    
    # 应用分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # 执行查询
    result = await db.execute(query)
    
    # 构建响应
    providers = []
    for provider, models_count in result:
        providers.append(build_provider_response(provider, models_count))
    
    return {
        "items": providers,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": calculate_total_pages(total, page_size)
    }


@router.get(
    "/{provider_id}",
    response_model=ProviderResponse,
    summary="获取提供商详情",
    description="根据 ID 获取提供商的详细信息"
)
async def get_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """获取提供商详情"""
    result = await db.execute(
        select(AIModelProvider).where(AIModelProvider.id == provider_id)
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")

    models_count = await get_provider_models_count(db, provider_id)
    return build_provider_response(provider, models_count)


@router.post(
    "",
    response_model=ProviderResponse,
    summary="创建提供商",
    description="创建新的 AI 模型提供商"
)
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

    return build_provider_response(provider, 0)


@router.put(
    "/{provider_id}",
    response_model=ProviderResponse,
    summary="更新提供商",
    description="更新提供商的信息"
)
async def update_provider(
    provider_id: str,
    provider_data: ProviderUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """更新提供商"""
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

    models_count = await get_provider_models_count(db, provider_id)
    return build_provider_response(provider, models_count)


@router.delete(
    "/{provider_id}",
    response_model=SuccessResponse,
    summary="删除提供商",
    description="删除指定的提供商（如果有关联模型则无法删除）"
)
async def delete_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """删除提供商"""
    result = await db.execute(
        select(AIModelProvider).where(AIModelProvider.id == provider_id)
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")

    # 检查是否有关联的模型
    models_count = await get_provider_models_count(db, provider_id)
    if models_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"无法删除提供商，还有 {models_count} 个关联的模型"
        )

    # 保存提供商信息用于响应
    provider_info = {
        "provider_key": provider.provider_key,
        "display_name": provider.display_name
    }

    # 删除提供商
    await db.delete(provider)
    await db.commit()

    return {
        "success": True,
        "message": f"提供商 '{provider_info['display_name']}' 已删除",
        "data": provider_info
    }


@router.post(
    "/{provider_id}/toggle",
    response_model=ProviderResponse,
    summary="启用/禁用提供商",
    description="切换提供商的启用状态"
)
async def toggle_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """启用/禁用提供商"""
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

    models_count = await get_provider_models_count(db, provider_id)
    return build_provider_response(provider, models_count)


@router.post(
    "/batch/toggle",
    response_model=BatchOperationResponse,
    summary="批量启用/禁用提供商",
    description="批量切换多个提供商的启用状态"
)
async def batch_toggle_providers(
    request: BatchOperationRequest,
    enable: bool = Query(..., description="true=启用, false=禁用"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """批量启用/禁用提供商"""
    success_count = 0
    failed_count = 0
    failed_ids = []

    for provider_id in request.ids:
        try:
            result = await db.execute(
                select(AIModelProvider).where(AIModelProvider.id == provider_id)
            )
            provider = result.scalar_one_or_none()
            
            if provider:
                provider.is_enabled = enable
                success_count += 1
            else:
                failed_count += 1
                failed_ids.append(provider_id)
        except Exception as e:
            failed_count += 1
            failed_ids.append(provider_id)
            print(f"批量操作失败: {provider_id}, 错误: {str(e)}")

    await db.commit()

    action = "启用" if enable else "禁用"
    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "failed_ids": failed_ids,
        "message": f"批量{action}完成：成功 {success_count} 个，失败 {failed_count} 个"
    }


@router.delete(
    "/batch",
    response_model=BatchOperationResponse,
    summary="批量删除提供商",
    description="批量删除多个提供商（有关联模型的提供商会跳过）"
)
async def batch_delete_providers(
    request: BatchOperationRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """批量删除提供商"""
    success_count = 0
    failed_count = 0
    failed_ids = []

    for provider_id in request.ids:
        try:
            result = await db.execute(
                select(AIModelProvider).where(AIModelProvider.id == provider_id)
            )
            provider = result.scalar_one_or_none()
            
            if not provider:
                failed_count += 1
                failed_ids.append(provider_id)
                continue
            
            # 检查是否有关联的模型
            models_count = await get_provider_models_count(db, provider_id)
            if models_count > 0:
                failed_count += 1
                failed_ids.append(provider_id)
                continue
            
            await db.delete(provider)
            success_count += 1
        except Exception as e:
            failed_count += 1
            failed_ids.append(provider_id)
            print(f"批量删除失败: {provider_id}, 错误: {str(e)}")

    await db.commit()

    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "failed_ids": failed_ids,
        "message": f"批量删除完成：成功 {success_count} 个，失败 {failed_count} 个"
    }

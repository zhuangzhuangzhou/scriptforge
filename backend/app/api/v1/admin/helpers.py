"""管理接口辅助函数"""
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.ai_model_provider import AIModelProvider
from app.models.ai_model import AIModel


def build_provider_response(provider: AIModelProvider, models_count: int = 0) -> Dict[str, Any]:
    """构建提供商响应数据
    
    Args:
        provider: 提供商对象
        models_count: 关联的模型数量
        
    Returns:
        提供商响应字典
    """
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


async def get_provider_models_count(db: AsyncSession, provider_id: str) -> int:
    """获取提供商的模型数量
    
    Args:
        db: 数据库会话
        provider_id: 提供商 ID
        
    Returns:
        模型数量
    """
    result = await db.execute(
        select(func.count(AIModel.id)).where(AIModel.provider_id == provider_id)
    )
    return result.scalar() or 0


def build_model_response(model: AIModel, provider_name: str) -> Dict[str, Any]:
    """构建模型响应数据
    
    Args:
        model: 模型对象
        provider_name: 提供商名称
        
    Returns:
        模型响应字典
    """
    return {
        "id": str(model.id),
        "provider_id": str(model.provider_id),
        "provider_name": provider_name,
        "model_key": model.model_key,
        "display_name": model.display_name,
        "model_type": model.model_type,
        "max_tokens": model.max_tokens,
        "max_input_tokens": model.max_input_tokens,
        "max_output_tokens": model.max_output_tokens,
        "timeout_seconds": model.timeout_seconds,
        "temperature_default": model.temperature_default,
        "supports_streaming": model.supports_streaming,
        "supports_function_calling": model.supports_function_calling,
        "description": model.description,
        "is_enabled": model.is_enabled,
        "is_default": model.is_default,
        "created_at": model.created_at,
        "updated_at": model.updated_at
    }


def apply_pagination(query, pagination_params):
    """应用分页参数到查询
    
    Args:
        query: SQLAlchemy 查询对象
        pagination_params: 分页参数
        
    Returns:
        应用分页后的查询对象
    """
    offset = (pagination_params.page - 1) * pagination_params.page_size
    return query.offset(offset).limit(pagination_params.page_size)


def calculate_total_pages(total: int, page_size: int) -> int:
    """计算总页数
    
    Args:
        total: 总记录数
        page_size: 每页大小
        
    Returns:
        总页数
    """
    return (total + page_size - 1) // page_size

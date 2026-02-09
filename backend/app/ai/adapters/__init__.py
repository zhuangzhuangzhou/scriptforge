from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.adapters.base import BaseModelAdapter
from app.ai.adapters.openai_adapter import OpenAIAdapter
from app.ai.adapters.anthropic_adapter import AnthropicAdapter
from app.ai.adapters.model_config_service import ModelConfigService
from app.core.config import settings

__all__ = ["BaseModelAdapter", "OpenAIAdapter", "AnthropicAdapter", "get_adapter"]

# 默认模型提供商，可在配置中覆盖
DEFAULT_MODEL_PROVIDER = getattr(settings, 'DEFAULT_MODEL_PROVIDER', 'openai')


async def get_adapter(
    provider: Optional[str] = None,
    model_id: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Optional[AsyncSession] = None
) -> BaseModelAdapter:
    """
    获取模型适配器实例

    根据配置返回对应的模型适配器。优先从数据库读取配置，如果数据库中没有配置则降级到环境变量。

    Args:
        provider: 模型提供商，可选值为 "openai" 或 "anthropic"
                  如果为 None，则使用默认配置
        model_id: 模型ID（UUID），如果指定则使用该模型
        user_id: 用户ID，用于获取用户自定义 API Key
        db: 数据库会话，如果提供则从数据库读取配置

    Returns:
        BaseModelAdapter: 模型适配器实例
    """
    # 1. 尝试从数据库获取配置
    if db:
        config_service = ModelConfigService(db)
        config = await config_service.get_model_config(
            provider_key=provider,
            model_id=model_id,
            user_id=user_id
        )

        if config:
            # 使用数据库配置创建适配器
            provider_type = config["provider_type"]

            if provider_type == "anthropic" or config["provider_key"] == "anthropic":
                return AnthropicAdapter(
                    api_key=config["api_key"],
                    model_name=config["model_key"]
                )
            else:
                # 默认使用 OpenAI 兼容适配器
                return OpenAIAdapter(
                    api_key=config["api_key"],
                    model_name=config["model_key"]
                )

    # 2. 降级到环境变量配置（向后兼容）
    use_provider = provider or DEFAULT_MODEL_PROVIDER

    if use_provider == "anthropic":
        api_key = settings.ANTHROPIC_API_KEY
        model_name = settings.ANTHROPIC_MODEL
        return AnthropicAdapter(api_key=api_key, model_name=model_name)
    else:
        # 默认使用 OpenAI
        api_key = settings.OPENAI_API_KEY
        model_name = settings.OPENAI_MODEL
        return OpenAIAdapter(api_key=api_key, model_name=model_name)

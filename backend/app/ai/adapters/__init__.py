from typing import Optional
from app.ai.adapters.base import BaseModelAdapter
from app.ai.adapters.openai_adapter import OpenAIAdapter
from app.ai.adapters.anthropic_adapter import AnthropicAdapter
from app.core.config import settings

__all__ = ["BaseModelAdapter", "OpenAIAdapter", "AnthropicAdapter", "get_adapter"]

# 默认模型提供商，可在配置中覆盖
DEFAULT_MODEL_PROVIDER = getattr(settings, 'DEFAULT_MODEL_PROVIDER', 'openai')


async def get_adapter(provider: Optional[str] = None) -> BaseModelAdapter:
    """
    获取模型适配器实例

    根据配置返回对应的模型适配器

    Args:
        provider: 模型提供商，可选值为 "openai" 或 "anthropic"
                  如果为 None，则使用默认配置

    Returns:
        BaseModelAdapter: 模型适配器实例
    """
    # 确定使用哪个提供商
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

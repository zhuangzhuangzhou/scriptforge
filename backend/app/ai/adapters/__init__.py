from app.ai.adapters.base import BaseModelAdapter
from app.ai.adapters.openai_adapter import OpenAIAdapter
from app.core.config import settings

__all__ = ["BaseModelAdapter", "OpenAIAdapter", "get_adapter"]


async def get_adapter() -> BaseModelAdapter:
    """
    获取模型适配器实例

    根据配置返回对应的模型适配器
    """
    # 从配置中读取 API Key 和模型名称
    api_key = settings.OPENAI_API_KEY
    model_name = settings.OPENAI_MODEL

    return OpenAIAdapter(api_key=api_key, model_name=model_name)

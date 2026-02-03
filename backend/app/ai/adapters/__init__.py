from app.ai.adapters.base import BaseModelAdapter
from app.ai.adapters.openai_adapter import OpenAIAdapter

__all__ = ["BaseModelAdapter", "OpenAIAdapter", "get_adapter"]


async def get_adapter() -> BaseModelAdapter:
    """
    获取模型适配器实例

    根据配置返回对应的模型适配器
    """
    # TODO: 根据配置选择适配器
    # 目前返回 OpenAIAdapter，后续可以扩展支持其他模型
    return OpenAIAdapter()

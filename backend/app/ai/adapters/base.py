from abc import ABC, abstractmethod
from typing import Dict, Any, Iterator


class BaseModelAdapter(ABC):
    """模型适配器基类"""

    def __init__(self, api_key: str, model_name: str, **kwargs):
        self.api_key = api_key
        self.model_name = model_name
        self.config = kwargs

    @abstractmethod
    def generate(self, prompt: str, return_usage: bool = False, **kwargs) -> Any:
        """
        生成文本
        :param prompt: 提示词
        :param return_usage: 是否返回使用量信息
        :return: 字符串（默认）或包含内容和使用量的字典
        """
        pass

    @abstractmethod
    def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
        """流式生成文本"""
        pass

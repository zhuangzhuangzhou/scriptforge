from typing import Iterator
from anthropic import Anthropic
from app.ai.adapters.base import BaseModelAdapter


class AnthropicAdapter(BaseModelAdapter):
    """Anthropic Claude模型适配器"""

    def __init__(self, api_key: str, model_name: str = "claude-3-opus-20240229", **kwargs):
        super().__init__(api_key, model_name, **kwargs)
        self.client = Anthropic(api_key=api_key)

    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 2000)

        message = self.client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )

        # Anthropic 返回的是 content blocks 列表
        return message.content[0].text

    def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
        """流式生成文本"""
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 2000)

        with self.client.messages.stream(
            model=self.model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                yield text

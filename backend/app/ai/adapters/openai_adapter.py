from typing import Iterator, Any
from openai import OpenAI
from app.ai.adapters.base import BaseModelAdapter


class OpenAIAdapter(BaseModelAdapter):
    """OpenAI模型适配器"""

    def __init__(self, api_key: str, model_name: str = "gpt-4-turbo-preview", **kwargs):
        super().__init__(api_key, model_name, **kwargs)
        # 设置较长的超时时间（120秒），适应大模型响应时间
        self.client = OpenAI(api_key=api_key, timeout=120.0)

    def generate(self, prompt: str, return_usage: bool = False, **kwargs) -> Any:
        """生成文本"""
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 2000)

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )

        content = response.choices[0].message.content

        if return_usage:
            return {
                "content": content,
                "usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                }
            }

        return content

    def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
        """流式生成文本"""
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 2000)

        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

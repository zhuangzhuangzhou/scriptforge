import time
from typing import Iterator, Any
from anthropic import Anthropic
from app.ai.adapters.base import BaseModelAdapter


class AnthropicAdapter(BaseModelAdapter):
    """Anthropic Claude模型适配器"""

    provider_name = "anthropic"

    def __init__(self, api_key: str, model_name: str = "claude-3-opus-20240229", base_url: str = None, **kwargs):
        super().__init__(api_key, model_name, **kwargs)
        # 如果提供了 base_url，使用自定义端点（如 MiniMax）
        if base_url:
            self.client = Anthropic(api_key=api_key, base_url=base_url)
        else:
            self.client = Anthropic(api_key=api_key)

    def generate(self, prompt: str, return_usage: bool = False, **kwargs) -> Any:
        """生成文本"""
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 2000)

        # 构建原始请求（用于日志）
        request_body = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }

        start_time = time.time()
        error_msg = None
        response_content = None
        prompt_tokens = None
        response_tokens = None
        raw_response = None

        try:
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            # 保存原始响应对象
            raw_response = message.model_dump()

            # Anthropic 返回的是 content blocks 列表
            response_content = message.content[0].text
            prompt_tokens = message.usage.input_tokens
            response_tokens = message.usage.output_tokens

            if return_usage:
                return {
                    "content": response_content,
                    "usage": {
                        "input_tokens": prompt_tokens,
                        "output_tokens": response_tokens
                    }
                }

            return response_content

        except Exception as e:
            error_msg = str(e)
            raise

        finally:
            latency_ms = int((time.time() - start_time) * 1000)
            self._log_call(
                prompt=prompt,
                response=response_content,
                prompt_tokens=prompt_tokens,
                response_tokens=response_tokens,
                temperature=temperature,
                max_tokens=max_tokens,
                latency_ms=latency_ms,
                status="error" if error_msg else "success",
                error_message=error_msg,
                metadata={
                    "request": request_body,
                    "response": raw_response,
                    "stream": False
                }
            )

    def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
        """流式生成文本"""
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 2000)

        # 构建原始请求（用于日志）
        request_body = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True
        }

        start_time = time.time()
        collected_content = []
        error_msg = None
        raw_response = None

        try:
            with self.client.messages.stream(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    collected_content.append(text)
                    yield text

            # 流结束后构建完整响应
            raw_response = {
                "id": "stream-complete",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "".join(collected_content)}],
                "model": self.model_name,
                "usage": None  # 流式响应不包含 usage
            }

        except Exception as e:
            error_msg = str(e)
            raise

        finally:
            latency_ms = int((time.time() - start_time) * 1000)
            full_response = "".join(collected_content)
            self._log_call(
                prompt=prompt,
                response=full_response if full_response else None,
                temperature=temperature,
                max_tokens=max_tokens,
                latency_ms=latency_ms,
                status="error" if error_msg else "success",
                error_message=error_msg,
                metadata={
                    "request": request_body,
                    "response": raw_response,
                    "stream": True
                }
            )

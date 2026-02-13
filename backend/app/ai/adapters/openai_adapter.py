import time
from typing import Iterator, Any
from openai import OpenAI
from app.ai.adapters.base import BaseModelAdapter


class OpenAIAdapter(BaseModelAdapter):
    """OpenAI模型适配器"""

    provider_name = "openai"

    def __init__(self, api_key: str, model_name: str = "gpt-4-turbo-preview", **kwargs):
        super().__init__(api_key, model_name, **kwargs)
        # 设置较长的超时时间（120秒），适应大模型响应时间
        self.client = OpenAI(api_key=api_key, timeout=120.0)

    def generate(self, prompt: str, return_usage: bool = False, **kwargs) -> Any:
        """生成文本"""
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 2000)

        # 构建原始请求（用于日志）
        request_body = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        start_time = time.time()
        error_msg = None
        response_content = None
        prompt_tokens = None
        response_tokens = None
        raw_response = None

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )

            # 保存原始响应对象
            raw_response = response.model_dump()

            response_content = response.choices[0].message.content
            prompt_tokens = response.usage.prompt_tokens
            response_tokens = response.usage.completion_tokens

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
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        start_time = time.time()
        collected_content = []
        error_msg = None
        raw_response = None

        try:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    collected_content.append(content)
                    yield content

            # 流结束后获取完整响应
            raw_response = {
                "model": self.model_name,
                "choices": [{"message": {"content": "".join(collected_content)}}],
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

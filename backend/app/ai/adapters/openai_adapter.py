"""OpenAI 模型适配器

提供与 OpenAI API 交互的功能，包括：
- 文本生成（非流式）
- 流式响应
- 完善的错误处理和空值检查
"""
import time
import logging
from typing import Iterator, Any, Optional
from openai import OpenAI
from app.ai.adapters.base import BaseModelAdapter

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseModelAdapter):
    """OpenAI 模型适配器

    特性：
    - 完善的空值检查，确保不会因为 None 值崩溃
    - 流式响应支持
    - 自动日志记录
    """

    provider_name = "openai"

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4-turbo-preview",
        base_url: Optional[str] = None,
        **kwargs
    ):
        """初始化适配器

        Args:
            api_key: OpenAI API Key
            model_name: 模型名称
            base_url: 自定义 API 端点（可选）
            **kwargs: 其他参数
        """
        super().__init__(api_key, model_name, **kwargs)
        # 设置较长的超时时间（120秒），适应大模型响应时间
        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0)
        else:
            self.client = OpenAI(api_key=api_key, timeout=120.0)

    def generate(self, prompt: str, return_usage: bool = False, **kwargs) -> Any:
        """生成文本（非流式）

        Args:
            prompt: 提示词
            return_usage: 是否返回 token 使用量
            **kwargs: 其他参数（temperature, max_tokens 等）

        Returns:
            生成的文本，或包含文本和使用量的字典
        """
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 100000)

        system_prompt = kwargs.get('system_prompt')
        messages = [{"role": "user", "content": prompt}]
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        # 构建原始请求（用于日志）
        request_body = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        start_time = time.time()
        error_msg = None
        response_content = ""
        prompt_tokens = None
        response_tokens = None
        raw_response = None

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # 保存原始响应对象（安全处理）
            try:
                raw_response = response.model_dump() if hasattr(response, 'model_dump') else None
            except Exception:
                raw_response = None

            # 安全提取响应内容
            response_content = self._safe_extract_content(response)

            # 安全提取 token 使用量
            if hasattr(response, 'usage') and response.usage:
                prompt_tokens = getattr(response.usage, 'prompt_tokens', None)
                response_tokens = getattr(response.usage, 'completion_tokens', None)

            if return_usage:
                return {
                    "content": response_content,
                    "usage": {
                        "input_tokens": prompt_tokens or 0,
                        "output_tokens": response_tokens or 0
                    }
                }

            return response_content

        except Exception as e:
            error_msg = str(e)
            logger.error(f"OpenAI generate 错误: {error_msg}")
            raise

        finally:
            latency_ms = int((time.time() - start_time) * 1000)
            self._log_call(
                prompt=prompt,
                response=response_content if response_content else None,
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
        """流式生成文本

        Args:
            prompt: 提示词
            **kwargs: 其他参数（temperature, max_tokens 等）

        Yields:
            流式响应的每个文本块
        """
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 100000)

        system_prompt = kwargs.get('system_prompt')
        messages = [{"role": "user", "content": prompt}]
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        # 构建原始请求（用于日志）
        request_body = {
            "model": self.model_name,
            "messages": messages,
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
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            for chunk in stream:
                # 完整的空值检查链
                content = self._safe_extract_stream_chunk(chunk)
                if content:
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
            logger.error(f"OpenAI stream_generate 错误: {error_msg}")
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

    def _safe_extract_content(self, response) -> str:
        """安全提取非流式响应内容

        Args:
            response: OpenAI API 响应对象

        Returns:
            提取的文本内容，如果提取失败返回空字符串
        """
        try:
            if response is None:
                return ""

            choices = getattr(response, 'choices', None)
            if not choices or not isinstance(choices, (list, tuple)) or len(choices) == 0:
                return ""

            first_choice = choices[0]
            if first_choice is None:
                return ""

            message = getattr(first_choice, 'message', None)
            if message is None:
                return ""

            content = getattr(message, 'content', None)
            return content if content else ""

        except Exception as e:
            logger.warning(f"提取 OpenAI 响应内容失败: {e}")
            return ""

    def _safe_extract_stream_chunk(self, chunk) -> Optional[str]:
        """安全提取流式响应块内容

        Args:
            chunk: 流式响应块

        Returns:
            提取的文本内容，如果提取失败返回 None
        """
        try:
            if chunk is None:
                return None

            choices = getattr(chunk, 'choices', None)
            if not choices or not isinstance(choices, (list, tuple)) or len(choices) == 0:
                return None

            first_choice = choices[0]
            if first_choice is None:
                return None

            delta = getattr(first_choice, 'delta', None)
            if delta is None:
                return None

            content = getattr(delta, 'content', None)
            return content if content else None

        except Exception as e:
            logger.warning(f"提取 OpenAI 流式块内容失败: {e}")
            return None

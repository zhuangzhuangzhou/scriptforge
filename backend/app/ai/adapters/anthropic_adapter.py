"""Anthropic Claude 模型适配器

提供与 Anthropic API 交互的功能，包括：
- 文本生成（非流式）
- 流式响应
- 完善的错误处理和空值检查
"""
import time
import logging
import json
import httpx
from typing import Iterator, Any, Optional
from anthropic import Anthropic
from app.ai.adapters.base import BaseModelAdapter

logger = logging.getLogger(__name__)


class AnthropicAdapter(BaseModelAdapter):
    """Anthropic Claude 模型适配器

    特性：
    - 完善的空值检查，确保不会因为 None 值崩溃
    - 流式响应支持
    - 自动日志记录
    """

    provider_name = "anthropic"

    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-3-opus-20240229",
        base_url: Optional[str] = None,
        **kwargs
    ):
        """初始化适配器

        Args:
            api_key: Anthropic API Key
            model_name: 模型名称
            base_url: 自定义 API 端点（可选，可以只填写域名如 https://api.autocode.space）
            **kwargs: 其他参数
        """
        super().__init__(api_key, model_name, **kwargs)

        # 处理 base_url：自动补全路径
        if base_url:
            base_url = base_url.rstrip('/')
            # 检查是否已经是完整路径
            if '/v1' not in base_url and '/anthropic' not in base_url:
                # 尝试自动补全路径
                # 常见的第三方代理可能使用 /anthropic/v1 或 /v1
                # 这里默认使用 /v1 路径
                if 'anthropic' in base_url.lower():
                    # 如果域名包含 anthropic，尝试 /anthropic/v1
                    test_url = f"{base_url}/anthropic/v1/messages"
                else:
                    # 其他情况默认使用 /v1/messages
                    test_url = f"{base_url}/v1/messages"

                # 检测哪个路径有效（只检测，不保存）
                # 用户可以手动提供完整路径来避免自动检测
                self.base_url = base_url
            else:
                self.base_url = base_url
        else:
            self.base_url = "https://api.anthropic.com"

        # 如果提供了 base_url，使用自定义端点
        if base_url:
            self.client = Anthropic(api_key=api_key, base_url=self.base_url)
        else:
            self.client = Anthropic(api_key=api_key)
        # 创建 httpx 客户端用于原始流式请求
        self.http_client = httpx.Client(timeout=600.0)

    def generate(self, prompt: str, return_usage: bool = False, **kwargs) -> Any:
        """生成文本（流式请求，非流式返回完整内容）

        Anthropic SDK 对于长时间操作（>10分钟）必须使用 stream=True，
        但我们仍然收集完整响应后返回。

        Args:
            prompt: 提示词
            return_usage: 是否返回 token 使用量
            **kwargs: 其他参数（temperature, max_tokens 等）

        Returns:
            生成的文本，或包含文本和使用量的字典
        """
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 100000)

        # 构建原始请求（用于日志）
        request_body = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }

        start_time = time.time()
        error_msg = None
        response_content = ""
        prompt_tokens = None
        response_tokens = None
        raw_response = None
        collected_content = []

        try:
            # Anthropic SDK 长时间操作必须使用 stream=True
            stream = self.client.messages.stream(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            # stream() 返回一个上下文管理器，需要迭代获取内容
            with stream as event_stream:
                # 遍历所有事件
                for event in event_stream:
                    if event.type == "content_block_delta":
                        # 提取文本增量
                        delta = event.delta
                        if hasattr(delta, 'text') and delta.text:
                            text = delta.text
                            collected_content.append(text)
                    elif event.type == "message_start":
                        # 消息开始，可以获取 usage
                        if hasattr(event, 'message') and event.message:
                            msg = event.message
                            if hasattr(msg, 'usage') and msg.usage:
                                usage = msg.usage
                                prompt_tokens = getattr(usage, 'input_tokens', None)
                                response_tokens = getattr(usage, 'output_tokens', None)
                    elif event.type == "message_delta":
                        # 消息增量，可能包含 usage
                        if hasattr(event, 'usage') and event.usage:
                            usage = event.usage
                            # 累积输出 tokens
                            current_output = getattr(usage, 'output_tokens', None)
                            if current_output:
                                response_tokens = current_output
                    elif event.type == "message_stop":
                        # 消息结束
                        pass

            # 收集完整响应
            response_content = "".join(collected_content)

            # 构建 raw_response（用于日志）
            raw_response = {
                "content": response_content,
                "usage": {
                    "input_tokens": prompt_tokens or 0,
                    "output_tokens": response_tokens or 0
                }
            }

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
            logger.error(f"Anthropic generate 错误: {error_msg}")
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
        """流式生成文本（使用原始 HTTP 请求，绕过 SDK bug）

        Args:
            prompt: 提示词
            **kwargs: 其他参数（temperature, max_tokens 等）

        Yields:
            流式响应的每个文本块
        """
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 100000)

        # 构建请求体
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

        try:
            # 构建 API URL：根据 base_url 自动适配路径
            base = self.base_url.rstrip('/')
            # 检查 base_url 是否已经是完整路径
            if '/v1' in base or '/messages' in base:
                # 用户提供了完整路径，直接使用
                url = base
            else:
                # 用户只提供了域名，自动补全路径
                # 常见的 Anthropic 兼容 API 路径格式
                if 'anthropic' in base.lower():
                    url = f"{base}/anthropic/v1/messages"
                else:
                    url = f"{base}/v1/messages"

            logger.info(f"Anthropic API URL: {url}")

            # 支持两种认证方式：Bearer token（第三方代理）和 x-api-key（官方 API）
            headers = {
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }

            # 如果是自定义端点（第三方代理），使用 Bearer token
            if url and "anthropic.com" not in url:
                headers["Authorization"] = f"Bearer {self.api_key}"
            else:
                headers["x-api-key"] = self.api_key

            with self.http_client.stream("POST", url, json=request_body, headers=headers) as response:
                response.raise_for_status()

                # 处理 SSE 流
                for line in response.iter_lines():
                    if not line:
                        continue

                    # SSE 格式: "event: xxx" 或 "data: {...}"
                    if line.startswith("data: "):
                        data_str = line[6:]  # 去掉 "data: " 前缀
                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            # 提取文本内容
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                text = delta.get("text", "")
                                if text:
                                    collected_content.append(text)
                                    yield text
                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP 错误 {e.response.status_code}: {e.response.text[:500]}"
            logger.error(f"Anthropic stream_generate HTTP 错误: {error_msg}")
            raise Exception(error_msg) from e

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Anthropic stream_generate 错误: {error_msg}")
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
                    "response": {"content": full_response} if full_response else None,
                    "stream": True
                }
            )

    def _safe_extract_content(self, message) -> str:
        """安全提取非流式响应内容

        Anthropic 返回的是 content blocks 列表，需要安全提取文本。

        Args:
            message: Anthropic API 响应对象

        Returns:
            提取的文本内容，如果提取失败返回空字符串
        """
        try:
            if message is None:
                return ""

            content = getattr(message, 'content', None)
            if not content:
                return ""

            # content 是一个列表
            if not isinstance(content, (list, tuple)) or len(content) == 0:
                return ""

            # 提取所有文本块
            texts = []
            for block in content:
                if block is None:
                    continue

                # 尝试从对象属性获取
                if hasattr(block, 'text'):
                    text = getattr(block, 'text', None)
                    if text:
                        texts.append(text)
                # 尝试从字典获取
                elif isinstance(block, dict) and 'text' in block:
                    text = block.get('text')
                    if text:
                        texts.append(text)

            return "".join(texts)

        except Exception as e:
            logger.warning(f"提取 Anthropic 响应内容失败: {e}")
            return ""

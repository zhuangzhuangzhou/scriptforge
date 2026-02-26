"""Google Gemini API 适配器

提供与 Gemini API 交互的功能，包括：
- 文本生成
- 流式响应
- 函数调用
- 多模态输入支持
"""
import httpx
import json
from typing import Dict, Any, List, Iterator
from app.ai.adapters.base import BaseModelAdapter


class GeminiAdapter(BaseModelAdapter):
    """Gemini API 适配器"""

    provider_name = "google_gemini"

    def __init__(
        self,
        api_key: str,
        api_endpoint: str = None,
        model: str = "gemini-1.5-pro",
        model_name: str = None,
        base_url: str = None,  # 兼容 OpenAI 风格的 base_url
        **kwargs
    ):
        """初始化适配器

        Args:
            api_key: Google API Key
            api_endpoint: API 端点
            model: 模型名称（优先使用）
            model_name: 模型名称（兼容旧参数）
            base_url: 兼容 OpenAI 风格的 API 端点
            **kwargs: 其他参数
        """
        # 优先使用 base_url（兼容 OpenAI 风格），其次是 api_endpoint，最后是默认
        endpoint = base_url or api_endpoint or "https://generativelanguage.googleapis.com"

        # 先调用父类 __init__，设置 model_name 等基础属性
        super().__init__(api_key=api_key, model_name=model_name or model, **kwargs)

        self.api_endpoint = endpoint.rstrip('/')
        # 使用同步客户端，支持流式响应
        self.client = httpx.Client(timeout=60.0)

    def _build_url(self, endpoint: str) -> str:
        """构建完整的 API URL"""
        return f"{self.api_endpoint}/v1beta/models/{self.model_name}:{endpoint}?key={self.api_key}"

    def _convert_messages_to_gemini_format(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """将标准消息格式转换为 Gemini 格式

        Args:
            messages: 标准格式的消息列表
                [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

        Returns:
            Gemini 格式的请求体
        """
        contents = []
        system_instruction = None

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                # Gemini 使用 systemInstruction 字段
                system_instruction = {"parts": [{"text": content}]}
            elif role == "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif role == "assistant":
                contents.append({
                    "role": "model",  # Gemini 使用 "model" 而不是 "assistant"
                    "parts": [{"text": content}]
                })

        result = {"contents": contents}
        if system_instruction:
            result["systemInstruction"] = system_instruction

        return result

    def generate(
        self,
        prompt: str,
        return_usage: bool = False,
        **kwargs
    ) -> Any:
        """生成内容（非流式）

        Args:
            prompt: 提示词
            return_usage: 是否返回使用量信息
            **kwargs: 其他参数

        Returns:
            生成的文本或包含文本和使用量的字典
        """
        system_prompt = kwargs.get('system_prompt')
        messages = [{"role": "user", "content": prompt}]
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 100000)

        url = self._build_url("generateContent")

        # 构建请求体
        request_body = self._convert_messages_to_gemini_format(messages)
        request_body["generationConfig"] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }

        # 添加其他配置
        if "top_p" in kwargs:
            request_body["generationConfig"]["topP"] = kwargs["top_p"]
        if "top_k" in kwargs:
            request_body["generationConfig"]["topK"] = kwargs["top_k"]

        # 发送请求
        response = self.client.post(url, json=request_body)
        response.raise_for_status()

        response_data = response.json()
        text = self.extract_text_from_response(response_data)

        if return_usage:
            usage = self.get_usage_info(response_data)
            return {
                "content": text,
                "usage": {
                    "input_tokens": usage["prompt_tokens"],
                    "output_tokens": usage["completion_tokens"]
                }
            }

        return text

    def generate_content_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 100000,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """生成内容（流式）

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大输出 tokens
            **kwargs: 其他参数

        Yields:
            流式响应的每个块
        """
        # Gemini 流式 API 需要添加 alt=sse 参数
        url = self._build_url("streamGenerateContent") + "&alt=sse"

        # 构建请求体
        request_body = self._convert_messages_to_gemini_format(messages)
        request_body["generationConfig"] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }

        # 发送流式请求
        with self.client.stream("POST", url, json=request_body) as response:
            response.raise_for_status()

            # Gemini SSE 格式: data: {...json...}
            for line in response.iter_lines():
                if not line:
                    continue

                # SSE 格式处理
                if line.startswith("data: "):
                    json_str = line[6:]  # 去掉 "data: " 前缀
                    try:
                        chunk = json.loads(json_str)
                        yield chunk
                    except json.JSONDecodeError:
                        continue
                elif line.strip() and not line.startswith(":"):
                    # 尝试直接解析（非 SSE 格式的备用方案）
                    try:
                        chunk = json.loads(line)
                        yield chunk
                    except json.JSONDecodeError:
                        continue

    def extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """从响应中提取文本内容

        Args:
            response: Gemini API 响应

        Returns:
            提取的文本
        """
        try:
            candidates = response.get("candidates", [])
            if not candidates:
                return ""

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])

            # 合并所有文本部分
            texts = [part.get("text", "") for part in parts if "text" in part]
            return "".join(texts)
        except (KeyError, IndexError):
            return ""

    def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
        """流式生成文本

        Args:
            prompt: 提示词
            **kwargs: 其他参数（temperature, max_tokens 等）

        Yields:
            流式响应的每个文本块
        """
        import time

        system_prompt = kwargs.get('system_prompt')
        # 将 prompt 转换为消息格式
        messages = [{"role": "user", "content": prompt}]
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        temperature = kwargs.pop('temperature', 0.7)
        max_tokens = kwargs.pop('max_tokens', 100000)

        start_time = time.time()
        collected_content = []
        error_msg = None
        prompt_tokens = None
        response_tokens = None
        last_usage = None

        try:
            # 调用流式生成方法
            for chunk in self.generate_content_stream(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            ):
                text = self.extract_text_from_response(chunk)
                if text:
                    collected_content.append(text)
                    yield text

                # 提取 token 统计（Gemini 在每个 chunk 中都可能包含 usageMetadata）
                usage = chunk.get("usageMetadata")
                if usage:
                    last_usage = usage
                    prompt_tokens = usage.get("promptTokenCount")
                    response_tokens = usage.get("candidatesTokenCount")

        except Exception as e:
            error_msg = str(e)
            raise

        finally:
            latency_ms = int((time.time() - start_time) * 1000)
            full_response = "".join(collected_content)

            # 记录日志
            self._log_call_sync(
                prompt=prompt,
                response=full_response if full_response else None,
                prompt_tokens=prompt_tokens,
                response_tokens=response_tokens,
                temperature=temperature,
                max_tokens=max_tokens,
                latency_ms=latency_ms,
                status="error" if error_msg else "success",
                error_message=error_msg,
                metadata={
                    "request": {
                        "model": self.model_name,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    "response": {
                        "content": full_response,
                        "usage": last_usage
                    } if full_response else None,
                    "stream": True
                }
            )

    def get_usage_info(self, response: Dict[str, Any]) -> Dict[str, int]:
        """获取 token 使用信息

        Args:
            response: Gemini API 响应

        Returns:
            使用信息字典
        """
        usage_metadata = response.get("usageMetadata", {})
        return {
            "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
            "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
            "total_tokens": usage_metadata.get("totalTokenCount", 0),
        }

    def close(self):
        """关闭客户端"""
        self.client.close()

    def __enter__(self):
        """同步上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """同步上下文管理器退出"""
        self.close()


# 使用示例
def example_usage():
    """使用示例"""
    api_key = "YOUR_GOOGLE_API_KEY"

    with GeminiAdapter(api_key=api_key, model="gemini-1.5-pro") as adapter:
        # 非流式生成
        messages = [
            {"role": "user", "content": "你好，请介绍一下自己"}
        ]

        response = adapter.generate(messages, temperature=0.7)
        text = adapter.extract_text_from_response(response)
        usage = adapter.get_usage_info(response)

        print(f"响应: {text}")
        print(f"Token 使用: {usage}")

        # 流式生成
        print("\n流式响应:")
        for chunk in adapter.generate_content_stream(messages):
            text = adapter.extract_text_from_response(chunk)
            if text:
                print(text, end="", flush=True)
        print()


if __name__ == "__main__":
    example_usage()

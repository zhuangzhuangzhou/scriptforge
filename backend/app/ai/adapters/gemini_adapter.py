"""Google Gemini API 适配器

提供与 Gemini API 交互的功能，包括：
- 文本生成
- 流式响应
- 函数调用
- 多模态输入支持
"""
import httpx
from typing import Dict, Any, List, Optional, AsyncIterator
import json


class GeminiAdapter:
    """Gemini API 适配器"""
    
    def __init__(
        self,
        api_key: str,
        api_endpoint: str = "https://generativelanguage.googleapis.com",
        model: str = "gemini-1.5-pro"
    ):
        """初始化适配器
        
        Args:
            api_key: Google API Key
            api_endpoint: API 端点
            model: 模型名称
        """
        self.api_key = api_key
        self.api_endpoint = api_endpoint.rstrip('/')
        self.model = model
        self.client = httpx.AsyncClient(timeout=60.0)
    
    def _build_url(self, endpoint: str) -> str:
        """构建完整的 API URL"""
        return f"{self.api_endpoint}/v1beta/models/{self.model}:{endpoint}?key={self.api_key}"
    
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
    
    async def generate_content(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> Dict[str, Any]:
        """生成内容（非流式）
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大输出 tokens
            **kwargs: 其他参数
        
        Returns:
            生成的响应
        """
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
        response = await self.client.post(url, json=request_body)
        response.raise_for_status()
        
        return response.json()
    
    async def generate_content_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """生成内容（流式）
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大输出 tokens
            **kwargs: 其他参数
        
        Yields:
            流式响应的每个块
        """
        url = self._build_url("streamGenerateContent")
        
        # 构建请求体
        request_body = self._convert_messages_to_gemini_format(messages)
        request_body["generationConfig"] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
        
        # 发送流式请求
        async with self.client.stream("POST", url, json=request_body) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        # Gemini 流式响应是 JSON 行
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
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()


# 使用示例
async def example_usage():
    """使用示例"""
    api_key = "YOUR_GOOGLE_API_KEY"
    
    async with GeminiAdapter(api_key=api_key, model="gemini-1.5-pro") as adapter:
        # 非流式生成
        messages = [
            {"role": "user", "content": "你好，请介绍一下自己"}
        ]
        
        response = await adapter.generate_content(messages, temperature=0.7)
        text = adapter.extract_text_from_response(response)
        usage = adapter.get_usage_info(response)
        
        print(f"响应: {text}")
        print(f"Token 使用: {usage}")
        
        # 流式生成
        print("\n流式响应:")
        async for chunk in adapter.generate_content_stream(messages):
            text = adapter.extract_text_from_response(chunk)
            if text:
                print(text, end="", flush=True)
        print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())

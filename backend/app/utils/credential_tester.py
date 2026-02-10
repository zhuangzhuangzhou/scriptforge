"""凭证测试工具"""
import httpx
from typing import Tuple


async def test_openai_credential(api_key: str, api_endpoint: str = None) -> Tuple[bool, str]:
    """测试 OpenAI API 凭证
    
    Args:
        api_key: OpenAI API Key
        api_endpoint: 可选的自定义 API 端点
        
    Returns:
        (是否成功, 消息)
    """
    endpoint = api_endpoint or "https://api.openai.com/v1"
    url = f"{endpoint}/models"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                return True, "OpenAI API 凭证验证成功"
            elif response.status_code == 401:
                return False, "API Key 无效或已过期"
            elif response.status_code == 429:
                return False, "API 请求频率超限，但凭证有效"
            else:
                return False, f"验证失败：HTTP {response.status_code}"
    except httpx.TimeoutException:
        return False, "请求超时，请检查网络连接或 API 端点"
    except Exception as e:
        return False, f"验证失败：{str(e)}"


async def test_anthropic_credential(api_key: str, api_endpoint: str = None) -> Tuple[bool, str]:
    """测试 Anthropic API 凭证
    
    Args:
        api_key: Anthropic API Key
        api_endpoint: 可选的自定义 API 端点
        
    Returns:
        (是否成功, 消息)
    """
    endpoint = api_endpoint or "https://api.anthropic.com"
    url = f"{endpoint}/v1/messages"
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    
    # 发送一个最小的测试请求
    data = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 1,
        "messages": [
            {"role": "user", "content": "Hi"}
        ]
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                return True, "Anthropic API 凭证验证成功"
            elif response.status_code == 401:
                return False, "API Key 无效或已过期"
            elif response.status_code == 429:
                return False, "API 请求频率超限，但凭证有效"
            else:
                return False, f"验证失败：HTTP {response.status_code}"
    except httpx.TimeoutException:
        return False, "请求超时，请检查网络连接或 API 端点"
    except Exception as e:
        return False, f"验证失败：{str(e)}"


async def test_azure_openai_credential(
    api_key: str,
    api_endpoint: str,
    api_version: str = "2023-05-15"
) -> Tuple[bool, str]:
    """测试 Azure OpenAI API 凭证
    
    Args:
        api_key: Azure OpenAI API Key
        api_endpoint: Azure OpenAI 端点
        api_version: API 版本
        
    Returns:
        (是否成功, 消息)
    """
    if not api_endpoint:
        return False, "Azure OpenAI 需要提供 API 端点"
    
    url = f"{api_endpoint}/openai/deployments?api-version={api_version}"
    
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                return True, "Azure OpenAI API 凭证验证成功"
            elif response.status_code == 401:
                return False, "API Key 无效或已过期"
            elif response.status_code == 404:
                return False, "API 端点不正确"
            else:
                return False, f"验证失败：HTTP {response.status_code}"
    except httpx.TimeoutException:
        return False, "请求超时，请检查网络连接或 API 端点"
    except Exception as e:
        return False, f"验证失败：{str(e)}"


async def test_gemini_credential(api_key: str, api_endpoint: str = None) -> Tuple[bool, str]:
    """测试 Google Gemini API 凭证
    
    Args:
        api_key: Google API Key
        api_endpoint: 可选的自定义 API 端点
        
    Returns:
        (是否成功, 消息)
    """
    endpoint = api_endpoint or "https://generativelanguage.googleapis.com"
    # 使用 models.list 接口测试凭证
    url = f"{endpoint}/v1beta/models?key={api_key}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                return True, "Google Gemini API 凭证验证成功"
            elif response.status_code == 400:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', '请求参数错误')
                return False, f"API Key 格式错误: {error_message}"
            elif response.status_code == 403:
                return False, "API Key 无效或权限不足"
            elif response.status_code == 429:
                return False, "API 请求频率超限，但凭证有效"
            else:
                return False, f"验证失败：HTTP {response.status_code}"
    except httpx.TimeoutException:
        return False, "请求超时，请检查网络连接或 API 端点"
    except Exception as e:
        return False, f"验证失败：{str(e)}"


async def test_credential(
    provider_type: str,
    api_key: str,
    api_endpoint: str = None,
    api_secret: str = None
) -> Tuple[bool, str]:
    """根据提供商类型测试凭证
    
    Args:
        provider_type: 提供商类型
        api_key: API Key
        api_endpoint: 可选的 API 端点
        api_secret: 可选的 API Secret
        
    Returns:
        (是否成功, 消息)
    """
    provider_type_lower = provider_type.lower()
    
    if provider_type_lower == "openai":
        return await test_openai_credential(api_key, api_endpoint)
    elif provider_type_lower == "anthropic":
        return await test_anthropic_credential(api_key, api_endpoint)
    elif provider_type_lower == "azure_openai":
        return await test_azure_openai_credential(api_key, api_endpoint)
    elif provider_type_lower == "gemini" or provider_type_lower == "google":
        return await test_gemini_credential(api_key, api_endpoint)
    else:
        return False, f"不支持的提供商类型: {provider_type}"

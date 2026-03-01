"""凭证测试工具"""
import httpx
from typing import Tuple, List, Optional


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
        # 确保显示详细的错误信息
        error_detail = str(e) if str(e) else f"未知错误 ({type(e).__name__})"
        return False, f"验证失败：{error_detail}"


async def test_anthropic_credential(
    api_key: str,
    api_endpoint: str = None,
    model_names: Optional[List[str]] = None
) -> Tuple[bool, str]:
    """测试 Anthropic API 凭证

    Args:
        api_key: Anthropic API Key
        api_endpoint: 可选的自定义 API 端点
        model_names: 可选的模型名称列表，优先使用提供商绑定的模型

    Returns:
        (是否成功, 消息)
    """
    endpoint = api_endpoint or "https://api.anthropic.com"
    url = f"{endpoint}/v1/messages"

    # 支持两种认证方式：官方 API 使用 x-api-key，第三方代理使用 Bearer token
    headers = {
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    if endpoint and "anthropic.com" not in endpoint:
        headers["Authorization"] = f"Bearer {api_key}"
    else:
        headers["x-api-key"] = api_key

    # 优先使用提供商绑定的模型，如果没有则使用默认列表
    if model_names:
        test_models = model_names
    else:
        test_models = [
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
        ]

    last_error = None
    for model in test_models:
        data = {
            "model": model,
            "max_tokens": 1,
            "messages": [
                {"role": "user", "content": "Hi"}
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=headers, json=data)

                if response.status_code == 200:
                    return True, f"Anthropic API 凭证验证成功 (模型: {model})"
                elif response.status_code == 401:
                    return False, "API Key 无效或已过期"
                elif response.status_code == 403:
                    # 尝试获取详细错误信息
                    try:
                        error_body = response.text[:500]
                        # 如果错误是模型不支持，继续尝试下一个
                        if "模型" in error_body or "model" in error_body.lower():
                            last_error = error_body
                            continue
                        return False, f"权限不足 (HTTP 403): {error_body}"
                    except:
                        return False, "权限不足 (HTTP 403)：可能是模型不支持或请求格式不正确"
                elif response.status_code == 429:
                    # 频率限制说明凭证是有效的，只是请求太频繁
                    return True, "凭证有效（触发频率限制，请稍后再试）"
                else:
                    # 尝试获取响应内容
                    try:
                        error_body = response.text[:500]
                        last_error = f"HTTP {response.status_code} - {error_body}"
                    except:
                        last_error = f"HTTP {response.status_code}"
        except Exception as e:
            last_error = str(e)

    # 所有模型都失败了
    return False, f"验证失败：{last_error}"


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
        # 确保显示详细的错误信息
        error_detail = str(e) if str(e) else f"未知错误 ({type(e).__name__})"
        return False, f"验证失败：{error_detail}"


async def test_gemini_credential(api_key: str, api_endpoint: str = None) -> Tuple[bool, str]:
    """测试 Google Gemini API 凭证

    Args:
        api_key: Google API Key
        api_endpoint: 可选的自定义 API 端点

    Returns:
        (是否成功, 消息)
    """
    import httpx
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
    except httpx.ConnectError:
        return False, "无法连接到 Google Gemini API，请检查网络连接或代理设置"
    except httpx.TimeoutException:
        return False, "请求超时，请检查网络连接"
    except Exception as e:
        # 确保显示详细的错误信息
        error_detail = str(e) if str(e) else f"未知错误 ({type(e).__name__})"
        return False, f"验证失败：{error_detail}"


async def test_credential(
    provider_type: str,
    api_key: str,
    api_endpoint: str = None,
    api_secret: str = None,
    model_names: Optional[List[str]] = None
) -> Tuple[bool, str]:
    """根据提供商类型测试凭证

    Args:
        provider_type: 提供商类型
        api_key: API Key
        api_endpoint: 可选的 API 端点
        api_secret: 可选的 API Secret
        model_names: 可选的模型名称列表（用于 Anthropic 测试）

    Returns:
        (是否成功, 消息)
    """
    provider_type_lower = provider_type.lower()

    if provider_type_lower == "openai":
        return await test_openai_credential(api_key, api_endpoint)
    elif provider_type_lower == "anthropic":
        return await test_anthropic_credential(api_key, api_endpoint, model_names)
    elif provider_type_lower == "azure_openai":
        return await test_azure_openai_credential(api_key, api_endpoint)
    elif provider_type_lower == "gemini" or provider_type_lower == "google":
        return await test_gemini_credential(api_key, api_endpoint)
    else:
        return False, f"不支持的提供商类型: {provider_type}"

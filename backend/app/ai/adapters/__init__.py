from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.adapters.base import BaseModelAdapter
from app.ai.adapters.openai_adapter import OpenAIAdapter
from app.ai.adapters.anthropic_adapter import AnthropicAdapter
from app.ai.adapters.model_config_service import ModelConfigService
from app.ai.simple_executor import parse_llm_response
from app.core.config import settings

__all__ = [
    "BaseModelAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "get_adapter",
    "get_adapter_sync",
    "parse_llm_response"  # 统一的 JSON 解析函数
]

# 默认模型提供商，可在配置中覆盖
DEFAULT_MODEL_PROVIDER = getattr(settings, 'DEFAULT_MODEL_PROVIDER', 'openai')


async def get_adapter(
    provider: Optional[str] = None,
    model_id: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Optional[AsyncSession] = None,
    log_enabled: bool = True
) -> BaseModelAdapter:
    """
    获取模型适配器实例

    根据配置返回对应的模型适配器。优先从数据库读取配置，如果数据库中没有配置则降级到环境变量。

    Args:
        provider: 模型提供商，可选值为 "openai" 或 "anthropic"
                  如果为 None，则使用默认配置
        model_id: 模型ID（UUID），如果指定则使用该模型
        user_id: 用户ID，用于获取用户自定义 API Key
        db: 数据库会话，如果提供则从数据库读取配置，同时用于记录 LLM 调用日志
        log_enabled: 是否启用 LLM 调用日志记录，默认启用

    Returns:
        BaseModelAdapter: 模型适配器实例
    """
    # 1. 尝试从数据库获取配置
    if db:
        config_service = ModelConfigService(db)
        config = await config_service.get_model_config(
            provider_key=provider,
            model_id=model_id,
            user_id=user_id
        )

        if config:
            # 使用数据库配置创建适配器
            provider_type = config["provider_type"]

            if provider_type == "anthropic" or config["provider_key"] == "anthropic":
                return AnthropicAdapter(
                    api_key=config["api_key"],
                    model_name=config["model_key"],
                    db=db,
                    log_enabled=log_enabled
                )
            else:
                # 默认使用 OpenAI 兼容适配器
                return OpenAIAdapter(
                    api_key=config["api_key"],
                    model_name=config["model_key"],
                    db=db,
                    log_enabled=log_enabled
                )

    # 2. 降级到环境变量配置（向后兼容）
    use_provider = provider or DEFAULT_MODEL_PROVIDER

    if use_provider == "anthropic":
        api_key = settings.ANTHROPIC_API_KEY
        model_name = settings.ANTHROPIC_MODEL
        return AnthropicAdapter(
            api_key=api_key,
            model_name=model_name,
            db=db,
            log_enabled=log_enabled
        )
    else:
        # 默认使用 OpenAI
        api_key = settings.OPENAI_API_KEY
        model_name = settings.OPENAI_MODEL
        return OpenAIAdapter(
            api_key=api_key,
            model_name=model_name,
            db=db,
            log_enabled=log_enabled
        )


# ============================================================================
# 同步版本（用于 Celery 任务）
# ============================================================================

from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timezone
from app.models.ai_model import AIModel
from app.models.ai_model_provider import AIModelProvider
from app.models.ai_model_credential import AIModelCredential


def get_adapter_sync(
    db: Session,
    model_id: Optional[str] = None,
    user_id: Optional[str] = None,
    log_enabled: bool = True
) -> BaseModelAdapter:
    """
    获取模型适配器实例（同步版本，用于 Celery）

    Args:
        db: 同步数据库会话
        model_id: 模型ID（UUID），必须指定
        user_id: 用户ID（预留，用于获取用户自定义配置）
        log_enabled: 是否启用 LLM 调用日志记录，默认启用

    Returns:
        BaseModelAdapter: 模型适配器实例

    Raises:
        ValueError: 如果模型不存在或未启用
    """
    if not model_id:
        raise ValueError("model_id 是必需的参数")

    # 查询模型
    model = db.query(AIModel).filter(
        AIModel.id == model_id,
        AIModel.is_enabled == True
    ).first()

    if not model:
        raise ValueError(f"模型不存在或未启用: {model_id}")

    # 查询提供商
    provider = db.query(AIModelProvider).filter(
        AIModelProvider.id == model.provider_id,
        AIModelProvider.is_enabled == True
    ).first()

    if not provider:
        raise ValueError(f"模型提供商不存在或未启用: {model.provider_id}")

    # 查询凭证
    # 优先选择：
    # 1. is_system_default=True 的凭证
    # 2. 未过期的凭证
    # 3. 按最后使用时间排序（最近使用的优先，实现负载均衡）
    from sqlalchemy import or_
    credential = db.query(AIModelCredential).filter(
        AIModelCredential.provider_id == provider.id,
        AIModelCredential.is_active == True,
        # 排除过期凭证
        or_(
            AIModelCredential.expires_at == None,
            AIModelCredential.expires_at > datetime.now(timezone.utc)
        )
    ).order_by(
        AIModelCredential.is_system_default.desc(),  # 优先系统默认
        AIModelCredential.last_used_at.desc().nullsfirst()  # 最近使用的优先（NULL 值排最前，表示从未使用）
    ).first()

    if not credential:
        raise ValueError(f"没有可用的凭证: {provider.display_name}")

    # 根据提供商类型创建适配器
    provider_type = provider.provider_type.lower()

    # 从提供商获取额外配置（如果有）
    extra_config = {"db": db, "log_enabled": log_enabled, "ai_model_id": str(model.id)}
    if hasattr(provider, 'config_schema') and provider.config_schema:
        if isinstance(provider.config_schema, dict):
            extra_config.update(provider.config_schema)

    # 如果提供商有自定义 API 端点，添加到配置中
    if hasattr(provider, 'api_endpoint') and provider.api_endpoint:
        extra_config['base_url'] = provider.api_endpoint

    # 将模型的默认配置传递给适配器
    model_config = {
        "max_output_tokens": model.max_output_tokens,
        "max_input_tokens": model.max_input_tokens,
        "temperature_default": float(model.temperature_default) if model.temperature_default else None,
        "timeout_seconds": model.timeout_seconds,
    }
    extra_config["model_config"] = model_config

    if provider_type == "anthropic":
        return AnthropicAdapter(
            api_key=credential.api_key,
            model_name=model.model_key,
            **extra_config
        )
    elif provider_type == "openai" or provider_type == "openai_compatible":
        return OpenAIAdapter(
            api_key=credential.api_key,
            model_name=model.model_key,
            **extra_config
        )
    elif provider_type == "azure_openai":
        # Azure OpenAI 使用 OpenAI 适配器，但需要额外配置
        return OpenAIAdapter(
            api_key=credential.api_key,
            model_name=model.model_key,
            **extra_config
        )
    elif provider_type == "google_gemini" or provider_type == "gemini":
        # Gemini 适配器
        from app.ai.adapters.gemini_adapter import GeminiAdapter
        return GeminiAdapter(
            api_key=credential.api_key,
            model_name=model.model_key,
            **extra_config
        )
    else:
        # 默认使用 OpenAI 兼容适配器
        return OpenAIAdapter(
            api_key=credential.api_key,
            model_name=model.model_key,
            **extra_config
        )

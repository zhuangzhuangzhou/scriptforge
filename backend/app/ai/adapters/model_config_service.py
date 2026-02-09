"""模型配置服务

从数据库获取模型配置、凭证等信息
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_model_provider import AIModelProvider
from app.models.ai_model import AIModel
from app.models.ai_model_credential import AIModelCredential


class ModelConfigService:
    """模型配置服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_model_config(
        self,
        provider_key: Optional[str] = None,
        model_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取模型配置

        Args:
            provider_key: 提供商标识（如 'openai', 'anthropic'）
            model_id: 模型ID（UUID）
            user_id: 用户ID（用于获取用户自定义 API Key）

        Returns:
            模型配置字典，包含：
            - provider_key: 提供商标识
            - provider_type: 提供商类型
            - model_key: 模型标识
            - api_key: API Key（解密后）
            - api_endpoint: API 端点
            - max_tokens: 最大 Token 数
            - timeout_seconds: 超时时间
            - temperature_default: 默认温度
            如果没有找到配置，返回 None
        """
        # 1. 查询模型
        model = None
        if model_id:
            # 根据模型ID查询
            result = await self.db.execute(
                select(AIModel)
                .where(AIModel.id == model_id)
                .where(AIModel.is_enabled == True)
            )
            model = result.scalar_one_or_none()
        elif provider_key:
            # 根据提供商查询默认模型
            result = await self.db.execute(
                select(AIModel)
                .join(AIModelProvider)
                .where(AIModelProvider.provider_key == provider_key)
                .where(AIModelProvider.is_enabled == True)
                .where(AIModel.is_enabled == True)
                .where(AIModel.is_default == True)
            )
            model = result.scalar_one_or_none()
        else:
            # 查询系统默认模型
            result = await self.db.execute(
                select(AIModel)
                .where(AIModel.is_enabled == True)
                .where(AIModel.is_default == True)
            )
            model = result.scalar_one_or_none()

        if not model:
            return None

        # 2. 查询凭证
        # TODO: 优先使用用户自定义 API Key（从 User.api_keys 字段）
        # 这里先使用系统默认凭证
        result = await self.db.execute(
            select(AIModelCredential)
            .where(AIModelCredential.provider_id == model.provider_id)
            .where(AIModelCredential.is_active == True)
            .where(
                and_(
                    AIModelCredential.expires_at.is_(None) |
                    (AIModelCredential.expires_at > datetime.utcnow())
                )
            )
            .order_by(AIModelCredential.is_system_default.desc())
            .limit(1)
        )
        credential = result.scalar_one_or_none()

        if not credential:
            return None

        # 3. 获取 API Key（明文存储）
        api_key = credential.api_key
        api_secret = credential.api_secret

        # 4. 构建配置字典
        config = {
            "provider_key": model.provider.provider_key,
            "provider_type": model.provider.provider_type,
            "model_key": model.model_key,
            "api_key": api_key,
            "api_secret": api_secret,
            "api_endpoint": model.provider.api_endpoint,
            "max_tokens": model.max_tokens,
            "max_input_tokens": model.max_input_tokens,
            "max_output_tokens": model.max_output_tokens,
            "timeout_seconds": model.timeout_seconds,
            "temperature_default": float(model.temperature_default) if model.temperature_default else 0.7,
            "supports_streaming": model.supports_streaming,
            "supports_function_calling": model.supports_function_calling,
        }

        return config

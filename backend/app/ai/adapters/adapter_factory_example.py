"""
适配器工厂函数改造示例

这个文件展示了如何改造现有的 get_adapter 函数以支持数据库配置。

使用方法：
1. 将此文件的内容集成到你的 backend/app/ai/adapters/__init__.py 中
2. 或者参考这个示例改造你现有的适配器创建逻辑
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.ai.adapters.model_config_service import ModelConfigService


async def get_adapter_with_db_config(
    provider: Optional[str] = None,
    model_id: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Optional[AsyncSession] = None
):
    """
    获取 AI 模型适配器（支持数据库配置）

    优先级：
    1. 数据库配置（如果提供了 db 参数）
    2. 环境变量配置（降级方案）

    Args:
        provider: 提供商标识（如 'openai', 'anthropic'）
        model_id: 模型ID（UUID字符串）
        user_id: 用户ID（用于获取用户自定义配置）
        db: 数据库会话

    Returns:
        适配器实例

    示例：
        # 使用数据库配置
        adapter = await get_adapter_with_db_config(
            provider="openai",
            db=db
        )

        # 使用特定模型
        adapter = await get_adapter_with_db_config(
            model_id="uuid-string",
            db=db
        )

        # 降级到环境变量
        adapter = await get_adapter_with_db_config(
            provider="openai"
        )
    """
    config = None

    # 1. 尝试从数据库获取配置
    if db:
        config_service = ModelConfigService(db)
        config = await config_service.get_model_config(
            provider_key=provider,
            model_id=model_id,
            user_id=user_id
        )

    # 2. 如果数据库配置可用，使用数据库配置
    if config:
        provider_type = config["provider_type"]
        api_key = config["api_key"]
        model_name = config["model_name"]
        api_endpoint = config.get("api_endpoint")

        if provider_type == "openai_compatible" or provider_type == "openai":
            # 导入 OpenAI 适配器（假设你有这个类）
            # from app.ai.adapters.openai_adapter import OpenAIAdapter
            # return OpenAIAdapter(
            #     api_key=api_key,
            #     model=model_name,
            #     base_url=api_endpoint
            # )
            print(f"使用数据库配置创建 OpenAI 适配器: {model_name}")
            return {
                "type": "openai",
                "api_key": api_key,
                "model": model_name,
                "base_url": api_endpoint
            }

        elif provider_type == "anthropic":
            # 导入 Anthropic 适配器（假设你有这个类）
            # from app.ai.adapters.anthropic_adapter import AnthropicAdapter
            # return AnthropicAdapter(
            #     api_key=api_key,
            #     model=model_name
            # )
            print(f"使用数据库配置创建 Anthropic 适配器: {model_name}")
            return {
                "type": "anthropic",
                "api_key": api_key,
                "model": model_name
            }

    # 3. 降级到环境变量配置
    print("数据库配置不可用，降级到环境变量配置")

    if provider == "openai" or not provider:
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        if api_key:
            # from app.ai.adapters.openai_adapter import OpenAIAdapter
            # return OpenAIAdapter(api_key=api_key, model=model)
            return {
                "type": "openai",
                "api_key": api_key,
                "model": model
            }

    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
        if api_key:
            # from app.ai.adapters.anthropic_adapter import AnthropicAdapter
            # return AnthropicAdapter(api_key=api_key, model=model)
            return {
                "type": "anthropic",
                "api_key": api_key,
                "model": model
            }

    raise ValueError(f"无法创建适配器: provider={provider}, 配置不可用")


# ==================== 使用示例 ====================

async def example_usage():
    """使用示例"""
    from app.core.database import get_db

    # 示例1：使用数据库配置获取 OpenAI 适配器
    async for db in get_db():
        adapter = await get_adapter_with_db_config(
            provider="openai",
            db=db
        )
        print(f"获取到适配器: {adapter}")
        break

    # 示例2：使用特定模型ID
    async for db in get_db():
        adapter = await get_adapter_with_db_config(
            model_id="your-model-uuid",
            db=db
        )
        print(f"获取到适配器: {adapter}")
        break

    # 示例3：降级到环境变量
    adapter = await get_adapter_with_db_config(
        provider="openai"
    )
    print(f"获取到适配器（环境变量）: {adapter}")


# ==================== 集成到现有任务的示例 ====================

async def example_task_integration(db: AsyncSession):
    """
    展示如何在现有任务中集成新的配置系统

    原有代码：
        adapter = get_adapter(provider="openai")

    改造后：
        adapter = await get_adapter_with_db_config(
            provider="openai",
            db=db
        )
    """
    # 获取适配器
    adapter = await get_adapter_with_db_config(
        provider="openai",
        db=db
    )

    # 使用适配器进行 AI 调用
    # response = await adapter.chat(messages=[...])
    print(f"使用适配器: {adapter}")

"""初始化模型管理默认数据

插入默认的模型提供商、模型和计费规则
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.ai_model_provider import AIModelProvider
from app.models.ai_model import AIModel
from app.models.ai_model_pricing import AIModelPricing
from app.models.system_model_config import SystemModelConfig
from decimal import Decimal


async def init_providers():
    """初始化模型提供商"""
    async with AsyncSessionLocal() as db:
        # 检查是否已有提供商
        result = await db.execute(select(AIModelProvider))
        existing = result.scalars().first()

        if existing:
            print("提供商已存在，跳过初始化")
            return

        # 创建 OpenAI 提供商
        openai_provider = AIModelProvider(
            provider_key="openai",
            display_name="OpenAI",
            provider_type="openai_compatible",
            api_endpoint="https://api.openai.com/v1",
            is_enabled=True,
            is_system_default=True,
            description="OpenAI 官方 API",
            icon_url="https://openai.com/favicon.ico"
        )
        db.add(openai_provider)

        # 创建 Anthropic 提供商
        anthropic_provider = AIModelProvider(
            provider_key="anthropic",
            display_name="Anthropic",
            provider_type="anthropic",
            api_endpoint="https://api.anthropic.com",
            is_enabled=True,
            is_system_default=False,
            description="Anthropic Claude API",
            icon_url="https://anthropic.com/favicon.ico"
        )
        db.add(anthropic_provider)

        await db.commit()
        print("✅ 成功创建 2 个模型提供商")

        return openai_provider, anthropic_provider


async def init_models():
    """初始化模型"""
    async with AsyncSessionLocal() as db:
        # 获取提供商
        result = await db.execute(
            select(AIModelProvider).where(AIModelProvider.provider_key == "openai")
        )
        openai_provider = result.scalar_one()

        result = await db.execute(
            select(AIModelProvider).where(AIModelProvider.provider_key == "anthropic")
        )
        anthropic_provider = result.scalar_one()

        # 检查是否已有模型
        result = await db.execute(select(AIModel))
        existing = result.scalars().first()

        if existing:
            print("模型已存在，跳过初始化")
            return

        # OpenAI 模型
        models = [
            # GPT-4 Turbo
            AIModel(
                provider_id=openai_provider.id,
                model_key="gpt-4-turbo-preview",
                display_name="GPT-4 Turbo",
                model_type="chat",
                is_enabled=True,
                is_default=True,
                max_tokens=128000,
                max_input_tokens=120000,
                max_output_tokens=4096,
                timeout_seconds=120,
                temperature_default=Decimal('0.7'),
                supports_streaming=True,
                supports_function_calling=True,
                description="GPT-4 Turbo 模型，支持 128K 上下文"
            ),
            # GPT-4
            AIModel(
                provider_id=openai_provider.id,
                model_key="gpt-4",
                display_name="GPT-4",
                model_type="chat",
                is_enabled=True,
                is_default=False,
                max_tokens=8192,
                max_input_tokens=8192,
                max_output_tokens=4096,
                timeout_seconds=120,
                temperature_default=Decimal('0.7'),
                supports_streaming=True,
                supports_function_calling=True,
                description="GPT-4 标准模型"
            ),
            # GPT-3.5 Turbo
            AIModel(
                provider_id=openai_provider.id,
                model_key="gpt-3.5-turbo",
                display_name="GPT-3.5 Turbo",
                model_type="chat",
                is_enabled=True,
                is_default=False,
                max_tokens=16385,
                max_input_tokens=16385,
                max_output_tokens=4096,
                timeout_seconds=60,
                temperature_default=Decimal('0.7'),
                supports_streaming=True,
                supports_function_calling=True,
                description="GPT-3.5 Turbo 模型，性价比高"
            ),
            # Claude 3 Opus
            AIModel(
                provider_id=anthropic_provider.id,
                model_key="claude-3-opus-20240229",
                display_name="Claude 3 Opus",
                model_type="chat",
                is_enabled=True,
                is_default=False,
                max_tokens=200000,
                max_input_tokens=200000,
                max_output_tokens=4096,
                timeout_seconds=120,
                temperature_default=Decimal('0.7'),
                supports_streaming=True,
                supports_function_calling=False,
                description="Claude 3 Opus 模型，最强大的 Claude 模型"
            ),
            # Claude 3 Sonnet
            AIModel(
                provider_id=anthropic_provider.id,
                model_key="claude-3-sonnet-20240229",
                display_name="Claude 3 Sonnet",
                model_type="chat",
                is_enabled=True,
                is_default=False,
                max_tokens=200000,
                max_input_tokens=200000,
                max_output_tokens=4096,
                timeout_seconds=120,
                temperature_default=Decimal('0.7'),
                supports_streaming=True,
                supports_function_calling=False,
                description="Claude 3 Sonnet 模型，平衡性能和成本"
            ),
        ]

        for model in models:
            db.add(model)

        await db.commit()
        print(f"✅ 成功创建 {len(models)} 个模型")

        return models


async def init_pricing():
    """初始化计费规则"""
    async with AsyncSessionLocal() as db:
        # 获取所有模型
        result = await db.execute(select(AIModel))
        models = result.scalars().all()

        # 检查是否已有计费规则
        result = await db.execute(select(AIModelPricing))
        existing = result.scalars().first()

        if existing:
            print("计费规则已存在，跳过初始化")
            return

        # 为每个模型创建默认计费规则
        pricing_rules = []

        for model in models:
            # 根据模型类型设置不同的价格
            if "gpt-4-turbo" in model.model_key:
                input_price = Decimal('1.5')
                output_price = Decimal('3.0')
            elif "gpt-4" in model.model_key:
                input_price = Decimal('3.0')
                output_price = Decimal('6.0')
            elif "gpt-3.5" in model.model_key:
                input_price = Decimal('0.5')
                output_price = Decimal('1.0')
            elif "claude-3-opus" in model.model_key:
                input_price = Decimal('1.5')
                output_price = Decimal('7.5')
            elif "claude-3-sonnet" in model.model_key:
                input_price = Decimal('0.3')
                output_price = Decimal('1.5')
            else:
                input_price = Decimal('1.0')
                output_price = Decimal('1.0')

            pricing = AIModelPricing(
                model_id=model.id,
                input_credits_per_1k_tokens=input_price,
                output_credits_per_1k_tokens=output_price,
                min_credits_per_request=Decimal('0.1'),
                is_active=True
            )
            pricing_rules.append(pricing)
            db.add(pricing)

        await db.commit()
        print(f"✅ 成功创建 {len(pricing_rules)} 条计费规则")


async def init_system_config():
    """初始化系统配置"""
    async with AsyncSessionLocal() as db:
        # 检查是否已有系统配置
        result = await db.execute(select(SystemModelConfig))
        existing = result.scalars().first()

        if existing:
            print("系统配置已存在，跳过初始化")
            return

        # 创建默认系统配置
        configs = [
            SystemModelConfig(
                config_key="default_provider",
                config_value={"value": "openai"},
                value_type="string",
                description="默认模型提供商",
                is_editable=True
            ),
            SystemModelConfig(
                config_key="default_model",
                config_value={"value": "gpt-4-turbo-preview"},
                value_type="string",
                description="默认模型",
                is_editable=True
            ),
            SystemModelConfig(
                config_key="global_token_limit",
                config_value={"value": 100000},
                value_type="integer",
                description="全局单次请求 Token 上限",
                is_editable=True
            ),
            SystemModelConfig(
                config_key="credits_per_1k_tokens",
                config_value={"value": 1.0},
                value_type="number",
                description="默认积分换算率（向后兼容）",
                is_editable=True
            ),
            SystemModelConfig(
                config_key="enable_user_custom_keys",
                config_value={"value": True},
                value_type="boolean",
                description="是否允许用户使用自定义 API Key",
                is_editable=True
            ),
        ]

        for config in configs:
            db.add(config)

        await db.commit()
        print(f"✅ 成功创建 {len(configs)} 条系统配置")


async def main():
    """主函数"""
    print("开始初始化模型管理数据...")
    print()

    try:
        # 1. 初始化提供商
        print("1. 初始化模型提供商...")
        await init_providers()
        print()

        # 2. 初始化模型
        print("2. 初始化模型...")
        await init_models()
        print()

        # 3. 初始化计费规则
        print("3. 初始化计费规则...")
        await init_pricing()
        print()

        # 4. 初始化系统配置
        print("4. 初始化系统配置...")
        await init_system_config()
        print()

        print("=" * 50)
        print("✅ 模型管理数据初始化完成！")
        print("=" * 50)

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

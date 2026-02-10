"""初始化 Gemini 提供商和模型配置

这个脚本会在数据库中创建：
1. Google Gemini 提供商
2. 常用的 Gemini 模型配置
3. 示例凭证（需要手动填入真实的 API Key）

运行方式：
    python scripts/init_gemini_provider.py
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


async def init_gemini_provider():
    """初始化 Gemini 提供商和模型"""
    
    async with AsyncSessionLocal() as db:
        # 1. 检查提供商是否已存在
        result = await db.execute(
            select(AIModelProvider).where(AIModelProvider.provider_key == "gemini")
        )
        provider = result.scalar_one_or_none()
        
        if provider:
            print(f"✓ Gemini 提供商已存在 (ID: {provider.id})")
        else:
            # 创建提供商
            provider = AIModelProvider(
                provider_key="gemini",
                display_name="Google Gemini",
                provider_type="gemini",
                api_endpoint="https://generativelanguage.googleapis.com",
                icon_url="https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg",
                description="Google 的多模态 AI 模型，支持文本、图像、音频和视频理解",
                is_enabled=True,
                is_system_default=False
            )
            db.add(provider)
            await db.commit()
            await db.refresh(provider)
            print(f"✓ 创建 Gemini 提供商 (ID: {provider.id})")
        
        # 2. 创建模型配置
        models_config = [
            {
                "model_key": "gemini-1.5-pro",
                "display_name": "Gemini 1.5 Pro",
                "model_type": "chat",
                "max_tokens": 8192,
                "max_input_tokens": 2097152,  # 2M tokens
                "max_output_tokens": 8192,
                "timeout_seconds": 60,
                "temperature_default": 0.7,
                "supports_streaming": True,
                "supports_function_calling": True,
                "description": "最强大的 Gemini 模型，支持超长上下文（2M tokens）和多模态输入",
                "pricing": {
                    "input_credits_per_1k_tokens": 1.25,  # $0.00125 per 1K tokens
                    "output_credits_per_1k_tokens": 5.0,   # $0.005 per 1K tokens
                    "min_credits_per_request": 0.1
                }
            },
            {
                "model_key": "gemini-1.5-flash",
                "display_name": "Gemini 1.5 Flash",
                "model_type": "chat",
                "max_tokens": 8192,
                "max_input_tokens": 1048576,  # 1M tokens
                "max_output_tokens": 8192,
                "timeout_seconds": 30,
                "temperature_default": 0.7,
                "supports_streaming": True,
                "supports_function_calling": True,
                "description": "快速且高效的 Gemini 模型，适合大规模部署",
                "pricing": {
                    "input_credits_per_1k_tokens": 0.075,  # $0.000075 per 1K tokens
                    "output_credits_per_1k_tokens": 0.3,   # $0.0003 per 1K tokens
                    "min_credits_per_request": 0.05
                }
            },
            {
                "model_key": "gemini-1.5-flash-8b",
                "display_name": "Gemini 1.5 Flash-8B",
                "model_type": "chat",
                "max_tokens": 8192,
                "max_input_tokens": 1048576,  # 1M tokens
                "max_output_tokens": 8192,
                "timeout_seconds": 20,
                "temperature_default": 0.7,
                "supports_streaming": True,
                "supports_function_calling": True,
                "description": "最快速的 Gemini 模型，适合高频率调用场景",
                "pricing": {
                    "input_credits_per_1k_tokens": 0.0375,  # $0.0000375 per 1K tokens
                    "output_credits_per_1k_tokens": 0.15,   # $0.00015 per 1K tokens
                    "min_credits_per_request": 0.02
                }
            },
            {
                "model_key": "gemini-1.0-pro",
                "display_name": "Gemini 1.0 Pro",
                "model_type": "chat",
                "max_tokens": 8192,
                "max_input_tokens": 32768,
                "max_output_tokens": 8192,
                "timeout_seconds": 60,
                "temperature_default": 0.7,
                "supports_streaming": True,
                "supports_function_calling": True,
                "description": "第一代 Gemini Pro 模型，稳定可靠",
                "pricing": {
                    "input_credits_per_1k_tokens": 0.5,
                    "output_credits_per_1k_tokens": 1.5,
                    "min_credits_per_request": 0.1
                }
            },
        ]
        
        created_count = 0
        skipped_count = 0
        
        for model_config in models_config:
            # 检查模型是否已存在
            result = await db.execute(
                select(AIModel).where(
                    AIModel.provider_id == provider.id,
                    AIModel.model_key == model_config["model_key"]
                )
            )
            existing_model = result.scalar_one_or_none()
            
            if existing_model:
                print(f"  - 跳过已存在的模型: {model_config['display_name']}")
                skipped_count += 1
                continue
            
            # 创建模型
            pricing_config = model_config.pop("pricing")
            model = AIModel(
                provider_id=provider.id,
                **model_config
            )
            db.add(model)
            await db.flush()  # 获取模型 ID
            
            # 创建计费规则
            pricing = AIModelPricing(
                model_id=model.id,
                **pricing_config,
                is_active=True
            )
            db.add(pricing)
            
            print(f"  ✓ 创建模型: {model_config['display_name']}")
            created_count += 1
        
        await db.commit()
        
        print(f"\n总结:")
        print(f"  - 创建了 {created_count} 个模型")
        print(f"  - 跳过了 {skipped_count} 个已存在的模型")
        print(f"\n下一步:")
        print(f"  1. 访问管理界面: http://localhost:5173/admin/models")
        print(f"  2. 在「凭证管理」中添加 Google API Key")
        print(f"  3. 测试凭证是否有效")
        print(f"\n获取 API Key:")
        print(f"  访问: https://aistudio.google.com/app/apikey")


async def main():
    """主函数"""
    print("=" * 60)
    print("初始化 Google Gemini 提供商和模型配置")
    print("=" * 60)
    print()
    
    try:
        await init_gemini_provider()
        print("\n✓ 初始化完成！")
    except Exception as e:
        print(f"\n✗ 初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

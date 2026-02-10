"""检查模型配置"""
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.ai_model import AIModel
from app.models.ai_model_provider import AIModelProvider

async def check_models():
    async with AsyncSessionLocal() as db:
        # 检查模型提供商
        providers_result = await db.execute(
            select(AIModelProvider).where(AIModelProvider.is_enabled == True)
        )
        providers = providers_result.scalars().all()
        
        print(f"激活的模型提供商数量: {len(providers)}")
        for provider in providers:
            print(f"  - {provider.display_name} ({provider.provider_type})")
            print(f"    Provider Key: {provider.provider_key}")
        
        # 检查模型
        models_result = await db.execute(
            select(AIModel).where(AIModel.is_enabled == True)
        )
        models = models_result.scalars().all()
        
        print(f"\n激活的模型数量: {len(models)}")
        for model in models:
            print(f"  - {model.display_name} ({model.model_key})")
            print(f"    Provider ID: {model.provider_id}")
        
        if len(models) == 0:
            print("\n⚠️  警告：没有激活的模型！")
            print("这可能是任务无法执行的原因。")

asyncio.run(check_models())

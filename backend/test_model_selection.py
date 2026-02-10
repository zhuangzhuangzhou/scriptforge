#!/usr/bin/env python3
"""测试模型选择逻辑"""
from app.core.database import SyncSessionLocal
from app.models.ai_model import AIModel
from app.models.ai_model_provider import AIModelProvider
from app.ai.adapters import get_adapter_sync

def test_model_selection():
    """测试同步模型选择"""
    db = SyncSessionLocal()
    try:
        # 查询所有可用的模型
        models = db.query(AIModel).filter(
            AIModel.is_enabled == True
        ).all()
        
        print(f"📋 找到 {len(models)} 个可用模型:\n")
        
        for model in models:
            provider = db.query(AIModelProvider).filter(
                AIModelProvider.id == model.provider_id
            ).first()
            
            print(f"模型 ID: {model.id}")
            print(f"  名称: {model.display_name}")
            print(f"  模型键: {model.model_key}")
            print(f"  提供商: {provider.name if provider else 'Unknown'}")
            print(f"  类型: {provider.provider_type if provider else 'Unknown'}")
            print(f"  是否默认: {model.is_default}")
            print()
        
        # 测试获取适配器
        if models:
            test_model = models[0]
            print(f"🧪 测试获取适配器:")
            print(f"   使用模型: {test_model.display_name} ({test_model.id})")
            
            try:
                adapter = get_adapter_sync(
                    db=db,
                    model_id=str(test_model.id),
                    user_id=None
                )
                print(f"   ✅ 成功创建适配器: {type(adapter).__name__}")
                print(f"   模型名称: {adapter.model_name}")
            except Exception as e:
                print(f"   ❌ 创建适配器失败: {e}")
        
        # 查找默认模型
        default_model = db.query(AIModel).filter(
            AIModel.is_enabled == True,
            AIModel.is_default == True
        ).first()
        
        if default_model:
            print(f"\n⭐ 默认模型:")
            print(f"   ID: {default_model.id}")
            print(f"   名称: {default_model.display_name}")
            print(f"\n💡 前端应该使用这个 ID 作为默认值")
        else:
            print(f"\n⚠️  没有设置默认模型")
            print(f"   建议设置一个默认模型")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_model_selection()

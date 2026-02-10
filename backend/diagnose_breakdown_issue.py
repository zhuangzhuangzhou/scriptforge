#!/usr/bin/env python3
"""诊断拆解任务失败的问题"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SyncSessionLocal
from app.models.ai_model import AIModel
from app.models.ai_model_provider import AIModelProvider
from app.models.ai_model_credential import AIModelCredential
from app.models.project import Project
from app.models.batch import Batch
from app.models.ai_task import AITask


def diagnose():
    """诊断问题"""
    db = SyncSessionLocal()
    
    try:
        print("🔍 开始诊断拆解任务问题...\n")
        
        # 1. 检查激活的模型提供商
        print("=" * 60)
        print("1. 检查模型提供商")
        print("=" * 60)
        providers = db.query(AIModelProvider).filter(
            AIModelProvider.is_enabled == True
        ).all()
        
        print(f"激活的提供商数量: {len(providers)}")
        for p in providers:
            print(f"  - {p.display_name} ({p.provider_type})")
            print(f"    Provider ID: {p.id}")
            print(f"    Provider Key: {p.provider_key}")
            
            # 检查该提供商的凭证
            credentials = db.query(AIModelCredential).filter(
                AIModelCredential.provider_id == p.id,
                AIModelCredential.is_active == True
            ).all()
            
            if credentials:
                print(f"    ✅ 凭证数量: {len(credentials)}")
                for cred in credentials:
                    print(f"       - Credential ID: {cred.id}")
                    print(f"         API Key: {cred.api_key[:10]}..." if cred.api_key else "         ❌ 无 API Key")
            else:
                print(f"    ❌ 没有激活的凭证")
        
        # 2. 检查激活的模型
        print("\n" + "=" * 60)
        print("2. 检查模型")
        print("=" * 60)
        models = db.query(AIModel).filter(
            AIModel.is_enabled == True
        ).all()
        
        print(f"激活的模型数量: {len(models)}")
        for m in models:
            print(f"  - {m.display_name} ({m.model_key})")
            print(f"    Model ID: {m.id}")
            print(f"    Provider ID: {m.provider_id}")
            
            # 检查提供商是否存在且激活
            provider = db.query(AIModelProvider).filter(
                AIModelProvider.id == m.provider_id,
                AIModelProvider.is_enabled == True
            ).first()
            
            if provider:
                print(f"    ✅ 提供商: {provider.display_name}")
                
                # 检查凭证
                credential = db.query(AIModelCredential).filter(
                    AIModelCredential.provider_id == provider.id,
                    AIModelCredential.is_active == True
                ).first()
                
                if credential:
                    print(f"    ✅ 有可用凭证")
                else:
                    print(f"    ❌ 没有可用凭证")
            else:
                print(f"    ❌ 提供商不存在或未激活")
        
        # 3. 检查项目配置
        print("\n" + "=" * 60)
        print("3. 检查项目配置")
        print("=" * 60)
        projects = db.query(Project).all()
        
        print(f"项目数量: {len(projects)}")
        for proj in projects:
            print(f"  - 项目: {proj.name}")
            print(f"    Project ID: {proj.id}")
            print(f"    Breakdown Model ID: {proj.breakdown_model_id}")
            
            if proj.breakdown_model_id:
                model = db.query(AIModel).filter(
                    AIModel.id == proj.breakdown_model_id
                ).first()
                
                if model:
                    print(f"    ✅ 模型: {model.display_name}")
                    print(f"       启用状态: {model.is_enabled}")
                else:
                    print(f"    ❌ 模型不存在")
            else:
                print(f"    ⚠️  未配置拆解模型")
        
        # 4. 检查失败的批次
        print("\n" + "=" * 60)
        print("4. 检查失败的批次")
        print("=" * 60)
        failed_batches = db.query(Batch).filter(
            Batch.breakdown_status == "failed"
        ).limit(5).all()
        
        print(f"失败批次数量（显示前5个）: {len(failed_batches)}")
        for batch in failed_batches:
            print(f"  - 批次 {batch.batch_number}")
            print(f"    Batch ID: {batch.id}")
            print(f"    Project ID: {batch.project_id}")
            
            # 查找对应的任务
            tasks = db.query(AITask).filter(
                AITask.batch_id == batch.id,
                AITask.task_type == "breakdown"
            ).all()
            
            if tasks:
                print(f"    任务数量: {len(tasks)}")
                for task in tasks:
                    print(f"      - Task ID: {task.id}")
                    print(f"        状态: {task.status}")
                    if task.error_message:
                        print(f"        错误: {task.error_message[:100]}...")
                    if task.config:
                        model_id = task.config.get("model_config_id")
                        print(f"        配置的模型 ID: {model_id}")
            else:
                print(f"    ⚠️  没有关联的任务")
        
        print("\n" + "=" * 60)
        print("诊断完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 诊断过程中出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    diagnose()

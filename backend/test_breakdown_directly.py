#!/usr/bin/env python3
"""直接测试拆解任务执行"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SyncSessionLocal
from app.models.batch import Batch
from app.models.ai_task import AITask
from app.models.project import Project
from app.ai.adapters import get_adapter_sync


def test_breakdown():
    """测试拆解任务"""
    db = SyncSessionLocal()
    
    try:
        print("🔍 测试拆解任务执行...\n")
        
        # 1. 找一个失败的批次
        print("=" * 60)
        print("1. 查找失败的批次")
        print("=" * 60)
        
        failed_batch = db.query(Batch).filter(
            Batch.breakdown_status == "failed"
        ).first()
        
        if not failed_batch:
            print("❌ 没有找到失败的批次")
            return
        
        print(f"✅ 找到批次: {failed_batch.batch_number}")
        print(f"   Batch ID: {failed_batch.id}")
        print(f"   Project ID: {failed_batch.project_id}")
        
        # 2. 获取项目配置
        print("\n" + "=" * 60)
        print("2. 获取项目配置")
        print("=" * 60)
        
        project = db.query(Project).filter(
            Project.id == failed_batch.project_id
        ).first()
        
        if not project:
            print("❌ 项目不存在")
            return
        
        print(f"✅ 项目: {project.name}")
        print(f"   Breakdown Model ID: {project.breakdown_model_id}")
        
        if not project.breakdown_model_id:
            print("❌ 项目未配置拆解模型")
            return
        
        # 3. 测试获取模型适配器
        print("\n" + "=" * 60)
        print("3. 测试获取模型适配器")
        print("=" * 60)
        
        try:
            model_adapter = get_adapter_sync(
                db=db,
                model_id=str(project.breakdown_model_id),
                user_id=str(project.user_id)
            )
            print(f"✅ 成功获取模型适配器")
            print(f"   适配器类型: {type(model_adapter).__name__}")
            
            # 4. 测试流式生成
            print("\n" + "=" * 60)
            print("4. 测试流式生成")
            print("=" * 60)
            
            test_prompt = "请用一句话介绍你自己。"
            print(f"测试提示词: {test_prompt}")
            print("开始流式生成...")
            
            full_response = ""
            chunk_count = 0
            
            for chunk in model_adapter.stream_generate(test_prompt):
                chunk_count += 1
                full_response += chunk
                print(f"  Chunk {chunk_count}: {chunk[:50]}..." if len(chunk) > 50 else f"  Chunk {chunk_count}: {chunk}")
                
                if chunk_count >= 5:  # 只测试前5个chunk
                    print("  ... (停止测试)")
                    break
            
            print(f"\n✅ 流式生成测试成功")
            print(f"   总共接收 {chunk_count} 个 chunks")
            print(f"   响应内容: {full_response[:100]}...")
            
        except ValueError as e:
            print(f"❌ 获取模型适配器失败: {e}")
            print("\n详细错误信息:")
            import traceback
            traceback.print_exc()
            return
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            print("\n详细错误信息:")
            import traceback
            traceback.print_exc()
            return
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_breakdown()

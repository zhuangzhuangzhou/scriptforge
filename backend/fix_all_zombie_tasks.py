#!/usr/bin/env python3
"""批量修复所有僵尸任务"""
from app.core.database import SyncSessionLocal
from app.models.ai_task import AITask
from app.models.batch import Batch
from datetime import datetime
from sqlalchemy import text

def fix_all_zombie_tasks():
    """修复所有僵尸任务"""
    db = SyncSessionLocal()
    try:
        # 查找所有 queued 状态的任务
        tasks = db.query(AITask).filter(AITask.status == "queued").all()
        
        print(f"📋 找到 {len(tasks)} 个排队中的任务")
        
        if len(tasks) == 0:
            print("✅ 没有需要修复的任务")
            return 0
        
        # 分类任务
        zombie_tasks = []
        normal_tasks = []
        
        for task in tasks:
            # 如果任务有进度但没有开始时间，说明是僵尸任务
            if task.progress > 0 and task.started_at is None:
                zombie_tasks.append(task)
            else:
                normal_tasks.append(task)
        
        print(f"\n🧟 僵尸任务: {len(zombie_tasks)} 个")
        print(f"✅ 正常任务: {len(normal_tasks)} 个")
        
        if len(zombie_tasks) == 0:
            print("\n✅ 没有僵尸任务需要修复")
            return 0
        
        print(f"\n🔧 开始修复僵尸任务...")
        
        fixed_count = 0
        for task in zombie_tasks:
            try:
                # 使用原始 SQL 更新，绕过验证
                sql = text("""
                    UPDATE ai_tasks 
                    SET 
                        status = 'failed',
                        error_message = '{"code": "TASK_ERROR", "message": "任务在旧版本 worker 中失败，已自动清理", "failed_at": "' || :now || '"}',
                        completed_at = :now
                    WHERE id = :task_id
                """)
                
                db.execute(sql, {
                    'task_id': str(task.id),
                    'now': datetime.utcnow()
                })
                
                # 更新批次状态
                if task.batch_id:
                    batch = db.query(Batch).filter(Batch.id == task.batch_id).first()
                    if batch and batch.breakdown_status == "processing":
                        batch.breakdown_status = "failed"
                
                fixed_count += 1
                print(f"   ✅ 修复任务: {task.id} (进度: {task.progress}%)")
                
            except Exception as e:
                print(f"   ❌ 修复失败: {task.id} - {e}")
        
        db.commit()
        
        print(f"\n✅ 修复完成！")
        print(f"   修复任务数: {fixed_count}")
        print(f"   失败任务数: {len(zombie_tasks) - fixed_count}")
        
        return fixed_count
        
    except Exception as e:
        print(f"❌ 批量修复失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 0
        
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 批量修复僵尸任务工具")
    print("=" * 50)
    
    fixed = fix_all_zombie_tasks()
    
    if fixed > 0:
        print(f"\n✅ 成功修复 {fixed} 个僵尸任务")
        print(f"   现在可以重新提交这些任务了")
    else:
        print(f"\n✅ 没有需要修复的任务")

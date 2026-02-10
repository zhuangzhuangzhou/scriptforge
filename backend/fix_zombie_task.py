#!/usr/bin/env python3
"""修复僵尸任务"""
from app.core.database import SyncSessionLocal
from app.models.ai_task import AITask
from app.models.batch import Batch
from datetime import datetime

def fix_zombie_task(task_id):
    """修复僵尸任务状态"""
    db = SyncSessionLocal()
    try:
        task = db.query(AITask).filter(AITask.id == task_id).first()
        
        if not task:
            print(f"❌ 任务不存在: {task_id}")
            return False
        
        print(f"📋 当前任务状态:")
        print(f"   状态: {task.status}")
        print(f"   进度: {task.progress}%")
        print(f"   当前步骤: {task.current_step}")
        
        # 直接更新状态，绕过验证
        print(f"\n🔧 修复任务状态...")
        
        # 使用原始 SQL 更新，绕过 ORM 验证
        from sqlalchemy import text
        
        sql = text("""
            UPDATE ai_tasks 
            SET 
                status = 'failed',
                error_message = '{"code": "TASK_ERROR", "message": "任务在旧版本 worker 中失败，已自动清理", "failed_at": "' || :now || '"}',
                completed_at = :now
            WHERE id = :task_id
        """)
        
        db.execute(sql, {
            'task_id': task_id,
            'now': datetime.utcnow()
        })
        db.commit()
        
        print(f"✅ 任务状态已更新为 failed")
        
        # 更新批次状态
        if task.batch_id:
            batch = db.query(Batch).filter(Batch.id == task.batch_id).first()
            if batch and batch.breakdown_status == "processing":
                batch.breakdown_status = "failed"
                db.commit()
                print(f"✅ 批次状态已更新为 failed")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        task_id = "cbd611f0-2aea-43ef-b95c-b3943ccb0843"
    
    if fix_zombie_task(task_id):
        print(f"\n✅ 修复完成！现在可以重新提交任务了。")
    else:
        print(f"\n❌ 修复失败")

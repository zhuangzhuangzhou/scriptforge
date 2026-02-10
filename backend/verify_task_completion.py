#!/usr/bin/env python3
"""验证任务完成状态"""
from app.core.database import SyncSessionLocal
from app.models.ai_task import AITask

def verify_task(task_id):
    """验证任务状态"""
    db = SyncSessionLocal()
    try:
        task = db.query(AITask).filter(AITask.id == task_id).first()
        
        if task:
            print(f"✅ 任务验证成功！")
            print(f"   任务ID: {task.id}")
            print(f"   状态: {task.status}")
            print(f"   进度: {task.progress}%")
            print(f"   当前步骤: {task.current_step}")
            print(f"   开始时间: {task.started_at}")
            print(f"   完成时间: {task.completed_at}")
            print(f"   Celery Task ID: {task.celery_task_id}")
            
            if task.status == "completed" and task.progress == 100:
                print(f"\n🎉 任务成功完成！修复有效！")
                return True
            else:
                print(f"\n⚠️  任务状态异常")
                return False
        else:
            print(f"❌ 任务不存在: {task_id}")
            return False
            
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        task_id = "6d5cfc2f-4ace-48ba-ba4f-06fb604e7fae"  # 默认任务ID
    
    verify_task(task_id)

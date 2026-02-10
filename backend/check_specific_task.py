#!/usr/bin/env python3
"""检查特定任务的详细状态"""
from app.core.database import SyncSessionLocal
from app.models.ai_task import AITask
from app.models.batch import Batch
from datetime import datetime, timezone

def check_task(task_id):
    """检查任务详细状态"""
    db = SyncSessionLocal()
    try:
        task = db.query(AITask).filter(AITask.id == task_id).first()
        
        if not task:
            print(f"❌ 任务不存在: {task_id}")
            return
        
        print(f"📋 任务详细信息:")
        print(f"   任务ID: {task.id}")
        print(f"   状态: {task.status}")
        print(f"   进度: {task.progress}%")
        print(f"   当前步骤: {task.current_step}")
        print(f"   重试次数: {task.retry_count}")
        print(f"   Celery Task ID: {task.celery_task_id}")
        print(f"   创建时间: {task.created_at}")
        print(f"   开始时间: {task.started_at}")
        print(f"   完成时间: {task.completed_at}")
        
        # 计算运行时间
        if task.started_at:
            now = datetime.now(timezone.utc)
            started = task.started_at.replace(tzinfo=timezone.utc) if task.started_at.tzinfo is None else task.started_at
            running_time = (now - started).total_seconds()
            print(f"   运行时间: {running_time:.1f} 秒 ({running_time/60:.1f} 分钟)")
        
        if task.error_message:
            print(f"\n❌ 错误信息:")
            print(f"   {task.error_message[:500]}")
        
        # 检查批次状态
        if task.batch_id:
            batch = db.query(Batch).filter(Batch.id == task.batch_id).first()
            if batch:
                print(f"\n📦 批次信息:")
                print(f"   批次ID: {batch.id}")
                print(f"   拆解状态: {batch.breakdown_status}")
                print(f"   章节范围: {batch.start_chapter} - {batch.end_chapter}")
                print(f"   总章节数: {batch.total_chapters}")
        
        # 分析问题
        print(f"\n🔍 问题分析:")
        if task.status == "running":
            if task.started_at:
                now = datetime.now(timezone.utc)
                started = task.started_at.replace(tzinfo=timezone.utc) if task.started_at.tzinfo is None else task.started_at
                running_time = (now - started).total_seconds()
                
                if running_time > 300:  # 超过5分钟
                    print(f"   ⚠️  任务运行时间过长 ({running_time/60:.1f} 分钟)")
                    print(f"   可能原因:")
                    print(f"   1. AI 模型响应缓慢")
                    print(f"   2. 网络问题")
                    print(f"   3. 任务逻辑卡住")
                    print(f"   4. Worker 进程可能已崩溃但状态未更新")
                else:
                    print(f"   ✅ 任务正在正常执行中")
            else:
                print(f"   ⚠️  任务状态为 running 但没有开始时间")
        elif task.status == "queued":
            print(f"   ⚠️  任务还在排队中，可能 Celery worker 未运行")
        elif task.status == "failed":
            print(f"   ❌ 任务已失败")
        elif task.status == "completed":
            print(f"   ✅ 任务已完成")
        
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        task_id = "cbd611f0-2aea-43ef-b95c-b3943ccb0843"
    
    check_task(task_id)

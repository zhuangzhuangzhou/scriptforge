"""测试批次进度 API 返回的数据"""
import asyncio
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.batch import Batch
from app.models.ai_task import AITask

async def test_api():
    project_id = "4228381f-0b5e-45f1-9b82-33d5248f88d2"
    
    async with AsyncSessionLocal() as db:
        # 模拟 API 逻辑
        batches_result = await db.execute(
            select(Batch.id, Batch.batch_number, Batch.breakdown_status)
            .where(Batch.project_id == project_id)
            .order_by(Batch.batch_number)
        )
        batches = batches_result.all()
        
        # 统计各状态数量
        total = len(batches)
        completed = sum(1 for b in batches if b.breakdown_status == "completed")
        in_progress = sum(1 for b in batches if b.breakdown_status == "in_progress")
        pending = sum(1 for b in batches if b.breakdown_status == "pending")
        failed = sum(1 for b in batches if b.breakdown_status == "failed")
        
        print(f"📊 批次进度统计:")
        print(f"   - 总批次: {total}")
        print(f"   - 已完成: {completed}")
        print(f"   - 进行中: {in_progress}")
        print(f"   - 待处理: {pending}")
        print(f"   - 失败: {failed}")
        
        # 查找 in_progress 的批次
        in_progress_batch = next((b for b in batches if b.breakdown_status == "in_progress"), None)
        
        if in_progress_batch:
            print(f"\n⚠️  发现 in_progress 批次:")
            print(f"   - 批次号: {in_progress_batch.batch_number}")
            print(f"   - 批次ID: {in_progress_batch.id}")
            
            # 查询该批次的任务
            task_result = await db.execute(
                select(AITask.id, AITask.status)
                .where(AITask.batch_id == in_progress_batch.id)
                .order_by(AITask.created_at.desc())
                .limit(1)
            )
            task = task_result.first()
            
            if task:
                print(f"   - 任务ID: {task.id}")
                print(f"   - 任务状态: {task.status}")
                
                if task.status == "completed":
                    print(f"\n❌ 问题: 任务已完成但批次状态未更新!")
        else:
            print(f"\n✅ 没有 in_progress 状态的批次")
        
        # 返回 API 响应格式
        current_task = None
        if in_progress_batch:
            task_result = await db.execute(
                select(AITask.id, AITask.batch_id, AITask.status)
                .where(AITask.batch_id == in_progress_batch.id)
                .limit(1)
            )
            task = task_result.first()
            if task:
                current_task = {
                    "task_id": str(task.id),
                    "batch_id": str(task.batch_id),
                    "status": task.status
                }
        
        print(f"\n📡 API 返回数据:")
        print(f"   - total_batches: {total}")
        print(f"   - completed: {completed}")
        print(f"   - in_progress: {in_progress}")
        print(f"   - pending: {pending}")
        print(f"   - failed: {failed}")
        print(f"   - current_task: {current_task}")

if __name__ == "__main__":
    asyncio.run(test_api())

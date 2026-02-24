"""修复批次 6 的状态"""
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.batch import Batch
from app.models.ai_task import AITask

async def fix_batch():
    async with AsyncSessionLocal() as db:
        # 查询批次 6
        batch_result = await db.execute(
            select(Batch).where(Batch.id == "369b0cac-7979-450a-9e12-a1a838ca36ca")
        )
        batch = batch_result.scalar_one()
        
        # 查询任务
        task_result = await db.execute(
            select(AITask)
            .where(AITask.batch_id == batch.id)
            .order_by(AITask.created_at.desc())
            .limit(1)
        )
        task = task_result.scalar_one()
        
        print(f"📋 批次 6 当前状态:")
        print(f"   - 批次状态: {batch.breakdown_status}")
        print(f"   - 任务状态: {task.status}")
        
        if task.status == "completed" and batch.breakdown_status != "completed":
            batch.breakdown_status = "completed"
            await db.commit()
            print(f"\n✅ 已修复批次状态为 completed")
        else:
            print(f"\n✓ 状态正常,无需修复")

if __name__ == "__main__":
    asyncio.run(fix_batch())

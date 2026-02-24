"""测试批次状态更新是否正常"""
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.batch import Batch
from app.models.ai_task import AITask

async def check_batch_status():
    async with AsyncSessionLocal() as db:
        # 查找第一个 pending 状态的批次
        result = await db.execute(
            select(Batch)
            .where(Batch.breakdown_status == "pending")
            .order_by(Batch.batch_number)
            .limit(1)
        )
        batch = result.scalar_one_or_none()
        
        if not batch:
            print("❌ 没有找到 pending 状态的批次")
            return
        
        print(f"✅ 找到待拆解批次:")
        print(f"   - 批次号: {batch.batch_number}")
        print(f"   - 批次ID: {batch.id}")
        print(f"   - 项目ID: {batch.project_id}")
        print(f"   - 当前状态: {batch.breakdown_status}")
        
        # 检查是否有关联的任务
        task_result = await db.execute(
            select(AITask)
            .where(AITask.batch_id == batch.id)
            .order_by(AITask.created_at.desc())
        )
        tasks = task_result.scalars().all()
        
        if tasks:
            print(f"\n📋 关联任务:")
            for task in tasks:
                print(f"   - 任务ID: {task.id}")
                print(f"   - 状态: {task.status}")
                print(f"   - 创建时间: {task.created_at}")
        else:
            print("\n📋 暂无关联任务")
        
        return batch

if __name__ == "__main__":
    asyncio.run(check_batch_status())

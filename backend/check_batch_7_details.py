"""检查批次 7 的详细信息"""
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.batch import Batch
from app.models.ai_task import AITask
from app.models.plot_breakdown import PlotBreakdown

async def check_batch():
    async with AsyncSessionLocal() as db:
        # 查询批次 7
        batch_result = await db.execute(
            select(Batch).where(Batch.id == "9e6c9f12-e7c8-473e-ae2d-0efe68aa2baa")
        )
        batch = batch_result.scalar_one()
        
        print(f"📋 批次 7 详细信息:")
        print(f"   - 批次号: {batch.batch_number}")
        print(f"   - 批次状态: {batch.breakdown_status}")
        print(f"   - 更新时间: {batch.updated_at}")
        
        # 查询任务
        task_result = await db.execute(
            select(AITask)
            .where(AITask.batch_id == batch.id)
            .order_by(AITask.created_at.desc())
        )
        tasks = task_result.scalars().all()
        
        print(f"\n📝 关联任务 ({len(tasks)} 个):")
        for task in tasks:
            print(f"   - 任务ID: {task.id}")
            print(f"   - 状态: {task.status}")
            print(f"   - 进度: {task.progress}%")
            print(f"   - 完成时间: {task.completed_at}")
            print(f"   - Celery任务ID: {task.celery_task_id}")
        
        # 查询拆解结果
        breakdown_result = await db.execute(
            select(PlotBreakdown)
            .where(PlotBreakdown.batch_id == batch.id)
            .order_by(PlotBreakdown.created_at.desc())
            .limit(1)
        )
        breakdown = breakdown_result.scalar_one_or_none()
        
        if breakdown:
            print(f"\n✅ 拆解结果:")
            print(f"   - 结果ID: {breakdown.id}")
            print(f"   - 剧情点数量: {len(breakdown.plot_points) if breakdown.plot_points else 0}")
            print(f"   - 创建时间: {breakdown.created_at}")
        else:
            print(f"\n❌ 没有找到拆解结果")

if __name__ == "__main__":
    asyncio.run(check_batch())

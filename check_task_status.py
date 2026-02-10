#!/usr/bin/env python3
"""检查任务和批次状态"""
import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import sys
sys.path.insert(0, 'backend')

from app.core.database import AsyncSessionLocal
from app.models.ai_task import AITask
from app.models.batch import Batch

async def check_status():
    async with AsyncSessionLocal() as db:
        # 查询所有任务状态
        task_result = await db.execute(
            select(
                AITask.status,
                func.count(AITask.id).label('count')
            ).group_by(AITask.status)
        )
        
        print("=" * 60)
        print("📊 任务状态统计")
        print("=" * 60)
        for row in task_result:
            print(f"  {row.status:15s}: {row.count} 个任务")
        
        # 查询所有批次状态
        batch_result = await db.execute(
            select(
                Batch.breakdown_status,
                func.count(Batch.id).label('count')
            ).group_by(Batch.breakdown_status)
        )
        
        print()
        print("=" * 60)
        print("📦 批次状态统计")
        print("=" * 60)
        for row in batch_result:
            print(f"  {row.breakdown_status:15s}: {row.count} 个批次")
        
        # 查询状态不一致的情况
        print()
        print("=" * 60)
        print("⚠️  状态不一致检查")
        print("=" * 60)
        
        # 查询有 queued/running 任务但批次状态是 pending 的情况
        inconsistent_result = await db.execute(
            select(Batch, AITask).join(
                AITask, Batch.id == AITask.batch_id
            ).where(
                AITask.status.in_(['queued', 'running']),
                Batch.breakdown_status == 'pending'
            )
        )
        
        inconsistent = inconsistent_result.all()
        if inconsistent:
            print(f"\n  发现 {len(inconsistent)} 个状态不一致的批次:")
            for batch, task in inconsistent:
                print(f"    批次 {batch.batch_number}: breakdown_status={batch.breakdown_status}, 任务状态={task.status}")
        else:
            print("  ✅ 未发现状态不一致")
        
        # 查询有任务但状态不匹配的批次
        print()
        print("=" * 60)
        print("🔍 批次与任务状态对比")
        print("=" * 60)
        
        all_batches_result = await db.execute(
            select(Batch).order_by(Batch.batch_number)
        )
        batches = all_batches_result.scalars().all()
        
        for batch in batches[:10]:  # 只显示前10个
            task_result = await db.execute(
                select(AITask).where(
                    AITask.batch_id == batch.id,
                    AITask.task_type == 'breakdown'
                ).order_by(AITask.created_at.desc())
            )
            tasks = task_result.scalars().all()
            
            if tasks:
                latest_task = tasks[0]
                status_match = "✅" if batch.breakdown_status == latest_task.status else "❌"
                print(f"  {status_match} 批次 {batch.batch_number}: batch_status={batch.breakdown_status:12s}, task_status={latest_task.status:12s}, tasks={len(tasks)}")
            else:
                print(f"  ⚪ 批次 {batch.batch_number}: batch_status={batch.breakdown_status:12s}, 无任务")

if __name__ == "__main__":
    asyncio.run(check_status())

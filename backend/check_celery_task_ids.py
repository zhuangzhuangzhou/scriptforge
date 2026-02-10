#!/usr/bin/env python3
"""检查任务的 Celery Task ID"""
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.ai_task import AITask


async def check_celery_ids():
    """检查 Celery Task ID"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AITask)
            .where(AITask.status == "queued")
            .order_by(AITask.created_at.desc())
            .limit(10)
        )
        tasks = result.scalars().all()
        
        print(f"📋 检查 {len(tasks)} 个排队中的任务:\n")
        
        for task in tasks:
            print(f"任务ID: {task.id}")
            print(f"  Celery Task ID: {task.celery_task_id}")
            print(f"  创建时间: {task.created_at}")
            print()


if __name__ == "__main__":
    asyncio.run(check_celery_ids())

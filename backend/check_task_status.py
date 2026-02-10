#!/usr/bin/env python3
"""检查任务状态"""
import asyncio
import sys
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.ai_task import AITask


async def check_tasks():
    """检查所有排队中的任务"""
    async with AsyncSessionLocal() as db:
        # 查询所有 queued 状态的任务
        result = await db.execute(
            select(AITask)
            .where(AITask.status == "queued")
            .order_by(AITask.created_at.desc())
            .limit(10)
        )
        tasks = result.scalars().all()
        
        if not tasks:
            print("✅ 没有排队中的任务")
            return
        
        print(f"📋 找到 {len(tasks)} 个排队中的任务:\n")
        
        for task in tasks:
            print(f"任务ID: {task.id}")
            print(f"  状态: {task.status}")
            print(f"  进度: {task.progress}%")
            print(f"  当前步骤: {task.current_step}")
            print(f"  创建时间: {task.created_at}")
            print(f"  重试次数: {task.retry_count}")
            if task.error_message:
                print(f"  错误信息: {task.error_message[:100]}...")
            print()


if __name__ == "__main__":
    asyncio.run(check_tasks())

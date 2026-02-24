#!/usr/bin/env python3
"""修复卡在 cancelling 状态的任务"""

import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.ai_task import AITask
from app.models.batch import Batch
from app.core.status import TaskStatus, BatchStatus


async def fix_stuck_cancelling_task():
    """修复卡在 cancelling 状态的任务"""
    async with AsyncSessionLocal() as db:
        # 查询所有 cancelling 状态的任务
        result = await db.execute(
            select(AITask).where(AITask.status == TaskStatus.CANCELLING)
        )
        tasks = result.scalars().all()

        if not tasks:
            print("✅ 没有找到卡在 cancelling 状态的任务")
            return

        print(f"找到 {len(tasks)} 个卡在 cancelling 状态的任务\n")

        for task in tasks:
            print(f"任务 ID: {task.id}")
            print(f"  批次 ID: {task.batch_id}")
            print(f"  任务类型: {task.task_type}")
            print(f"  创建时间: {task.created_at}")
            print(f"  Celery 任务 ID: {task.celery_task_id}")

            # 更新任务状态为 canceled
            task.status = TaskStatus.CANCELED
            task.completed_at = datetime.now(timezone.utc)
            task.error_message = "任务取消操作超时，已自动标记为已取消"

            # 检查批次是否有之前的成功结果
            batch_result = await db.execute(
                select(Batch).where(Batch.id == task.batch_id)
            )
            batch = batch_result.scalar_one_or_none()

            if batch:
                # 检查是否有其他成功的任务
                other_tasks_result = await db.execute(
                    select(AITask).where(
                        AITask.batch_id == batch.id,
                        AITask.id != task.id,
                        AITask.status == TaskStatus.COMPLETED
                    )
                )
                other_successful_tasks = other_tasks_result.scalars().all()

                if other_successful_tasks:
                    # 有之前的成功结果，保持批次状态
                    print(f"  ✅ 批次有之前的成功结果，保持状态: {batch.breakdown_status}")
                else:
                    # 没有成功结果，更新批次状态为 pending（允许重试）
                    if task.task_type == "breakdown":
                        batch.breakdown_status = BatchStatus.PENDING
                    elif task.task_type in ("script", "episode_script"):
                        batch.script_status = BatchStatus.PENDING
                    print(f"  ⚠️  批次无成功结果，状态更新为: pending")

            print(f"  ✅ 任务状态已更新为: {TaskStatus.CANCELED}\n")

        # 提交更改
        await db.commit()
        print(f"✅ 成功修复 {len(tasks)} 个卡住的任务")


if __name__ == "__main__":
    asyncio.run(fix_stuck_cancelling_task())

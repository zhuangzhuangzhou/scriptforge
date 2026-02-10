#!/usr/bin/env python3
"""测试 Celery 任务执行"""
import asyncio
import uuid
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.ai_task import AITask
from app.models.batch import Batch
from app.models.user import User
from app.tasks.breakdown_tasks import run_breakdown_task


async def create_test_task():
    """创建一个测试任务"""
    async with AsyncSessionLocal() as db:
        # 查找一个用户
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ 没有找到用户")
            return
        
        # 查找一个批次
        result = await db.execute(
            select(Batch)
            .limit(1)
        )
        batch = result.scalar_one_or_none()
        
        if not batch:
            print("❌ 没有找到批次")
            return
        
        # 创建测试任务
        task_id = str(uuid.uuid4())
        task = AITask(
            id=task_id,
            project_id=batch.project_id,
            batch_id=batch.id,
            task_type="breakdown",
            status="queued",
            progress=0,
            config={}
        )
        
        db.add(task)
        await db.commit()
        
        print(f"✅ 创建测试任务: {task_id}")
        print(f"   用户ID: {user.id}")
        print(f"   批次ID: {batch.id}")
        print(f"   项目ID: {batch.project_id}")
        
        # 提交到 Celery
        print("\n🚀 提交任务到 Celery...")
        celery_task = run_breakdown_task.delay(
            task_id=task_id,
            batch_id=batch.id,
            project_id=batch.project_id,
            user_id=user.id
        )
        
        # 更新 celery_task_id
        task.celery_task_id = celery_task.id
        await db.commit()
        
        print(f"✅ Celery Task ID: {celery_task.id}")
        print(f"\n⏳ 等待任务执行...")
        print(f"   可以通过以下命令查看日志:")
        print(f"   tail -f backend/celery.log")
        
        return task_id


if __name__ == "__main__":
    task_id = asyncio.run(create_test_task())
    if task_id:
        print(f"\n📊 查看任务状态:")
        print(f"   curl http://localhost:8000/api/v1/breakdown/tasks/{task_id}")

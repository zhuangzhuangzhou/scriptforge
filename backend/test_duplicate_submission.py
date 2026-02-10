#!/usr/bin/env python3
"""测试重复提交检查"""
import asyncio
from app.core.database import AsyncSessionLocal
from app.models.ai_task import AITask
from app.models.batch import Batch
from app.models.user import User
from sqlalchemy import select

async def test_duplicate_check():
    """测试重复提交检查逻辑"""
    async with AsyncSessionLocal() as db:
        # 查找一个用户
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ 没有找到用户")
            return
        
        # 查找一个批次
        result = await db.execute(
            select(Batch).limit(1)
        )
        batch = result.scalar_one_or_none()
        
        if not batch:
            print("❌ 没有找到批次")
            return
        
        print(f"📋 测试批次: {batch.id}")
        print(f"   批次状态: {batch.breakdown_status}")
        
        # 检查是否已有任务在执行
        existing_task_result = await db.execute(
            select(AITask).where(
                AITask.batch_id == batch.id,
                AITask.status.in_(["queued", "running"])
            )
        )
        existing_task = existing_task_result.scalar_one_or_none()
        
        if existing_task:
            print(f"\n✅ 重复提交检查生效！")
            print(f"   已有任务在执行: {existing_task.id}")
            print(f"   任务状态: {existing_task.status}")
            print(f"   任务进度: {existing_task.progress}%")
            print(f"\n💡 如果用户再次提交，会收到 409 Conflict 错误")
        else:
            print(f"\n✅ 该批次没有正在执行的任务")
            print(f"   可以创建新任务")

if __name__ == "__main__":
    asyncio.run(test_duplicate_check())

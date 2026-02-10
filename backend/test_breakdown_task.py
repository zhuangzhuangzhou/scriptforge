"""测试 breakdown 任务执行"""
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.ai_task import AITask
from app.models.batch import Batch
from app.models.user import User
from app.tasks.breakdown_tasks import run_breakdown_task

async def test_task():
    task_id = "0ee986ae-78ce-4ec1-a64f-ef44465a4854"
    
    async with AsyncSessionLocal() as db:
        # 获取任务信息
        result = await db.execute(
            select(AITask).where(AITask.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            print(f"任务不存在: {task_id}")
            return
        
        print(f"任务ID: {task.id}")
        print(f"批次ID: {task.batch_id}")
        print(f"项目ID: {task.project_id}")
        
        # 获取批次信息
        batch_result = await db.execute(
            select(Batch).where(Batch.id == task.batch_id)
        )
        batch = batch_result.scalar_one_or_none()
        
        if not batch:
            print(f"批次不存在: {task.batch_id}")
            return
        
        print(f"批次号: {batch.batch_number}")
        print(f"章节范围: {batch.start_chapter} - {batch.end_chapter}")
        
        # 获取用户信息
        user_result = await db.execute(
            select(User).where(User.id.in_(
                select(Batch.project_id).where(Batch.id == task.batch_id)
            ))
        )
        
        # 通过项目获取用户
        from app.models.project import Project
        project_result = await db.execute(
            select(Project).where(Project.id == task.project_id)
        )
        project = project_result.scalar_one_or_none()
        
        if not project:
            print(f"项目不存在: {task.project_id}")
            return
        
        print(f"用户ID: {project.user_id}")
        
        # 尝试手动执行任务（同步方式）
        print("\n开始执行任务...")
        try:
            result = run_breakdown_task(
                str(task.id),
                str(task.batch_id),
                str(task.project_id),
                str(project.user_id)
            )
            print(f"任务执行结果: {result}")
        except Exception as e:
            print(f"任务执行失败: {e}")
            import traceback
            traceback.print_exc()

asyncio.run(test_task())

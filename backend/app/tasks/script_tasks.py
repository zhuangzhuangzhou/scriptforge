from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.ai.adapters import get_adapter
from app.ai.pipeline_executor import PipelineExecutor
from app.core.progress import update_task_progress
from app.core.credits import CreditsService, SCRIPT_BASE_CREDITS
from app.models.ai_task import AITask
from app.models.batch import Batch
from sqlalchemy import select


@celery_app.task(bind=True)
def run_script_task(self, task_id: str, batch_id: str, project_id: str, breakdown_id: str, user_id: str):
    """执行Script任务"""
    import asyncio

    async def _run():
        async with AsyncSessionLocal() as db:
            batch_record = None
            try:
                # 任务开始：更新状态为 running
                await update_task_progress(
                    db, task_id,
                    status="running",
                    progress=0,
                    current_step="初始化任务"
                )

                # 更新批次状态为 processing
                batch_result = await db.execute(
                    select(Batch).where(Batch.id == batch_id)
                )
                batch_record = batch_result.scalar_one_or_none()
                if batch_record:
                    batch_record.script_status = "processing"
                    await db.commit()

                # 读取任务配置（获取选择的 skills / pipeline）
                task_result = await db.execute(
                    select(AITask).where(AITask.id == task_id)
                )
                task_record = task_result.scalar_one_or_none()
                task_config = task_record.config if task_record else {}

                # 创建模型适配器（统一入口）
                model_adapter = await get_adapter()

                # 定义进度回调函数
                async def progress_callback(step: str, progress: int):
                    await update_task_progress(
                        db, task_id,
                        progress=progress,
                        current_step=step
                    )

                # 各阶段进度更新
                await progress_callback("加载拆解数据", 10)

                # 使用配置驱动的 Pipeline 执行
                executor = PipelineExecutor(
                    db=db,
                    model_adapter=model_adapter,
                    user_id=user_id
                )

                await executor.run_script(
                    project_id=project_id,
                    batch_id=batch_id,
                    breakdown_id=breakdown_id,
                    pipeline_id=task_config.get("pipeline_id"),
                    selected_skills=task_config.get("selected_skills"),
                    progress_callback=progress_callback
                )

                # 任务完成：更新状态
                await update_task_progress(
                    db, task_id,
                    status="completed",
                    progress=100,
                    current_step="任务完成"
                )

                # 更新批次状态为 completed
                if batch_record:
                    batch_record.script_status = "completed"
                    await db.commit()

                # 任务成功完成后扣费
                credits_service = CreditsService(db)
                await credits_service.consume_credits(
                    user_id=user_id,
                    amount=SCRIPT_BASE_CREDITS,
                    description=f"剧本生成 - 批次 {batch_id}",
                    reference_id=task_id
                )
                await db.commit()

                return {"status": "completed"}

            except Exception as e:
                # 任务失败：更新状态和错误信息
                await update_task_progress(
                    db, task_id,
                    status="failed",
                    error_message=str(e)
                )
                if batch_record:
                    batch_record.script_status = "failed"
                    await db.commit()
                raise

    return asyncio.run(_run())

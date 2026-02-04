from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.ai.adapters import OpenAIAdapter
from app.ai.graph.script_workflow import create_script_workflow
from app.core.config import settings
from app.core.progress import update_task_progress


@celery_app.task(bind=True)
def run_script_task(self, task_id: str, batch_id: str, project_id: str, breakdown_id: str):
    """执行Script任务"""
    import asyncio

    async def _run():
        async with AsyncSessionLocal() as db:
            try:
                # 任务开始：更新状态为 running
                await update_task_progress(
                    db, task_id,
                    status="running",
                    progress=0,
                    current_step="初始化任务"
                )

                # 创建模型适配器
                model_adapter = OpenAIAdapter(
                    api_key=settings.OPENAI_API_KEY,
                    model_name=settings.OPENAI_MODEL
                )

                # 定义进度回调函数
                async def progress_callback(step: str, progress: int):
                    await update_task_progress(
                        db, task_id,
                        progress=progress,
                        current_step=step
                    )

                # 创建工作流
                workflow = create_script_workflow(model_adapter, db)

                # 执行工作流，传入进度回调
                initial_state = {
                    "batch_id": batch_id,
                    "project_id": project_id,
                    "breakdown_id": breakdown_id,
                    "breakdown_data": {},
                    "episodes": [],
                    "scenes": [],
                    "dialogues": [],
                    "current_step": "",
                    "progress": 0,
                    "errors": [],
                    "progress_callback": progress_callback,
                }

                # 各阶段进度更新
                await progress_callback("加载拆解数据", 10)
                result = await workflow.ainvoke(initial_state)

                # 任务完成：更新状态
                await update_task_progress(
                    db, task_id,
                    status="completed",
                    progress=100,
                    current_step="任务完成"
                )

                return result

            except Exception as e:
                # 任务失败：更新状态和错误信息
                await update_task_progress(
                    db, task_id,
                    status="failed",
                    error_message=str(e)
                )
                raise

    return asyncio.run(_run())

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.ai.adapters import OpenAIAdapter
from app.ai.graph.breakdown_workflow import create_breakdown_workflow
from app.core.config import settings


@celery_app.task(bind=True)
def run_breakdown_task(self, task_id: str, batch_id: str, project_id: str):
    """执行Breakdown任务"""
    import asyncio

    async def _run():
        async with AsyncSessionLocal() as db:
            # 创建模型适配器
            model_adapter = OpenAIAdapter(
                api_key=settings.OPENAI_API_KEY,
                model_name=settings.OPENAI_MODEL
            )

            # 创建工作流
            workflow = create_breakdown_workflow(model_adapter, db)

            # 执行工作流
            initial_state = {
                "batch_id": batch_id,
                "project_id": project_id,
                "chapters": [],
                "conflicts": [],
                "plot_hooks": [],
                "characters": [],
                "scenes": [],
                "emotions": [],
                "current_step": "",
                "progress": 0,
                "errors": []
            }

            result = await workflow.ainvoke(initial_state)
            return result

    return asyncio.run(_run())

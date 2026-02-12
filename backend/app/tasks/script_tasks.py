"""单集剧本创作 Celery 任务

支持两种模式：
1. 批量模式（旧版）：基于 batch_id 和 breakdown_id 生成所有剧集
2. 单集模式（新版）：基于 breakdown_id 和 episode_number 生成单集剧本
"""
import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.celery_app import celery_app
from app.core.database import SyncSessionLocal, AsyncSessionLocal
from app.core.progress import update_task_progress, update_task_progress_sync
from app.core.credits import CreditsService, consume_credits_for_task_sync
from app.core.exceptions import AITaskException, RetryableError, classify_exception
from app.models.ai_task import AITask
from app.models.batch import Batch
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

# Celery 任务配置
CELERY_TASK_CONFIG = {
    "bind": True,
    "autoretry_for": (RetryableError, TimeoutError, ConnectionError),
    "retry_kwargs": {"max_retries": 3, "countdown": 60},
    "retry_backoff": True,
    "retry_backoff_max": 600,
    "retry_jitter": True,
    "acks_late": True,
    "reject_on_worker_lost": True,
}


@celery_app.task(bind=True)
def run_script_task(self, task_id: str, batch_id: str, project_id: str, breakdown_id: str, user_id: str):
    """执行 Script 任务（批量模式，旧版兼容）"""
    import asyncio

    async def _run():
        async with AsyncSessionLocal() as db:
            batch_record = None
            try:
                await update_task_progress(db, task_id, status="running", progress=0, current_step="初始化任务")

                batch_result = await db.execute(select(Batch).where(Batch.id == batch_id))
                batch_record = batch_result.scalar_one_or_none()
                if batch_record:
                    batch_record.script_status = "processing"
                    await db.commit()

                task_result = await db.execute(select(AITask).where(AITask.id == task_id))
                task_record = task_result.scalar_one_or_none()
                task_config = task_record.config if task_record else {}

                from app.ai.adapters import get_adapter
                model_id = task_config.get("model_id")
                model_adapter = await get_adapter(model_id=model_id, user_id=user_id, db=db)

                async def progress_callback(step: str, progress: int):
                    await update_task_progress(db, task_id, progress=progress, current_step=step)

                await progress_callback("加载拆解数据", 10)

                from app.ai.pipeline_executor import PipelineExecutor
                executor = PipelineExecutor(db=db, model_adapter=model_adapter, user_id=user_id)

                await executor.run_script(
                    project_id=project_id,
                    batch_id=batch_id,
                    breakdown_id=breakdown_id,
                    pipeline_id=task_config.get("pipeline_id"),
                    selected_skills=task_config.get("selected_skills"),
                    progress_callback=progress_callback
                )

                await update_task_progress(db, task_id, status="completed", progress=100, current_step="任务完成")

                if batch_record:
                    batch_record.script_status = "completed"
                    await db.commit()

                # 扣除积分（使用数据库配置）
                credits_service = CreditsService(db)
                credits_result = await credits_service.consume_credits_for_task(
                    user=await db.get(User, user_id),
                    task_type="script",
                    reference_id=task_id
                )
                if not credits_result["success"]:
                    logger.warning(f"积分扣费失败: {credits_result['message']}")
                await db.commit()

                return {"status": "completed"}

            except Exception as e:
                await update_task_progress(db, task_id, status="failed", error_message=str(e))
                if batch_record:
                    batch_record.script_status = "failed"
                    await db.commit()
                raise

    return asyncio.run(_run())


@celery_app.task(**CELERY_TASK_CONFIG)
def run_episode_script_task(
    self,
    task_id: str,
    breakdown_id: str,
    episode_number: int,
    project_id: str,
    user_id: str
):
    """执行单集剧本创作任务（新版）

    Args:
        task_id: 任务 ID
        breakdown_id: 剧情拆解 ID
        episode_number: 集数
        project_id: 项目 ID
        user_id: 用户 ID
    """
    db = SyncSessionLocal()
    log_publisher = None

    try:
        from app.core.redis_log_publisher import RedisLogPublisher
        try:
            log_publisher = RedisLogPublisher()
        except Exception as e:
            logger.warning(f"初始化 RedisLogPublisher 失败: {e}")

        update_task_progress_sync(db, task_id, status="running", progress=0, current_step="初始化剧本创作任务... (0%)")

        task_record = db.query(AITask).filter(AITask.id == task_id).first()
        task_config = task_record.config if task_record else {}

        model_id = task_config.get("model_config_id")
        if not model_id:
            raise ValueError("任务配置中缺少 model_config_id")

        from app.ai.adapters import get_adapter_sync
        model_adapter = get_adapter_sync(db=db, model_id=model_id, user_id=user_id)

        result = _execute_episode_script_sync(
            db=db, task_id=task_id, breakdown_id=breakdown_id,
            episode_number=episode_number, project_id=project_id,
            model_adapter=model_adapter, task_config=task_config,
            log_publisher=log_publisher
        )

        update_task_progress_sync(db, task_id, status="completed", progress=100, current_step="剧本创作完成 (100%)")

        # 扣除积分（任务完成后扣费）
        credits_result = consume_credits_for_task_sync(db, user_id, "script", task_id)
        if not credits_result["success"]:
            logger.warning(f"积分扣费失败: {credits_result['message']}")

        return {"status": "completed", "task_id": task_id, **result}

    except Exception as e:
        classified_error = classify_exception(e)
        error_info = {"code": getattr(classified_error, "code", "UNKNOWN_ERROR"), "message": str(e)}
        update_task_progress_sync(db, task_id, status="failed", error_message=json.dumps(error_info))
        if log_publisher:
            log_publisher.publish_error(task_id, str(e), error_code=error_info["code"])
        raise

    finally:
        if log_publisher:
            try:
                log_publisher.close()
            except Exception:
                pass
        db.close()


def _execute_episode_script_sync(
    db: Session, task_id: str, breakdown_id: str, episode_number: int,
    project_id: str, model_adapter, task_config: dict, log_publisher=None
) -> dict:
    """执行单集剧本创作"""
    from app.models.plot_breakdown import PlotBreakdown
    from app.models.chapter import Chapter
    from app.ai.simple_executor import SimpleSkillExecutor
    from app.core.init_ai_resources import load_layered_resources_sync

    # 1. 加载剧情拆解
    update_task_progress_sync(db, task_id, progress=5, current_step="加载剧情拆解结果... (5%)")
    breakdown = db.query(PlotBreakdown).filter(PlotBreakdown.id == breakdown_id).first()
    if not breakdown:
        raise AITaskException(code="DATA_NOT_FOUND", message=f"剧情拆解 {breakdown_id} 不存在")

    # 2. 筛选本集剧情点
    update_task_progress_sync(db, task_id, progress=10, current_step=f"筛选第 {episode_number} 集剧情点... (10%)")
    episode_plot_points = [
        pp for pp in (breakdown.plot_points or [])
        if isinstance(pp, dict) and pp.get("episode") == episode_number
    ]
    if not episode_plot_points:
        raise AITaskException(code="NO_PLOT_POINTS", message=f"第 {episode_number} 集没有剧情点")

    # 3. 加载章节原文
    update_task_progress_sync(db, task_id, progress=15, current_step="加载章节原文... (15%)")
    source_chapters = {pp.get("source_chapter") for pp in episode_plot_points if pp.get("source_chapter")}
    chapters = db.query(Chapter).filter(
        Chapter.batch_id == breakdown.batch_id,
        Chapter.chapter_number.in_(source_chapters) if source_chapters else True
    ).order_by(Chapter.chapter_number).limit(10).all()
    chapters_text = "\n\n".join([f"## 第 {ch.chapter_number} 章\n{ch.content or ''}" for ch in chapters])

    # 4. 加载 AI 资源
    update_task_progress_sync(db, task_id, progress=20, current_step="加载 AI 资源... (20%)")
    novel_type = task_config.get("novel_type")
    resources = load_layered_resources_sync(db, stage="script", novel_type=novel_type)
    adapt_method = "\n\n---\n\n".join([v for v in [resources.get("core"), resources.get("script"), resources.get("type")] if v])

    # 5. 生成剧本
    update_task_progress_sync(db, task_id, progress=30, current_step=f"生成第 {episode_number} 集剧本... (30%)")
    skill_executor = SimpleSkillExecutor(db, model_adapter, log_publisher)

    try:
        script_result = skill_executor.execute_skill(
            skill_name="webtoon_script",
            inputs={
                "plot_points": json.dumps(episode_plot_points, ensure_ascii=False),
                "chapters_text": chapters_text[:5000],
                "adapt_method": adapt_method,
                "episode_number": str(episode_number)
            },
            task_id=task_id
        )
    except Exception as e:
        raise AITaskException(code="SKILL_EXECUTION_ERROR", message=f"剧本生成失败: {str(e)}")

    update_task_progress_sync(db, task_id, progress=70, current_step="剧本生成完成 (70%)")

    # 6. 保存结果
    update_task_progress_sync(db, task_id, progress=90, current_step="保存剧本... (90%)")

    full_script = script_result.get("full_script", "") if isinstance(script_result, dict) else str(script_result)
    title = script_result.get("title", f"第 {episode_number} 集") if isinstance(script_result, dict) else f"第 {episode_number} 集"

    return {
        "episode_number": episode_number,
        "title": title,
        "word_count": len(full_script),
        "script": script_result
    }

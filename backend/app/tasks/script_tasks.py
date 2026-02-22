"""单集剧本创作 Celery 任务

基于 breakdown_id 和 episode_number 生成单集剧本。

积分策略：
- API 层预扣积分（scripts.py）
- 任务成功完成：不退款（积分已预扣）
- 任务失败：自动退款（保持公平）
"""
import json
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.core.database import SyncSessionLocal
from app.core.progress import update_task_progress_sync
from app.core.status import TaskStatus
from app.core.exceptions import AITaskException, RetryableError, classify_exception
from app.models.ai_task import AITask
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

        update_task_progress_sync(db, task_id, status=TaskStatus.RUNNING, progress=0, current_step="初始化剧本创作任务... (0%)")

        # 发布任务开始日志
        if log_publisher:
            log_publisher.publish_info(
                task_id,
                f"🎬 开始生成第 {episode_number} 集剧本..."
            )

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

        update_task_progress_sync(db, task_id, status=TaskStatus.COMPLETED, progress=100, current_step="剧本创作完成 (100%)")

        # 发布任务完成日志
        if log_publisher:
            log_publisher.publish_task_complete(
                task_id,
                status=TaskStatus.COMPLETED,
                message=f"✅ 第 {episode_number} 集剧本生成完成！"
            )

        # 注意：积分已在 API 层预扣，无需在这里扣费

        return {"status": TaskStatus.COMPLETED, "task_id": task_id, **result}

    except Exception as e:
        classified_error = classify_exception(e)
        error_info = {"code": getattr(classified_error, "code", "UNKNOWN_ERROR"), "message": str(e)}
        update_task_progress_sync(db, task_id, status=TaskStatus.FAILED, error_message=json.dumps(error_info))

        # 失败时退还预扣的积分
        try:
            from app.core.quota import refund_episode_quota_sync
            refund_episode_quota_sync(db, user_id, 1, auto_commit=False)
            db.commit()
            logger.info(f"任务失败，已退还预扣积分: user_id={user_id}, task_id={task_id}")
        except Exception as refund_error:
            logger.error(f"退还积分失败: {refund_error}")
            db.rollback()

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
    if log_publisher:
        log_publisher.publish_step_start(task_id, "load_breakdown", "加载剧情拆解结果")

    breakdown = db.query(PlotBreakdown).filter(PlotBreakdown.id == breakdown_id).first()
    if not breakdown:
        raise AITaskException(code="DATA_NOT_FOUND", message=f"剧情拆解 {breakdown_id} 不存在")

    if log_publisher:
        log_publisher.publish_step_end(task_id, "load_breakdown", {"status": "completed", "plot_points_count": len(breakdown.plot_points or [])})

    # 2. 筛选本集剧情点
    update_task_progress_sync(db, task_id, progress=10, current_step=f"筛选第 {episode_number} 集剧情点... (10%)")
    if log_publisher:
        log_publisher.publish_step_start(task_id, "filter_plot_points", "筛选本集剧情点")

    episode_plot_points = [
        pp for pp in (breakdown.plot_points or [])
        if isinstance(pp, dict) and pp.get("episode") == episode_number
    ]
    if not episode_plot_points:
        raise AITaskException(code="NO_PLOT_POINTS", message=f"第 {episode_number} 集没有剧情点")

    if log_publisher:
        log_publisher.publish_step_end(task_id, "filter_plot_points", {"status": "completed", "episode": episode_number, "count": len(episode_plot_points)})

    # 3. 加载章节原文
    update_task_progress_sync(db, task_id, progress=15, current_step="加载章节原文... (15%)")
    if log_publisher:
        log_publisher.publish_step_start(task_id, "load_chapters", "加载章节原文")

    source_chapters = {pp.get("source_chapter") for pp in episode_plot_points if pp.get("source_chapter")}
    chapters = db.query(Chapter).filter(
        Chapter.batch_id == breakdown.batch_id,
        Chapter.chapter_number.in_(source_chapters) if source_chapters else True
    ).order_by(Chapter.chapter_number).limit(10).all()
    chapters_text = "\n\n".join([f"## 第 {ch.chapter_number} 章\n{ch.content or ''}" for ch in chapters])

    if log_publisher:
        log_publisher.publish_step_end(task_id, "load_chapters", {"status": "completed", "chapters_loaded": len(chapters)})

    # 4. 加载 AI 资源
    update_task_progress_sync(db, task_id, progress=20, current_step="加载 AI 资源... (20%)")
    if log_publisher:
        log_publisher.publish_step_start(task_id, "load_resources", "加载 AI 资源")

    novel_type = task_config.get("novel_type")
    resources = load_layered_resources_sync(db, stage="script", novel_type=novel_type)
    adapt_method = "\n\n---\n\n".join([v for v in [resources.get("core"), resources.get("script"), resources.get("type")] if v])

    if log_publisher:
        log_publisher.publish_step_end(task_id, "load_resources", {"status": "completed"})

    # 5. 生成剧本
    update_task_progress_sync(db, task_id, progress=30, current_step=f"生成第 {episode_number} 集剧本... (30%)")
    if log_publisher:
        log_publisher.publish_step_start(task_id, "generate_script", "生成剧本内容")

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

    # 剧本生成完成
    if log_publisher:
        log_publisher.publish_step_end(
            task_id,
            "generate_script",
            {"status": "completed", "word_count": len(script_result.get("full_script", "") if isinstance(script_result, dict) else 0)}
        )

    update_task_progress_sync(db, task_id, progress=70, current_step="剧本生成完成 (70%)")

    # 6. 保存结果到数据库
    update_task_progress_sync(db, task_id, progress=90, current_step="保存剧本... (90%)")
    if log_publisher:
        log_publisher.publish_info(task_id, "💾 保存剧本到数据库...")

    from app.models.script import Script

    # 提取剧本数据
    full_script = script_result.get("full_script", "") if isinstance(script_result, dict) else str(script_result)
    title = script_result.get("title", f"第 {episode_number} 集") if isinstance(script_result, dict) else f"第 {episode_number} 集"
    structure = script_result.get("structure", {}) if isinstance(script_result, dict) else {}
    scenes = script_result.get("scenes", []) if isinstance(script_result, dict) else []
    characters = script_result.get("characters", []) if isinstance(script_result, dict) else []
    hook_type = script_result.get("hook_type", "") if isinstance(script_result, dict) else ""

    # 计算字数和场景数
    word_count = len(full_script)
    scene_count = len(scenes)

    # 检查是否已存在该集剧本
    existing_script = db.query(Script).filter(
        Script.plot_breakdown_id == breakdown_id,
        Script.episode_number == episode_number
    ).first()

    if existing_script:
        # 更新现有剧本
        existing_script.title = title
        existing_script.content = {
            "structure": structure,
            "full_script": full_script,
            "scenes": scenes,
            "characters": characters,
            "hook_type": hook_type
        }
        existing_script.word_count = word_count
        existing_script.scene_count = scene_count
        existing_script.status = "draft"
        script_id = str(existing_script.id)
        if log_publisher:
            log_publisher.publish_info(task_id, f"✏️ 更新已存在的剧本 (ID: {script_id[:8]}...)")
    else:
        # 创建新剧本
        new_script = Script(
            batch_id=breakdown.batch_id,
            project_id=project_id,
            plot_breakdown_id=breakdown_id,
            episode_number=episode_number,
            title=title,
            content={
                "structure": structure,
                "full_script": full_script,
                "scenes": scenes,
                "characters": characters,
                "hook_type": hook_type
            },
            word_count=word_count,
            scene_count=scene_count,
            status="draft"
        )
        db.add(new_script)
        db.flush()
        script_id = str(new_script.id)
        if log_publisher:
            log_publisher.publish_success(task_id, f"✅ 剧本已保存 (ID: {script_id[:8]}...)")

    db.commit()

    return {
        "episode_number": episode_number,
        "title": title,
        "word_count": word_count,
        "scene_count": scene_count,
        "script_id": script_id,
        "script": script_result
    }

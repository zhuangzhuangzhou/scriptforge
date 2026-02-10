"""剧情拆解Celery任务

包含重试机制、配额回滚和错误分类功能。

注意：此文件使用同步数据库操作，因为 Celery worker 运行在同步上下文中。
"""
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.core.database import SyncSessionLocal
from app.core.progress import update_task_progress_sync
from app.core.credits import BREAKDOWN_BASE_CREDITS
from app.core.exceptions import (
    AITaskException,
    RetryableError,
    QuotaExceededError,
    classify_exception,
)
from app.models.ai_task import AITask
from app.models.batch import Batch
from app.models.user import User


# Celery任务配置
CELERY_TASK_CONFIG = {
    "bind": True,                       # 绑定self参数
    "autoretry_for": (RetryableError, TimeoutError, ConnectionError),
    "retry_kwargs": {
        "max_retries": 3,              # 最多重试3次
        "countdown": 60,                # 基础等待时间（秒）
    },
    "retry_backoff": True,              # 启用指数退避
    "retry_backoff_max": 600,           # 最大等待时间（10分钟）
    "retry_jitter": True,               # 添加随机抖动
    "acks_late": True,                 # 任务完成后才确认
    "reject_on_worker_lost": True,     # Worker丢失时重新排队
}


@celery_app.task(**CELERY_TASK_CONFIG)
def run_breakdown_task(self, task_id: str, batch_id: str, project_id: str, user_id: str):
    """执行Breakdown任务（同步版本，支持流式输出）

    支持：
    - 自动重试（网络错误等可重试错误）
    - 配额回滚（任务失败时返还配额）
    - 错误分类（区分可重试/不可重试错误）
    - 实时流式输出（通过 Redis Pub/Sub 推送日志）
    
    注意：使用同步数据库操作，避免 greenlet 错误
    """
    
    # 使用同步数据库会话
    db = SyncSessionLocal()
    batch_record = None
    task_record = None
    log_publisher = None

    try:
        # 初始化 Redis 日志发布器
        from app.core.redis_log_publisher import RedisLogPublisher
        try:
            log_publisher = RedisLogPublisher()
        except Exception as e:
            print(f"初始化 RedisLogPublisher 失败: {e}")
            log_publisher = None
        
        # 任务开始：更新状态为 running
        update_task_progress_sync(
            db, task_id,
            status="running",
            progress=0,
            current_step="初始化任务中... (0%)"
        )

        # 更新批次状态为 processing
        batch_record = db.query(Batch).filter(Batch.id == batch_id).first()
        if batch_record:
            batch_record.breakdown_status = "processing"
            db.commit()

        # 读取任务配置
        task_record = db.query(AITask).filter(AITask.id == task_id).first()
        task_config = task_record.config if task_record else {}
        
        # 获取模型配置 ID（必需）
        model_id = task_config.get("model_config_id")
        if not model_id:
            raise ValueError("任务配置中缺少 model_config_id")
        
        # 获取模型适配器
        from app.ai.adapters import get_adapter_sync
        try:
            model_adapter = get_adapter_sync(
                db=db,
                model_id=model_id,
                user_id=user_id
            )
        except ValueError as e:
            raise AITaskException(
                code="MODEL_ERROR",
                message=f"模型配置错误: {str(e)}"
            )

        # 执行拆解逻辑（传递 log_publisher）
        breakdown = _execute_breakdown_sync(
            db=db,
            task_id=task_id,
            batch_id=batch_id,
            project_id=project_id,
            model_adapter=model_adapter,
            task_config=task_config,
            log_publisher=log_publisher
        )
        
        # 任务完成：更新状态
        update_task_progress_sync(
            db, task_id,
            status="completed",
            progress=100,
            current_step="任务完成 (100%)"
        )

        # 更新批次状态为 completed
        if batch_record:
            batch_record.breakdown_status = "completed"
            batch_record.ai_processed = True  # 标记为已处理
            db.commit()

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
                    batch_record.breakdown_status = "processing"
                    await db.commit()

                # 读取任务配置
                task_result = await db.execute(
                    select(AITask).where(AITask.id == task_id)
                )
                task_record = task_result.scalar_one_or_none()
                task_config = task_record.config if task_record else {}

                # 创建模型适配器（从数据库读取配置）
                model_id = task_config.get("model_id")  # 如果任务配置中指定了模型
                model_adapter = await get_adapter(
                    model_id=model_id,
                    user_id=user_id,
                    db=db
                )

                # 定义进度回调函数
                async def progress_callback(step: str, progress: int):
                    await update_task_progress(
                        db, task_id,
                        progress=progress,
                        current_step=step
                    )

                # 各阶段进度更新
                await progress_callback("加载章节", 10)

                # 使用配置驱动的 Pipeline 执行
                executor = PipelineExecutor(
                    db=db,
                    model_adapter=model_adapter,
                    user_id=user_id,
                    task_config=task_config
                )

                await executor.run_breakdown(
                    project_id=project_id,
                    batch_id=batch_id,
                    pipeline_id=task_config.get("pipeline_id"),
                    selected_skills=task_config.get("selected_skills"),
                    progress_callback=progress_callback
                )

                # 验证拆解结果已保存（状态一致性检查）
                from app.models.plot_breakdown import PlotBreakdown
                breakdown_check = await db.execute(
                    select(PlotBreakdown).where(PlotBreakdown.batch_id == batch_id)
                )
                breakdown_exists = breakdown_check.scalar_one_or_none()

                if not breakdown_exists:
                    # 如果拆解结果未保存，抛出异常阻止状态更新
                    raise ValueError(f"批次 {batch_id} 的拆解结果未保存，任务执行异常")

                # 任务完成：更新状态
                await update_task_progress(
                    db, task_id,
                    status="completed",
                    progress=100,
                    current_step="任务完成"
                )

                # 更新批次状态为 completed
                if batch_record:
                    batch_record.breakdown_status = "completed"
                    await db.commit()

                # 任务成功完成后扣费
                credits_service = CreditsService(db)
                await credits_service.consume_credits(
                    user_id=user_id,
                    amount=BREAKDOWN_BASE_CREDITS,
                    description=f"剧情拆解 - 批次 {batch_id}",
                    reference_id=task_id
                )
                await db.commit()

                return {"status": "completed", "task_id": task_id}

            except RetryableError as e:
                # 可重试错误：更新状态，Celery会自动重试
                await _handle_retryable_error(
                    db, task_id, batch_record, task_record, e
                )
                raise  # 重新抛出，让Celery处理重试

            except QuotaExceededError as e:
                # 配额不足错误：标记失败，回滚配额，不重试
                await _handle_quota_exceeded(
                    db, task_id, batch_record, task_record, user_id, e
                )
                raise

            except AITaskException as e:
                # 其他AI任务错误：标记失败，不重试
                await _handle_task_failure(
                    db, task_id, batch_record, task_record, user_id, e
                )
                raise

    except AITaskException as e:
        # 其他AI任务错误：标记失败，不重试
        _handle_task_failure_sync(
            db, task_id, batch_record, task_record, user_id, e, log_publisher
        )
        raise

    except Exception as e:
        # 未知错误：分类后处理
        classified_error = classify_exception(e)
        if isinstance(classified_error, RetryableError):
            _handle_retryable_error_sync(
                db, task_id, batch_record, task_record, classified_error, log_publisher
            )
            raise
        else:
            _handle_task_failure_sync(
                db, task_id, batch_record, task_record, user_id, classified_error, log_publisher
            )
            raise

    finally:
        # 清理资源
        if log_publisher:
            try:
                log_publisher.close()
            except Exception as e:
                print(f"关闭 RedisLogPublisher 失败: {e}")
        db.close()


def _handle_retryable_error_sync(
    db: Session,
    task_id: str,
    batch_record,
    task_record,
    error: RetryableError,
    log_publisher=None
):
    """处理可重试错误（同步版本）

    更新状态为retrying，等待Celery自动重试。
    """
    error_info = {
        "code": error.code,
        "message": error.message,
        "retry_count": task_record.retry_count if task_record else 0,
        "retrying_at": datetime.utcnow().isoformat(),
        "will_retry_after": error.retry_after
    }

    update_task_progress_sync(
        db, task_id,
        status="retrying",
        error_message=json.dumps(error_info)
    )

    if batch_record:
        batch_record.breakdown_status = "pending"
        db.commit()
    
    # 发布错误消息
    if log_publisher:
        log_publisher.publish_error(
            task_id,
            error.message,
            error_code=error.code
        )


def _handle_quota_exceeded_sync(
    db: Session,
    task_id: str,
    batch_record,
    task_record,
    user_id: str,
    error: QuotaExceededError,
    log_publisher=None
):
    """处理配额不足错误（同步版本）

    标记任务失败，回滚已消耗的配额。
    """
    # 回滚配额
    _refund_quota_sync(db, user_id)

    # 更新任务状态
    error_info = error.to_dict()
    error_info["failed_at"] = datetime.utcnow().isoformat()

    update_task_progress_sync(
        db, task_id,
        status="failed",
        error_message=json.dumps(error_info)
    )

    # 更新批次状态
    if batch_record:
        batch_record.breakdown_status = "failed"
        db.commit()
    
    # 发布错误消息
    if log_publisher:
        log_publisher.publish_error(
            task_id,
            error.message,
            error_code=error.code
        )


def _handle_task_failure_sync(
    db: Session,
    task_id: str,
    batch_record,
    task_record,
    user_id: str,
    error: AITaskException,
    log_publisher=None
):
    """处理任务失败（同步版本）

    更新状态，记录错误信息，回滚配额。
    """
    # 回滚配额
    _refund_quota_sync(db, user_id)

    # 更新任务状态
    error_info = error.to_dict()
    error_info["failed_at"] = datetime.utcnow().isoformat()
    error_info["retry_count"] = task_record.retry_count if task_record else 0

    update_task_progress_sync(
        db, task_id,
        status="failed",
        error_message=json.dumps(error_info)
    )

    # 更新批次状态
    if batch_record:
        batch_record.breakdown_status = "failed"
        db.commit()
    
    # 发布错误消息
    if log_publisher:
        log_publisher.publish_error(
            task_id,
            error.message,
            error_code=error.code
        )


def _refund_quota_sync(db: Session, user_id: str):
    """回滚用户配额（同步版本）

    从User记录中恢复已消耗的配额。
    """
    from app.core.quota import refund_episode_quota_sync

    # 调用新实现的同步配额回滚函数
    refund_episode_quota_sync(db, user_id, amount=1)




def _execute_breakdown_sync(
    db: Session,
    task_id: str,
    batch_id: str,
    project_id: str,
    model_adapter,
    task_config: dict,
    log_publisher=None
) -> dict:
    """执行拆解逻辑（同步版本，支持流式输出）
    
    Args:
        db: 同步数据库会话
        task_id: 任务ID
        batch_id: 批次ID
        project_id: 项目ID
        model_adapter: 模型适配器
        task_config: 任务配置
        log_publisher: Redis 日志发布器（可选）
        
    Returns:
        dict: 拆解结果
    """
    from app.models.chapter import Chapter
    from app.models.plot_breakdown import PlotBreakdown
    
    # 1. 加载章节数据
    update_task_progress_sync(db, task_id, progress=10, current_step="加载章节数据中... (10%)")
    
    chapters = db.query(Chapter).filter(
        Chapter.batch_id == batch_id
    ).order_by(Chapter.chapter_number).all()
    
    if not chapters:
        raise AITaskException(
            code="DATA_NOT_FOUND",
            message=f"批次 {batch_id} 没有章节数据"
        )
    
    # 2. 格式化章节文本
    chapters_text = _format_chapters_sync(chapters)
    
    # 3. 执行各个拆解技能（传递 log_publisher 和 task_id）
    update_task_progress_sync(db, task_id, progress=20, current_step="提取冲突中... (20%)")
    conflicts = _extract_conflicts_sync(
        chapters_text, model_adapter, task_config, log_publisher, task_id
    )
    
    update_task_progress_sync(db, task_id, progress=35, current_step="识别情节钩子中... (35%)")
    plot_hooks = _identify_plot_hooks_sync(
        chapters_text, model_adapter, task_config, log_publisher, task_id
    )
    
    update_task_progress_sync(db, task_id, progress=50, current_step="分析角色中... (50%)")
    characters = _analyze_characters_sync(
        chapters_text, model_adapter, task_config, log_publisher, task_id
    )
    
    update_task_progress_sync(db, task_id, progress=65, current_step="识别场景中... (65%)")
    scenes = _identify_scenes_sync(
        chapters_text, model_adapter, task_config, log_publisher, task_id
    )
    
    update_task_progress_sync(db, task_id, progress=80, current_step="提取情感中... (80%)")
    emotions = _extract_emotions_sync(
        chapters_text, model_adapter, task_config, log_publisher, task_id
    )
    
    # 4. 保存拆解结果
    update_task_progress_sync(db, task_id, progress=90, current_step="保存拆解结果中... (90%)")
    
    breakdown = PlotBreakdown(
        batch_id=batch_id,
        project_id=project_id,
        conflicts=conflicts,
        plot_hooks=plot_hooks,
        characters=characters,
        scenes=scenes,
        emotions=emotions,
        consistency_status="pending",
        consistency_score=None,
        consistency_results=None,
        qa_status="pending",
        qa_report=None,
        used_adapt_method_id=task_config.get("adapt_method_key")
    )
    
    db.add(breakdown)
    db.commit()
    db.refresh(breakdown)
    
    return {
        "breakdown_id": str(breakdown.id),
        "conflicts_count": len(conflicts) if conflicts else 0,
        "plot_hooks_count": len(plot_hooks) if plot_hooks else 0,
        "characters_count": len(characters) if characters else 0,
        "scenes_count": len(scenes) if scenes else 0,
        "emotions_count": len(emotions) if emotions else 0
    }


def _format_chapters_sync(chapters) -> str:
    """格式化章节文本"""
    formatted = []
    for ch in chapters:
        chapter_num = ch.chapter_number
        title = ch.title or f"第 {chapter_num} 章"
        content = ch.content or ""
        
        formatted.append(f"## 第 {chapter_num} 章：{title}\n\n{content}")
    
    return "\n\n".join(formatted)


def _extract_conflicts_sync(
    chapters_text: str,
    model_adapter,
    task_config: dict,
    log_publisher=None,
    task_id: str = None
) -> list:
    """提取冲突（支持流式输出）
    
    Args:
        chapters_text: 章节文本
        model_adapter: 模型适配器
        task_config: 任务配置
        log_publisher: Redis 日志发布器（可选）
        task_id: 任务 ID（可选）
    
    Returns:
        list: 冲突列表
    """
    step_name = "提取冲突"
    
    # 发布步骤开始消息
    if log_publisher and task_id:
        log_publisher.publish_step_start(task_id, step_name)
    
    prompt = f"""你是一个专业的剧情分析师。请分析以下章节内容，提取其中的主要冲突。

章节内容：
{chapters_text}

请以 JSON 数组格式返回冲突列表，每个冲突包含以下字段：
- type: 冲突类型（如：人物冲突、内心冲突、环境冲突等）
- description: 冲突描述
- participants: 参与者列表
- intensity: 冲突强度（1-10）
- chapter_range: 涉及的章节范围

示例格式：
[
  {{
    "type": "人物冲突",
    "description": "主角与反派之间的权力斗争",
    "participants": ["主角", "反派"],
    "intensity": 8,
    "chapter_range": [1, 3]
  }}
]

请只返回 JSON 数组，不要包含其他文字。
"""
    
    try:
        # 使用流式生成
        full_response = ""
        for chunk in model_adapter.stream_generate(prompt):
            # 发布流式内容片段
            if log_publisher and task_id:
                log_publisher.publish_stream_chunk(task_id, step_name, chunk)
            full_response += chunk
        
        # 解析结果
        result = _parse_json_response_sync(full_response, default=[])
        
        # 发布步骤结束消息
        if log_publisher and task_id:
            log_publisher.publish_step_end(task_id, step_name, {"count": len(result)})
        
        return result
        
    except Exception as e:
        # 发布错误消息
        if log_publisher and task_id:
            log_publisher.publish_error(task_id, str(e), error_code=None, step_name=step_name)
        print(f"提取冲突失败: {e}")
        return []


def _identify_plot_hooks_sync(
    chapters_text: str,
    model_adapter,
    task_config: dict,
    log_publisher=None,
    task_id: str = None
) -> list:
    """识别情节钩子（支持流式输出）
    
    Args:
        chapters_text: 章节文本
        model_adapter: 模型适配器
        task_config: 任务配置
        log_publisher: Redis 日志发布器（可选）
        task_id: 任务 ID（可选）
    
    Returns:
        list: 情节钩子列表
    """
    step_name = "识别情节钩子"
    
    # 发布步骤开始消息
    if log_publisher and task_id:
        log_publisher.publish_step_start(task_id, step_name)
    
    prompt = f"""你是一个专业的剧情分析师。请分析以下章节内容，识别其中的情节钩子（吸引读者继续阅读的关键点）。

章节内容：
{chapters_text}

请以 JSON 数组格式返回情节钩子列表，每个钩子包含以下字段：
- type: 钩子类型（如：悬念、转折、伏笔、高潮等）
- description: 钩子描述
- chapter: 所在章节
- impact: 影响力（1-10）

示例格式：
[
  {{
    "type": "悬念",
    "description": "主角发现了一个神秘的线索",
    "chapter": 2,
    "impact": 7
  }}
]

请只返回 JSON 数组，不要包含其他文字。
"""
    
    try:
        # 使用流式生成
        full_response = ""
        for chunk in model_adapter.stream_generate(prompt):
            # 发布流式内容片段
            if log_publisher and task_id:
                log_publisher.publish_stream_chunk(task_id, step_name, chunk)
            full_response += chunk
        
        # 解析结果
        result = _parse_json_response_sync(full_response, default=[])
        
        # 发布步骤结束消息
        if log_publisher and task_id:
            log_publisher.publish_step_end(task_id, step_name, {"count": len(result)})
        
        return result
        
    except Exception as e:
        # 发布错误消息
        if log_publisher and task_id:
            log_publisher.publish_error(task_id, str(e), error_code=None, step_name=step_name)
        print(f"识别情节钩子失败: {e}")
        return []


def _analyze_characters_sync(
    chapters_text: str,
    model_adapter,
    task_config: dict,
    log_publisher=None,
    task_id: str = None
) -> list:
    """分析角色（支持流式输出）
    
    Args:
        chapters_text: 章节文本
        model_adapter: 模型适配器
        task_config: 任务配置
        log_publisher: Redis 日志发布器（可选）
        task_id: 任务 ID（可选）
    
    Returns:
        list: 角色列表
    """
    step_name = "分析角色"
    
    # 发布步骤开始消息
    if log_publisher and task_id:
        log_publisher.publish_step_start(task_id, step_name)
    
    prompt = f"""你是一个专业的剧情分析师。请分析以下章节内容，提取并分析其中的主要角色。

章节内容：
{chapters_text}

请以 JSON 数组格式返回角色列表，每个角色包含以下字段：
- name: 角色名称
- role: 角色定位（如：主角、配角、反派等）
- traits: 性格特征列表
- relationships: 与其他角色的关系
- arc: 角色弧光描述

示例格式：
[
  {{
    "name": "张三",
    "role": "主角",
    "traits": ["勇敢", "善良", "冲动"],
    "relationships": {{"李四": "好友", "王五": "敌人"}},
    "arc": "从懦弱到勇敢的成长"
  }}
]

请只返回 JSON 数组，不要包含其他文字。
"""
    
    try:
        # 使用流式生成
        full_response = ""
        for chunk in model_adapter.stream_generate(prompt):
            # 发布流式内容片段
            if log_publisher and task_id:
                log_publisher.publish_stream_chunk(task_id, step_name, chunk)
            full_response += chunk
        
        # 解析结果
        result = _parse_json_response_sync(full_response, default=[])
        
        # 发布步骤结束消息
        if log_publisher and task_id:
            log_publisher.publish_step_end(task_id, step_name, {"count": len(result)})
        
        return result
        
    except Exception as e:
        # 发布错误消息
        if log_publisher and task_id:
            log_publisher.publish_error(task_id, str(e), error_code=None, step_name=step_name)
        print(f"分析角色失败: {e}")
        return []


def _identify_scenes_sync(
    chapters_text: str,
    model_adapter,
    task_config: dict,
    log_publisher=None,
    task_id: str = None
) -> list:
    """识别场景（支持流式输出）
    
    Args:
        chapters_text: 章节文本
        model_adapter: 模型适配器
        task_config: 任务配置
        log_publisher: Redis 日志发布器（可选）
        task_id: 任务 ID（可选）
    
    Returns:
        list: 场景列表
    """
    step_name = "识别场景"
    
    # 发布步骤开始消息
    if log_publisher and task_id:
        log_publisher.publish_step_start(task_id, step_name)
    
    prompt = f"""你是一个专业的剧情分析师。请分析以下章节内容，识别其中的主要场景。

章节内容：
{chapters_text}

请以 JSON 数组格式返回场景列表，每个场景包含以下字段：
- location: 场景地点
- time: 时间（如：白天、夜晚、具体时间等）
- description: 场景描述
- characters: 出现的角色列表
- chapter: 所在章节
- mood: 场景氛围

示例格式：
[
  {{
    "location": "古老的城堡",
    "time": "深夜",
    "description": "月光透过破碎的窗户洒进大厅",
    "characters": ["主角", "神秘人"],
    "chapter": 1,
    "mood": "紧张、神秘"
  }}
]

请只返回 JSON 数组，不要包含其他文字。
"""
    
    try:
        # 使用流式生成
        full_response = ""
        for chunk in model_adapter.stream_generate(prompt):
            # 发布流式内容片段
            if log_publisher and task_id:
                log_publisher.publish_stream_chunk(task_id, step_name, chunk)
            full_response += chunk
        
        # 解析结果
        result = _parse_json_response_sync(full_response, default=[])
        
        # 发布步骤结束消息
        if log_publisher and task_id:
            log_publisher.publish_step_end(task_id, step_name, {"count": len(result)})
        
        return result
        
    except Exception as e:
        # 发布错误消息
        if log_publisher and task_id:
            log_publisher.publish_error(task_id, str(e), error_code=None, step_name=step_name)
        print(f"识别场景失败: {e}")
        return []


def _extract_emotions_sync(
    chapters_text: str,
    model_adapter,
    task_config: dict,
    log_publisher=None,
    task_id: str = None
) -> list:
    """提取情感（支持流式输出）
    
    Args:
        chapters_text: 章节文本
        model_adapter: 模型适配器
        task_config: 任务配置
        log_publisher: Redis 日志发布器（可选）
        task_id: 任务 ID（可选）
    
    Returns:
        list: 情感列表
    """
    step_name = "提取情感"
    
    # 发布步骤开始消息
    if log_publisher and task_id:
        log_publisher.publish_step_start(task_id, step_name)
    
    prompt = f"""你是一个专业的剧情分析师。请分析以下章节内容，提取其中的情感变化。

章节内容：
{chapters_text}

请以 JSON 数组格式返回情感列表，每个情感包含以下字段：
- emotion: 情感类型（如：喜悦、悲伤、愤怒、恐惧等）
- intensity: 情感强度（1-10）
- character: 相关角色
- trigger: 触发事件
- chapter: 所在章节

示例格式：
[
  {{
    "emotion": "愤怒",
    "intensity": 8,
    "character": "主角",
    "trigger": "发现被背叛",
    "chapter": 3
  }}
]

请只返回 JSON 数组，不要包含其他文字。
"""
    
    try:
        # 使用流式生成
        full_response = ""
        for chunk in model_adapter.stream_generate(prompt):
            # 发布流式内容片段
            if log_publisher and task_id:
                log_publisher.publish_stream_chunk(task_id, step_name, chunk)
            full_response += chunk
        
        # 解析结果
        result = _parse_json_response_sync(full_response, default=[])
        
        # 发布步骤结束消息
        if log_publisher and task_id:
            log_publisher.publish_step_end(task_id, step_name, {"count": len(result)})
        
        return result
        
    except Exception as e:
        # 发布错误消息
        if log_publisher and task_id:
            log_publisher.publish_error(task_id, str(e), error_code=None, step_name=step_name)
        print(f"提取情感失败: {e}")
        return []


def _parse_json_response_sync(response: str, default=None):
    """解析 JSON 响应"""
    import re
    
    if default is None:
        default = []
    
    try:
        # 尝试直接解析
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # 尝试提取 JSON 代码块
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # 尝试提取任何 JSON 数组或对象
    json_match = re.search(r'(\[.*\]|\{.*\})', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # 解析失败，返回默认值
    return default

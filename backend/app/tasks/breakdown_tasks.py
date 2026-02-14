"""剧情拆解Celery任务

包含重试机制、配额回滚和错误分类功能。

注意：此文件使用同步数据库操作，因为 Celery worker 运行在同步上下文中。
"""
import json
from datetime import datetime
import logging
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.core.database import SyncSessionLocal
from app.core.progress import update_task_progress_sync
from app.core.credits import consume_credits_for_task_sync, consume_token_credits_sync
from app.core.exceptions import (
    AITaskException,
    RetryableError,
    QuotaExceededError,
    classify_exception,
)
from app.models.ai_task import AITask
from app.models.batch import Batch
from app.models.user import User

logger = logging.getLogger(__name__)


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

        # 发布任务完成消息到 logs 频道（供 WebSocket 客户端接收）
        if log_publisher:
            log_publisher.publish_task_complete(task_id, status="completed", message="拆解任务执行完成")

        # 更新批次状态为 completed
        if batch_record:
            batch_record.breakdown_status = "completed"
            batch_record.ai_processed = True  # 标记为已处理
            db.commit()

        # Token 计费：从 LLMCallLog 汇总该任务的 token 使用量并扣费
        token_result = consume_token_credits_sync(
            db=db,
            user_id=user_id,
            task_id=task_id,
            task_type="breakdown"
        )
        if token_result.get("token_credits", 0) > 0:
            db.commit()
            logger.info(
                f"Token 扣费完成: input={token_result.get('input_tokens', 0)}, "
                f"output={token_result.get('output_tokens', 0)}, "
                f"credits={token_result.get('token_credits', 0)}"
            )

        return {"status": "completed", "task_id": task_id}

    except AITaskException as e:
        # 其他AI任务错误：标记失败，不重试
        _handle_task_failure_sync(
            db, task_id, batch_record, task_record, user_id, e, log_publisher
        )
        raise

    except SoftTimeLimitExceeded as e:
        """处理任务超时（软超时）

        当任务执行时间超过 soft_time_limit（25分钟）时触发。
        超时情况特殊处理：
        1. 任务通常还没真正调用 API，不需要扣 Token 费用
        2. 需要返还已扣除的配额
        3. 更新批次状态为 failed
        """
        logger.warning(f"任务执行超时（软超时）: task_id={task_id}")

        # 发布超时警告
        if log_publisher:
            try:
                log_publisher.publish_warning(
                    task_id,
                    "任务执行时间过长，系统将终止此任务"
                )
            except Exception:
                pass

        # 标记任务失败（超时特殊处理）
        _handle_timeout_failure_sync(
            db=db,
            task_id=task_id,
            batch_record=batch_record,
            task_record=task_record,
            user_id=user_id,
            log_publisher=log_publisher
        )
        raise

    except Exception as e:
        # 记录详细错误日志
        import traceback
        logger.exception(f"任务执行发生未知错误: {e}")
        logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")

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

    标记任务失败。
    注意：采用后扣费模式，不需要回滚积分。
    """
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


def _handle_timeout_failure_sync(
    db: Session,
    task_id: str,
    batch_record,
    task_record,
    user_id: str,
    log_publisher=None
):
    """处理任务超时失败（同步版本）

    超时与普通失败的区别：
    1. 超时通常意味着 API 还没真正调用，不需要扣 Token 费用
    2. 需要返还已扣除的配额
    3. 错误信息更友好

    处理流程：
    1. 更新任务状态为 failed
    2. 更新批次状态为 failed
    3. 返还配额
    4. 发布错误消息
    """
    from app.core.quota import refund_episode_quota_sync

    # 构建超时错误信息
    timeout_info = {
        "code": "TASK_TIMEOUT",
        "message": "任务执行超时，请稍后重试或减少章节数量",
        "failed_at": datetime.utcnow().isoformat(),
        "retry_count": task_record.retry_count if task_record else 0,
        "is_timeout": True
    }

    # 更新任务状态
    update_task_progress_sync(
        db, task_id,
        status="failed",
        error_message=json.dumps(timeout_info),
        current_step="任务超时"
    )

    # 更新批次状态为 failed
    if batch_record:
        batch_record.breakdown_status = "failed"
        db.commit()
        logger.info(f"批次 {batch_record.id} 状态已更新为 failed（超时）")

    # 返还配额（超时场景：返还 100%）
    try:
        refund_episode_quota_sync(db, user_id, 1)
        db.commit()
        logger.info(f"超时任务已返还配额: user_id={user_id}")
    except Exception as refund_error:
        logger.error(f"返还配额失败: {refund_error}")
        db.rollback()

    # 发布错误消息（WebSocket 通知）
    if log_publisher:
        try:
            log_publisher.publish_error(
                task_id,
                "任务执行超时，请稍后重试或减少章节数量",
                error_code="TASK_TIMEOUT"
            )
        except Exception:
            pass

    logger.info(f"超时任务处理完成: task_id={task_id}")


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

    更新状态，记录错误信息。
    注意：即使任务失败，也需要扣除已消耗的 Token 费用（因为实际调用了 API）。
    """
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

    # Token 计费：即使任务失败，也需要扣除已消耗的 Token 费用
    token_result = consume_token_credits_sync(
        db=db,
        user_id=user_id,
        task_id=task_id,
        task_type="breakdown"
    )
    if token_result.get("token_credits", 0) > 0:
        db.commit()
        logger.info(
            f"任务失败但仍扣除 Token 费用: input={token_result.get('input_tokens', 0)}, "
            f"output={token_result.get('output_tokens', 0)}, "
            f"credits={token_result.get('token_credits', 0)}"
        )

    # 发布错误消息
    if log_publisher:
        log_publisher.publish_error(
            task_id,
            error.message,
            error_code=error.code
        )




def _execute_breakdown_sync(
    db: Session,
    task_id: str,
    batch_id: str,
    project_id: str,
    model_adapter,
    task_config: dict,
    log_publisher=None
) -> dict:
    """执行拆解逻辑（v3：Agent 驱动）

    使用增强的 Agent 执行器，支持循环质检和条件修正。

    流程：
    1. 加载章节数据
    2. 加载 AI 资源文档
    3. 调用 breakdown_agent 执行拆解（内部循环质检）
    4. 保存结果到 PlotBreakdown

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
    # 根据 task_config 判断执行模式
    use_v1 = task_config.get("format_version") == 1
    use_agent = task_config.get("use_agent", True)  # 默认使用 Agent

    if use_v1:
        return _execute_breakdown_sync_v1(
            db, task_id, batch_id, project_id,
            model_adapter, task_config, log_publisher
        )

    from app.models.chapter import Chapter
    from app.models.batch import Batch
    from app.models.plot_breakdown import PlotBreakdown
    from app.ai.simple_executor import SimpleAgentExecutor, SimpleSkillExecutor
    from app.core.init_ai_resources import load_layered_resources_sync
    import logging
    logger = logging.getLogger(__name__)

    # 1. 加载章节数据（10%）
    update_task_progress_sync(db, task_id, progress=5, current_step="加载章节数据中... (5%)")

    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise AITaskException(code="DATA_NOT_FOUND", message=f"批次 {batch_id} 不存在")

    chapters = db.query(Chapter).filter(
        Chapter.batch_id == batch_id
    ).order_by(Chapter.chapter_number).all()

    if not chapters:
        raise AITaskException(code="DATA_NOT_FOUND", message=f"批次 {batch_id} 没有章节数据")

    chapters_text = _format_chapters_sync(chapters)
    update_task_progress_sync(db, task_id, progress=10, current_step="章节数据加载完成 (10%)")

    # 1.5 计算起始集数（查询该项目中"之前"批次的最大集数）
    # 只查询 start_chapter 小于当前批次的批次，确保第一批次从1开始
    start_episode = 1

    # 获取当前批次的 start_chapter
    current_start_chapter = batch.start_chapter

    # 查询之前批次的 breakdown 结果
    from sqlalchemy import and_
    previous_breakdowns = db.query(PlotBreakdown).join(
        Batch, PlotBreakdown.batch_id == Batch.id
    ).filter(
        and_(
            PlotBreakdown.project_id == project_id,
            Batch.start_chapter < current_start_chapter  # 只查询之前的批次
        )
    ).all()

    for prev_bd in previous_breakdowns:
        if prev_bd.plot_points:
            for pp in prev_bd.plot_points:
                if isinstance(pp, dict) and pp.get("episode"):
                    ep = pp.get("episode")
                    if isinstance(ep, int) and ep >= start_episode:
                        start_episode = ep + 1

    logger.info(f"计算起始集数: start_episode={start_episode} (项目 {project_id}, 当前批次 start_chapter={current_start_chapter})")

    # 2. 加载 AI 资源文档（15%）
    update_task_progress_sync(db, task_id, progress=12, current_step="加载 AI 资源文档中... (12%)")

    novel_type = task_config.get("novel_type")
    resource_ids = task_config.get("resource_ids", [])

    adapt_method = ""
    output_style = ""
    template = ""
    example = ""
    grouped_resources = {}

    if resource_ids:
        grouped_resources = _load_resources_by_ids_sync(db, resource_ids)
        if grouped_resources.get("methodology"):
            adapt_method = "\n\n---\n\n".join(grouped_resources["methodology"])
        if grouped_resources.get("output_style"):
            output_style = "\n\n---\n\n".join(grouped_resources["output_style"])
        if grouped_resources.get("qa_rules"):
            qa_content = "\n\n---\n\n".join(grouped_resources["qa_rules"])
            adapt_method = (adapt_method + "\n\n---\n\n" + qa_content) if adapt_method else qa_content
        if grouped_resources.get("template"):
            template = "\n\n---\n\n".join(grouped_resources["template"])
    else:
        layered_resources = load_layered_resources_sync(db, stage="breakdown", novel_type=novel_type)
        adapt_method_parts = [layered_resources.get(k) for k in ("core", "breakdown", "type") if layered_resources.get(k)]
        adapt_method = "\n\n---\n\n".join(adapt_method_parts) if adapt_method_parts else _load_ai_resource_sync(db, task_config.get("adapt_method_id"), "adapt_method")
        output_style = _load_ai_resource_sync(db, task_config.get("output_style_id"), "output_style")
        template = _load_ai_resource_sync(db, task_config.get("template_id"), "template")
        example = _load_ai_resource_sync(db, task_config.get("example_id"), "example")

    update_task_progress_sync(db, task_id, progress=15, current_step="AI 资源文档加载完成 (15%)")

    # 3. 执行拆解（20%-90%）
    update_task_progress_sync(db, task_id, progress=20, current_step="执行剧情拆解中... (20%)")

    # 构建 Agent 上下文
    agent_context = {
        "chapters_text": chapters_text,
        "adapt_method": adapt_method or "",
        "output_style": output_style or "",
        "template": template or "",
        "example": example or "",
        "start_chapter": str(batch.start_chapter),
        "end_chapter": str(batch.end_chapter),
        "start_episode": str(start_episode),
    }

    # 尝试使用 Agent 执行
    plot_points = []
    qa_status = "pending"
    qa_score = None
    qa_report = None

    if use_agent:
        try:
            agent_executor = SimpleAgentExecutor(db, model_adapter, log_publisher)
            results = agent_executor.execute_agent(
                agent_name="breakdown_agent",
                context=agent_context,
                task_id=task_id
            )

            # 提取结果
            plot_points = results.get("plot_points", [])
            qa_result = results.get("qa_result", {})
            qa_status = qa_result.get("status", "pending")
            qa_score = qa_result.get("score")
            qa_report = qa_result

            # 更新进度到 50%（AI 生成完成）
            update_task_progress_sync(db, task_id, progress=50, current_step="AI 剧情生成完成 (50%)")

            logger.info(f"Agent 执行完成，plot_points: {len(plot_points)}，qa_status: {qa_status}")

        except Exception as e:
            logger.warning(f"Agent 执行失败，回退到 Skill 直接调用: {e}")
            use_agent = False

    # 回退：直接调用 Skill
    if not use_agent or not plot_points:
        skill_executor = SimpleSkillExecutor(db, model_adapter, log_publisher)
        try:
            plot_points = skill_executor.execute_skill(
                skill_name="webtoon_breakdown",
                inputs=agent_context,
                task_id=task_id
            )
            if isinstance(plot_points, dict):
                plot_points = plot_points.get("plot_points", plot_points.get("results", []))
        except Exception as e:
            logger.error(f"Skill 执行失败: {e}")
            raise AITaskException(code="SKILL_EXECUTION_ERROR", message=str(e))

        # 更新进度到 50%（Skill 生成完成）
        update_task_progress_sync(db, task_id, progress=50, current_step="剧情生成完成 (50%)")

        # 回退模式：执行 QA 质检
        logger.info("回退到 Skill 模式，执行 QA 质检...")
        qa_result = _run_breakdown_qa_sync(
            db=db,
            task_id=task_id,
            plot_points=plot_points,
            chapters_text=chapters_text,
            adapt_method=adapt_method,
            model_adapter=model_adapter,
            log_publisher=log_publisher
        )
        qa_status = qa_result.get("status", "pending")
        qa_score = qa_result.get("score")
        qa_report = qa_result
        logger.info(f"Skill + QA 模式完成，qa_status: {qa_status}, qa_score: {qa_score}")

        # 更新进度到 70%（QA 质检完成）
        update_task_progress_sync(db, task_id, progress=70, current_step="质检完成 (70%)")

    # 如果 Agent 模式执行成功，检查是否已有 qa_result
    if use_agent and qa_status == "pending" and not qa_report:
        # Agent 模式下 QA 可能被跳过，补充执行
        logger.info("Agent 模式无 QA 结果，补充执行质检...")
        qa_result = _run_breakdown_qa_sync(
            db=db,
            task_id=task_id,
            plot_points=plot_points,
            chapters_text=chapters_text,
            adapt_method=adapt_method,
            model_adapter=model_adapter,
            log_publisher=log_publisher
        )
        qa_status = qa_result.get("status", "pending")
        qa_score = qa_result.get("score")
        qa_report = qa_result

    # 确保 plot_points 是列表
    if not isinstance(plot_points, list):
        plot_points = [plot_points] if plot_points else []

    # 4. 质检不通过时自动重试（最多3次）
    max_auto_fix_retries = task_config.get("max_auto_fix_retries", 3)
    auto_fix_enabled = task_config.get("auto_fix_on_fail", True)  # 默认启用
    fix_attempt = 0

    # 标准化 qa_status（统一转为大写）
    normalized_qa_status = qa_status.upper() if isinstance(qa_status, str) else "PENDING"
    logger.info(f"质检状态标准化: 原始={qa_status}, 标准化={normalized_qa_status}")

    # 判断是否需要自动修正（FAIL 或得分低于 60 分）
    needs_fix = (
        normalized_qa_status == "FAIL" or
        (qa_score is not None and qa_score < 60)
    )

    while (auto_fix_enabled and
           needs_fix and
           fix_attempt < max_auto_fix_retries and
           qa_report):

        fix_attempt += 1
        logger.info(f"质检未通过，开始第 {fix_attempt}/{max_auto_fix_retries} 次自动修正...")

        if log_publisher:
            log_publisher.publish_warning(
                task_id,
                f"质检未通过 (得分: {qa_score})，开始第 {fix_attempt}/{max_auto_fix_retries} 次自动修正..."
            )

        update_task_progress_sync(
            db, task_id,
            progress=85 + fix_attempt,
            current_step=f"自动修正中 (第 {fix_attempt} 次)..."
        )

        # 提取修正指令
        fix_instructions = _extract_fix_instructions_from_qa_report(qa_report)

        if not fix_instructions:
            logger.info("无法提取修正指令，跳过自动修正")
            break

        # 执行自动修正
        plot_points = _auto_fix_breakdown_sync(
            plot_points=plot_points,
            fix_instructions=fix_instructions,
            chapters_text=chapters_text,
            model_adapter=model_adapter,
            log_publisher=log_publisher,
            task_id=task_id
        )

        # 重新执行质检
        logger.info(f"第 {fix_attempt} 次修正完成，重新执行质检...")
        qa_result = _run_breakdown_qa_sync(
            db=db,
            task_id=task_id,
            plot_points=plot_points,
            chapters_text=chapters_text,
            adapt_method=adapt_method,
            model_adapter=model_adapter,
            log_publisher=log_publisher
        )
        qa_status = qa_result.get("status", "pending")
        qa_score = qa_result.get("score")
        qa_report = qa_result

        logger.info(f"第 {fix_attempt} 次修正后质检结果: status={qa_status}, score={qa_score}")

        # 重新计算是否需要继续修正
        normalized_qa_status = qa_status.upper() if isinstance(qa_status, str) else "PENDING"
        needs_fix = (
            normalized_qa_status == "FAIL" or
            (qa_score is not None and qa_score < 60)
        )

        if not needs_fix:
            if log_publisher:
                log_publisher.publish_success(
                    task_id,
                    f"第 {fix_attempt} 次修正后质检通过！得分: {qa_score}"
                )
            break

    # 记录最终修正次数
    if fix_attempt > 0:
        if qa_report is None:
            qa_report = {}
        qa_report["auto_fix_attempts"] = fix_attempt
        normalized_final_status = qa_status.upper() if isinstance(qa_status, str) else "PENDING"
        qa_report["auto_fix_success"] = normalized_final_status == "PASS" or (qa_score is not None and qa_score >= 60)

    update_task_progress_sync(db, task_id, progress=90, current_step=f"拆解完成，生成 {len(plot_points)} 个剧情点 (90%)")

    # 4. 保存结果（90%-100%）
    # 标准化 qa_status 为大写（前端期望 'PASS' | 'FAIL' | 'pending'）
    normalized_qa_status_for_db = qa_status.upper() if isinstance(qa_status, str) and qa_status.upper() in ("PASS", "FAIL") else "pending"

    # 获取 ai_model_id（来自 ai_models 表）
    ai_model_id = task_config.get("model_config_id")

    breakdown = PlotBreakdown(
        batch_id=batch_id,
        project_id=project_id,
        task_id=task_id,  # 关联任务 ID
        ai_model_id=ai_model_id,  # 关联 AI 模型 ID（来自 ai_models 表）
        plot_points=plot_points,
        format_version=2,
        consistency_status="pending",
        qa_status=normalized_qa_status_for_db,
        qa_score=qa_score,
        qa_report=qa_report,
        used_adapt_method_id=task_config.get("adapt_method_id"),
    )

    db.add(breakdown)
    db.commit()
    db.refresh(breakdown)

    update_task_progress_sync(db, task_id, progress=95, current_step="拆解结果已保存 (95%)")

    return {
        "breakdown_id": str(breakdown.id),
        "format_version": 2,
        "plot_points_count": len(plot_points),
        "qa_status": qa_status,
        "qa_score": qa_score,
        "use_agent": use_agent,
    }


def _execute_breakdown_sync_v1(
    db: Session,
    task_id: str,
    batch_id: str,
    project_id: str,
    model_adapter,
    task_config: dict,
    log_publisher=None
) -> dict:
    """执行拆解逻辑 v1（旧版：Agent 系统 + 6 字段格式）

    保留作为 fallback，当 task_config.format_version == 1 时使用。
    """
    from app.models.chapter import Chapter
    from app.models.plot_breakdown import PlotBreakdown
    from app.ai.simple_executor import SimpleAgentExecutor

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

    chapters_text = _format_chapters_sync(chapters)

    # 2. 使用 Agent 系统执行拆解
    update_task_progress_sync(db, task_id, progress=20, current_step="开始执行拆解流程... (20%)")

    executor = SimpleAgentExecutor(
        db=db,
        model_adapter=model_adapter,
        log_publisher=log_publisher
    )

    context = {"chapters_text": chapters_text}

    try:
        results = executor.execute_agent(
            agent_name="breakdown_agent",
            context=context,
            task_id=task_id
        )

        conflicts = results.get("conflicts", [])
        plot_hooks = results.get("plot_hooks", [])
        characters = results.get("characters", [])
        scenes = results.get("scenes", [])
        emotions = results.get("emotions", [])
        episodes = results.get("episodes", [])

    except Exception as e:
        if log_publisher:
            log_publisher.publish_warning(
                task_id,
                f"Agent 系统执行失败，回退到传统方法: {str(e)}"
            )

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

        update_task_progress_sync(db, task_id, progress=85, current_step="规划剧集结构中... (85%)")
        episodes = _plan_episodes_sync(
            conflicts=conflicts,
            plot_hooks=plot_hooks,
            characters=characters,
            scenes=scenes,
            emotions=emotions,
            chapters=chapters,
            model_adapter=model_adapter,
            task_config=task_config,
            log_publisher=log_publisher,
            task_id=task_id
        )

    # 质量检查（可选）
    qa_status = "pending"
    qa_score = None
    qa_report = None

    enable_qa = task_config.get("enable_qa", False)

    if enable_qa:
        update_task_progress_sync(db, task_id, progress=88, current_step="质量检查中... (88%)")

        breakdown_data = {
            "conflicts": conflicts,
            "plot_hooks": plot_hooks,
            "characters": characters,
            "scenes": scenes,
            "emotions": emotions,
            "episodes": episodes
        }

        adapt_method_config = _get_adapt_method_sync(db, task_config)

        qa_result = _run_qa_loop_sync(
            db=db,
            task_id=task_id,
            breakdown_data=breakdown_data,
            chapters=chapters,
            adapt_method=adapt_method_config,
            model_adapter=model_adapter,
            log_publisher=log_publisher
        )

        qa_status = qa_result.get("qa_status", "pending")
        qa_score = qa_result.get("qa_score")
        qa_report = qa_result.get("qa_report")

        if qa_result.get("modified_data"):
            modified = qa_result["modified_data"]
            conflicts = modified.get("conflicts", conflicts)
            plot_hooks = modified.get("plot_hooks", plot_hooks)
            characters = modified.get("characters", characters)
            scenes = modified.get("scenes", scenes)
            emotions = modified.get("emotions", emotions)
            episodes = modified.get("episodes", episodes)

    # 获取 model_config_id 用于数据分析（来自 model_configs 表）
    model_config_id = task_config.get("model_config_id")

    breakdown = PlotBreakdown(
        batch_id=batch_id,
        project_id=project_id,
        task_id=task_id,  # 关联任务 ID
        ai_model_id=model_config_id,  # ai_models 表的 ID（复用 model_config_id 的值，因为实际存储的是 ai_models 的 ID）
        model_config_id=model_config_id,  # model_configs 表的 ID（可能为空，因为 model_configs 表目前为空）
        conflicts=conflicts,
        plot_hooks=plot_hooks,
        characters=characters,
        scenes=scenes,
        emotions=emotions,
        episodes=episodes,
        format_version=1,
        consistency_status="pending",
        consistency_score=None,
        consistency_results=None,
        qa_status=qa_status,
        qa_score=qa_score,
        qa_report=qa_report,
        used_adapt_method_id=task_config.get("adapt_method_key")
    )

    db.add(breakdown)
    db.commit()
    db.refresh(breakdown)

    return {
        "breakdown_id": str(breakdown.id),
        "format_version": 1,
        "conflicts_count": len(conflicts) if conflicts else 0,
        "plot_hooks_count": len(plot_hooks) if plot_hooks else 0,
        "characters_count": len(characters) if characters else 0,
        "scenes_count": len(scenes) if scenes else 0,
        "emotions_count": len(emotions) if emotions else 0,
        "episodes_count": len(episodes) if episodes else 0
    }


def _load_ai_resource_sync(db: Session, resource_id, category: str) -> str:
    """从数据库加载 AI 资源文档内容

    Args:
        db: 数据库会话
        resource_id: 资源 ID（可为 None）
        category: 资源分类（adapt_method / output_style / template / example）

    Returns:
        str: 资源的 content 字段（Markdown 文本），如果找不到返回空字符串
    """
    from app.models.ai_resource import AIResource

    if resource_id:
        # 按 ID 查询指定资源
        resource = db.query(AIResource).filter(
            AIResource.id == resource_id,
            AIResource.is_active == True
        ).first()

        if resource:
            return resource.content or ""

    # resource_id 为空或按 ID 未找到：查询该 category 下的系统内置默认资源
    resource = db.query(AIResource).filter(
        AIResource.category == category,
        AIResource.is_builtin == True,
        AIResource.is_active == True
    ).first()

    if resource:
        return resource.content or ""

    return ""


def _load_resources_by_ids_sync(db: Session, resource_ids: list) -> dict:
    """批量加载用户选择的 AI 资源，按分类分组

    Args:
        db: 数据库会话
        resource_ids: 资源 ID 列表

    Returns:
        dict: 按分类分组的资源内容，格式为 {category: [content1, content2, ...]}
    """
    from app.models.ai_resource import AIResource

    if not resource_ids:
        return {}

    # 批量查询所有选中的资源
    resources = db.query(AIResource).filter(
        AIResource.id.in_(resource_ids),
        AIResource.is_active == True
    ).all()

    # 按分类分组
    grouped = {}
    for resource in resources:
        category = resource.category
        if category not in grouped:
            grouped[category] = []
        if resource.content:
            grouped[category].append(resource.content)

    return grouped


def _extract_fix_instructions_from_qa_report(qa_report: dict) -> str:
    """从 QA 报告中提取修正指令

    将问题列表和修复指引组合成提示词，用于自动修正。

    Args:
        qa_report: QA 质检报告

    Returns:
        str: 格式化的修正指令文本
    """
    if not qa_report:
        return ""

    instructions_parts = []

    # 1. 提取问题列表
    issues = qa_report.get("issues", [])
    if issues:
        instructions_parts.append("## 发现的问题\n")
        for i, issue in enumerate(issues, 1):
            if isinstance(issue, str):
                instructions_parts.append(f"{i}. {issue}")
            elif isinstance(issue, dict):
                desc = issue.get("description") or issue.get("issue") or str(issue)
                target = issue.get("target", "")
                if target:
                    instructions_parts.append(f"{i}. {target}: {desc}")
                else:
                    instructions_parts.append(f"{i}. {desc}")
        instructions_parts.append("")

    # 2. 提取修复指引
    fix_instructions = qa_report.get("fix_instructions", [])
    if fix_instructions:
        instructions_parts.append("## 修复指引\n")
        if isinstance(fix_instructions, str):
            instructions_parts.append(fix_instructions)
        elif isinstance(fix_instructions, list):
            for i, inst in enumerate(fix_instructions, 1):
                if isinstance(inst, str):
                    instructions_parts.append(f"{i}. {inst}")
                elif isinstance(inst, dict):
                    action = inst.get("action") or inst.get("suggestion") or str(inst)
                    target = inst.get("target", "")
                    if target:
                        instructions_parts.append(f"{i}. {target}: {action}")
                    else:
                        instructions_parts.append(f"{i}. {action}")
        instructions_parts.append("")

    # 3. 提取改进建议
    suggestions = qa_report.get("suggestions", [])
    if suggestions:
        instructions_parts.append("## 改进建议\n")
        for i, suggestion in enumerate(suggestions, 1):
            if isinstance(suggestion, str):
                instructions_parts.append(f"{i}. {suggestion}")
            elif isinstance(suggestion, dict):
                action = suggestion.get("action") or suggestion.get("suggestion") or str(suggestion)
                instructions_parts.append(f"{i}. {action}")
        instructions_parts.append("")

    # 4. 提取各维度的详细问题
    dimensions = qa_report.get("dimensions", {})
    if dimensions:
        failed_dimensions = []
        if isinstance(dimensions, dict):
            for name, dim_data in dimensions.items():
                if isinstance(dim_data, dict) and not dim_data.get("passed", dim_data.get("pass", True)):
                    details = dim_data.get("details", "")
                    if details:
                        failed_dimensions.append(f"- {name}: {details}")
        elif isinstance(dimensions, list):
            for dim in dimensions:
                if isinstance(dim, dict) and not dim.get("passed", dim.get("pass", True)):
                    name = dim.get("name", "未知维度")
                    details = dim.get("details", "")
                    if details:
                        failed_dimensions.append(f"- {name}: {details}")

        if failed_dimensions:
            instructions_parts.append("## 未通过的维度详情\n")
            instructions_parts.extend(failed_dimensions)
            instructions_parts.append("")

    return "\n".join(instructions_parts)


def _auto_fix_breakdown_sync(
    plot_points: list,
    fix_instructions,
    chapters_text: str,
    model_adapter,
    log_publisher=None,
    task_id: str = None
) -> list:
    """根据质检反馈自动修正剧情点（针对性修正策略）

    优化版本：
    - 支持结构化修正指令（fix_instructions_list）
    - 按问题类型分类处理
    - 优先使用直接替换，减少 AI 调用

    Args:
        plot_points: 当前剧情点列表
        fix_instructions: 质检给出的修正指令（str 或 list）
        chapters_text: 原文章节文本
        model_adapter: 模型适配器
        log_publisher: 日志发布器（可选）
        task_id: 任务 ID（可选）

    Returns:
        list: 修正后的剧情点 JSON 数组
    """
    step_name = "自动修正剧情点"

    if log_publisher and task_id:
        log_publisher.publish_step_start(task_id, step_name)

    # 解析修正指令
    instructions_list = []
    instructions_text = ""

    if isinstance(fix_instructions, list):
        instructions_list = fix_instructions
    elif isinstance(fix_instructions, str):
        instructions_text = fix_instructions
        # 尝试从文本中解析结构化指令
        instructions_list = _parse_fix_instructions_text(fix_instructions)

    # 如果有结构化指令，尝试直接替换
    if instructions_list:
        modified_points, remaining_instructions = _apply_direct_fixes(
            plot_points, instructions_list
        )

        if log_publisher and task_id:
            direct_fixed = len(instructions_list) - len(remaining_instructions)
            log_publisher.publish_info(
                task_id,
                f"直接修正 {direct_fixed} 个问题，剩余 {len(remaining_instructions)} 个需要 AI 处理"
            )

        # 如果所有问题都已直接修正，返回结果
        if not remaining_instructions:
            if log_publisher and task_id:
                log_publisher.publish_step_end(
                    task_id, step_name,
                    {"status": "success", "method": "direct_fix", "count": len(modified_points)}
                )
            return modified_points

        # 更新 plot_points 和 instructions_text
        plot_points = modified_points
        instructions_text = _format_remaining_instructions(remaining_instructions)

    # 如果没有修正指令，直接返回
    if not instructions_text and not instructions_list:
        if log_publisher and task_id:
            log_publisher.publish_step_end(
                task_id, step_name,
                {"status": "skipped", "reason": "no_instructions"}
            )
        return plot_points

    # 使用 AI 进行复杂修正
    prompt = f"""你是一个专业的剧情拆解修正专家。请根据质检反馈修正以下剧情点。

## 当前剧情点
```json
{json.dumps(plot_points, ensure_ascii=False, indent=2)}
```

## 质检修正指令
{instructions_text}

## 原文参考
{chapters_text[:3000]}
{"..." if len(chapters_text) > 3000 else ""}

## 修正要求
1. 严格按照修正指令进行修改
2. 保持 JSON 数组格式不变
3. 只修改需要修正的部分，不要改动正确的内容
4. 确保修正后的内容与原文一致
5. 每个剧情点必须包含：场景、角色、事件、情绪钩子类型、集数

请直接返回修正后的完整 JSON 数组，不要包含其他文字。
"""

    try:
        full_response = ""
        for chunk in model_adapter.stream_generate(prompt):
            if log_publisher and task_id:
                log_publisher.publish_stream_chunk(task_id, step_name, chunk)
            full_response += chunk

        result = _parse_json_response_sync(full_response, default=plot_points)

        # 确保返回列表
        if isinstance(result, dict):
            result = result.get("plot_points", result.get("results", [result]))
        if not isinstance(result, list):
            result = [result]

        if log_publisher and task_id:
            log_publisher.publish_step_end(
                task_id, step_name,
                {"status": "success", "method": "ai_fix", "count": len(result)}
            )

        return result

    except Exception as e:
        if log_publisher and task_id:
            log_publisher.publish_error(
                task_id,
                f"自动修正失败: {str(e)}",
                error_code="AUTO_FIX_ERROR",
                step_name=step_name
            )
        # 修正失败时返回原始数据
        return plot_points


def _parse_fix_instructions_text(text: str) -> list:
    """从文本中解析结构化修正指令"""
    import re
    instructions = []

    # 匹配格式：1. 【剧情X】\n   问题：...\n   修正为：...
    pattern = r'\d+\.\s*【剧情(\d+)】\s*\n\s*问题：(.+?)\n\s*修正为：(.+?)(?=\n\d+\.|$)'
    matches = re.findall(pattern, text, re.DOTALL)

    for match in matches:
        instructions.append({
            "target": f"【剧情{match[0]}】",
            "target_index": int(match[0]) - 1,
            "issue": match[1].strip(),
            "suggestion": match[2].strip()
        })

    return instructions


def _apply_direct_fixes(plot_points: list, instructions: list) -> tuple:
    """直接应用修正指令（不需要 AI）

    Returns:
        tuple: (修正后的 plot_points, 剩余未处理的 instructions)
    """
    modified_points = list(plot_points)  # 复制列表
    remaining = []

    for inst in instructions:
        target_index = inst.get("target_index")
        suggestion = inst.get("suggestion", "")
        fix_type = inst.get("type", "")

        # 检查索引是否有效
        if target_index is None or target_index < 0 or target_index >= len(modified_points):
            remaining.append(inst)
            continue

        # 根据问题类型进行直接修正
        if fix_type == "emotion_hook_type" and suggestion:
            # 情绪钩子类型修正：直接替换
            point = modified_points[target_index]
            if isinstance(point, dict) and "emotion_hook" in point:
                # 从 suggestion 中提取情绪钩子类型
                point["emotion_hook"] = _extract_emotion_hook(suggestion)
            elif isinstance(point, str):
                # 字符串格式的剧情点，直接替换
                modified_points[target_index] = suggestion
            else:
                remaining.append(inst)

        elif fix_type == "format_error" and suggestion:
            # 格式错误：直接替换整个剧情点
            modified_points[target_index] = suggestion

        else:
            # 其他类型需要 AI 处理
            remaining.append(inst)

    return modified_points, remaining


def _extract_emotion_hook(text: str) -> str:
    """从文本中提取情绪钩子类型"""
    import re
    # 常见情绪钩子类型
    hook_types = [
        "打脸蓄力", "打脸爽点", "碾压爽点", "金手指觉醒", "实力突破",
        "身份曝光", "身份提升", "虐心痛点", "误会产生", "真相揭露",
        "危机出现", "绝境反杀", "底牌爆发", "先知优势", "复仇成功",
        "初露锋芒", "甜宠时刻", "吃醋争风", "悬念开场", "反转爽点"
    ]

    for hook in hook_types:
        if hook in text:
            return hook

    # 尝试匹配逗号前的最后一个词组
    match = re.search(r'，([^，]+)，第\d+集', text)
    if match:
        return match.group(1)

    return ""


def _format_remaining_instructions(instructions: list) -> str:
    """格式化剩余的修正指令为文本"""
    if not instructions:
        return ""

    lines = ["请按以下指令修正剧情点：\n"]
    for i, inst in enumerate(instructions, 1):
        target = inst.get("target", "未知")
        issue = inst.get("issue", "")
        suggestion = inst.get("suggestion", "")
        lines.append(f"{i}. {target}")
        lines.append(f"   问题：{issue}")
        if suggestion:
            lines.append(f"   修正为：{suggestion}")
        lines.append("")

    return "\n".join(lines)


def _simplify_plot_points(plot_points: list) -> list:
    """简化剧情点列表（降级策略）

    当质检分数过低时，只保留核心剧情点，删除低强度内容。

    策略：
    1. 只保留包含高强度情绪钩子的剧情点
    2. 每6章最多保留5个剧情点
    3. 确保每集至少有1个剧情点

    Args:
        plot_points: 原始剧情点列表

    Returns:
        list: 简化后的剧情点列表
    """
    if not plot_points:
        return []

    # 高强度情绪钩子类型
    high_intensity_hooks = {
        "打脸爽点", "碾压爽点", "金手指觉醒", "身份曝光", "真相揭露",
        "绝境反杀", "底牌爆发", "复仇成功", "反转爽点", "虐心高潮",
        "打脸蓄力", "实力突破", "危机出现"
    }

    # 中等强度情绪钩子类型
    medium_intensity_hooks = {
        "初露锋芒", "身份提升", "悬念开场", "误会产生", "甜宠时刻",
        "吃醋争风", "先知优势"
    }

    simplified = []
    episode_counts = {}  # 记录每集的剧情点数量

    for point in plot_points:
        # 提取情绪钩子类型
        hook_type = ""
        episode = None

        if isinstance(point, dict):
            hook_type = point.get("emotion_hook", point.get("hook_type", ""))
            episode = point.get("episode", point.get("集数"))
        elif isinstance(point, str):
            # 从字符串中提取
            for hook in high_intensity_hooks | medium_intensity_hooks:
                if hook in point:
                    hook_type = hook
                    break
            # 提取集数
            import re
            match = re.search(r'第(\d+)集', point)
            if match:
                episode = int(match.group(1))

        # 判断是否保留
        is_high = hook_type in high_intensity_hooks
        is_medium = hook_type in medium_intensity_hooks

        if is_high:
            # 高强度：必须保留
            simplified.append(point)
            if episode:
                episode_counts[episode] = episode_counts.get(episode, 0) + 1
        elif is_medium:
            # 中等强度：如果该集还没有剧情点，则保留
            if episode and episode_counts.get(episode, 0) == 0:
                simplified.append(point)
                episode_counts[episode] = 1

    # 如果简化后太少，保留前 5 个
    if len(simplified) < 3 and len(plot_points) >= 3:
        simplified = plot_points[:5]

    return simplified


def _format_chapters_sync(chapters) -> str:
    """格式化章节文本

    Args:
        chapters: 章节列表

    Returns:
        str: 格式化后的章节文本
    """
    formatted = []

    for ch in chapters:
        chapter_num = ch.chapter_number
        title = ch.title or f"第 {chapter_num} 章"
        content = ch.content or ""
        chapter_text = f"## 第 {chapter_num} 章：{title}\n\n{content}"
        formatted.append(chapter_text)

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


def _plan_episodes_sync(
    conflicts: list,
    plot_hooks: list,
    characters: list,
    scenes: list,
    emotions: list,
    chapters: list,
    model_adapter,
    task_config: dict,
    log_publisher=None,
    task_id: str = None
) -> list:
    """规划剧集结构（支持流式输出）

    基于拆解结果，AI智能规划剧集结构，将章节内容分配到不同剧集。

    Args:
        conflicts: 冲突列表
        plot_hooks: 剧情钩子列表
        characters: 角色列表
        scenes: 场景列表
        emotions: 情感列表
        chapters: 章节列表
        model_adapter: 模型适配器
        task_config: 任务配置
        log_publisher: Redis 日志发布器（可选）
        task_id: 任务 ID（可选）

    Returns:
        list: 剧集列表
    """
    step_name = "规划剧集结构"

    if log_publisher and task_id:
        log_publisher.publish_step_start(task_id, step_name)

    # 构建章节信息
    chapter_info = [{"chapter_number": ch.chapter_number, "title": ch.title} for ch in chapters]

    # 构建提示词
    prompt = f"""你是一个专业的剧集规划师。基于以下剧情拆解结果，智能规划剧集结构。

章节信息：
{json.dumps(chapter_info, ensure_ascii=False)}

拆解结果统计：
- 冲突点：{len(conflicts)}个
- 剧情钩子：{len(plot_hooks)}个
- 角色：{len(characters)}个
- 场景：{len(scenes)}个
- 情感点：{len(emotions)}个

详细数据：
冲突：{json.dumps(conflicts, ensure_ascii=False)}
钩子：{json.dumps(plot_hooks, ensure_ascii=False)}
角色：{json.dumps(characters, ensure_ascii=False)}
场景：{json.dumps(scenes, ensure_ascii=False)}
情感：{json.dumps(emotions, ensure_ascii=False)}

请规划剧集结构，将章节内容合理分配到不同剧集中。每集应该：
1. 有完整的故事弧线
2. 包含主要冲突和高潮
3. 有吸引人的剧情钩子
4. 时长适中（建议每集包含2-4个章节）

以JSON格式返回：
[
  {{
    "episode_number": 1,
    "title": "第一集标题",
    "main_conflict": "主要冲突描述",
    "key_scenes": ["关键场景1", "关键场景2"],
    "chapter_range": [1, 3],
    "conflicts": [],
    "plot_hooks": [],
    "characters": [],
    "scenes": [],
    "emotions": []
  }}
]

注意：
- conflicts/plot_hooks/characters/scenes/emotions 字段应该从上面的详细数据中筛选出该集包含的内容
- 根据 chapter 字段或 chapter_range 字段判断是否属于该集
- 如果某个数据项没有明确的章节信息，可以根据内容判断

请只返回JSON数组，不要包含其他文字。
"""

    try:
        # 使用流式生成
        full_response = ""
        for chunk in model_adapter.stream_generate(prompt):
            if log_publisher and task_id:
                log_publisher.publish_stream_chunk(task_id, step_name, chunk)
            full_response += chunk

        # 解析结果
        result = _parse_json_response_sync(full_response, default=[])

        if log_publisher and task_id:
            log_publisher.publish_step_end(task_id, step_name, {"count": len(result)})

        return result

    except Exception as e:
        if log_publisher and task_id:
            log_publisher.publish_error(task_id, str(e), error_code=None, step_name=step_name)
        print(f"规划剧集结构失败: {e}")
        return []


def _get_adapt_method_sync(db: Session, task_config: dict) -> dict:
    """获取改编方法论配置（同步版本）

    Args:
        db: 数据库会话
        task_config: 任务配置

    Returns:
        dict: 改编方法论配置（包含 content 字段为 Markdown 内容）
    """
    from app.models.ai_resource import AIResource
    import re

    adapt_method_key = task_config.get("adapt_method_key")

    if not adapt_method_key:
        # 返回默认配置
        return {
            "description": "标准网文适配漫画原则",
            "content": "",
            "rules": [
                "确保内容连贯，冲突明显",
                "每集包含完整的故事弧线",
                "设置吸引人的剧情钩子"
            ]
        }

    # 判断是否为 UUID
    is_uuid = bool(re.match(r"^[0-9a-fA-F-]{36}$", adapt_method_key))

    # 从 AIResource 查询
    if is_uuid:
        resource = db.query(AIResource).filter(
            AIResource.id == adapt_method_key,
            AIResource.is_active == True
        ).first()
    else:
        resource = db.query(AIResource).filter(
            AIResource.name == adapt_method_key,
            AIResource.category == "methodology",
            AIResource.is_active == True
        ).first()

    if not resource:
        return {
            "description": "标准网文适配漫画原则",
            "content": "",
            "rules": []
        }

    return {
        "description": resource.description or resource.display_name or "标准网文适配漫画原则",
        "content": resource.content or "",
        "rules": []  # AIResource 使用 Markdown 内容，不再使用 rules 列表
    }


def _run_qa_loop_sync(
    db: Session,
    task_id: str,
    breakdown_data: dict,
    chapters: list,
    adapt_method: dict,
    model_adapter,
    log_publisher=None
) -> dict:
    """执行质检循环（同步版本）

    使用 SimpleSkillExecutor 调用 breakdown_aligner Skill（模板驱动）。

    Args:
        db: 数据库会话
        task_id: 任务 ID
        breakdown_data: 拆解数据
        chapters: 章节列表
        adapt_method: 改编方法论配置
        model_adapter: 模型适配器
        log_publisher: 日志发布器

    Returns:
        dict: 质检结果
    """
    from app.ai.simple_executor import SimpleSkillExecutor

    try:
        # 格式化章节文本
        chapters_text = "\n\n".join([
            f"## 第 {ch.chapter_number} 章：{ch.title or ''}\n\n{ch.content or ''}"
            for ch in chapters
        ])

        # 格式化拆解数据为 JSON
        plot_points_json = json.dumps(breakdown_data, ensure_ascii=False)

        # 格式化改编方法论
        adapt_method_text = adapt_method.get("description", "")
        if adapt_method.get("rules"):
            adapt_method_text += "\n\n规则：\n" + "\n".join(
                f"- {rule}" for rule in adapt_method["rules"]
            )

        # 使用 SimpleSkillExecutor 调用 breakdown_aligner Skill
        skill_executor = SimpleSkillExecutor(db, model_adapter, log_publisher)

        result = skill_executor.execute_skill(
            skill_name="breakdown_aligner",
            inputs={
                "plot_points": plot_points_json,
                "chapters_text": chapters_text,
                "adapt_method": adapt_method_text,
            },
            task_id=task_id
        )

        # 解析质检结果
        qa_status = "PASS" if result.get("status") == "PASS" else "FAIL"
        qa_score = result.get("score", 0)

        # 发布质检结果
        if log_publisher:
            if qa_status == "PASS":
                log_publisher.publish_success(
                    task_id,
                    f"✓ 质量检查通过！得分: {qa_score}"
                )
            else:
                log_publisher.publish_warning(
                    task_id,
                    f"⚠ 质量检查未通过，得分: {qa_score}"
                )

        return {
            "qa_status": qa_status,
            "qa_score": qa_score,
            "qa_report": result
        }

    except Exception as e:
        print(f"质检执行失败: {e}")
        if log_publisher:
            log_publisher.publish_error(
                task_id,
                f"质检执行失败: {str(e)}",
                error_code="QA_ERROR"
            )

        return {
            "qa_status": "ERROR",
            "qa_score": 0,
            "qa_report": {
                "error": str(e),
                "status": "ERROR"
            }
        }


def _try_fix_incomplete_json(json_str: str) -> str:
    """尝试修复不完整的 JSON 字符串

    常见问题：
    - 缺少结尾的 } 或 ]
    - 字符串未闭合
    - 尾部有多余字符

    Args:
        json_str: 可能不完整的 JSON 字符串

    Returns:
        修复后的 JSON 字符串
    """
    import re

    # 移除尾部的 ``` 标记
    json_str = re.sub(r'`+\s*$', '', json_str)

    # 统计括号
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    open_brackets = json_str.count('[')
    close_brackets = json_str.count(']')

    # 补充缺失的闭合括号
    if open_braces > close_braces:
        # 检查是否在字符串中间被截断（查找未闭合的引号）
        # 简单处理：如果最后一个字符不是 } 或 ]，尝试截断到最后一个完整的值
        last_valid_pos = max(
            json_str.rfind('},'),
            json_str.rfind('}]'),
            json_str.rfind('"}'),
            json_str.rfind('"]'),
            json_str.rfind('" }'),
            json_str.rfind('" ]'),
        )
        if last_valid_pos > 0:
            # 截断到最后一个完整的位置
            json_str = json_str[:last_valid_pos + 1]
            # 重新统计
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            open_brackets = json_str.count('[')
            close_brackets = json_str.count(']')

        # 补充缺失的 }
        json_str += '}' * (open_braces - close_braces)

    if open_brackets > close_brackets:
        json_str += ']' * (open_brackets - close_brackets)

    return json_str


def _parse_json_response_sync(response: str, default=None):
    """解析 JSON 响应（高度容错版本）

    解析策略（按优先级）：
    1. 直接解析整个响应
    2. 提取 ```json ... ``` 代码块
    3. 提取 ``` ... ```（无语言标记）
    4. 提取 { ... } JSON 对象
    5. 提取 [ ... ] JSON 数组
    6. 尝试修复不完整的 JSON

    Args:
        response: AI 模型的响应文本
        default: 解析失败时返回的默认值

    Returns:
        解析后的 JSON 对象，或默认值
    """
    import re

    if default is None:
        default = []

    # 检查响应是否为空
    if not response or not isinstance(response, str):
        return default

    response = response.strip()
    if not response:
        return default

    try:
        # 策略1：直接解析
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # 策略2：提取 ```json ... ``` 代码块
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str = _try_fix_incomplete_json(json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    # 策略3：提取 ``` ... ```（无语言标记）
    json_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str = _try_fix_incomplete_json(json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    # 策略4：提取 { ... } 或 [ ... ]
    json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', response)
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str = _try_fix_incomplete_json(json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    # 策略5：检查是否包含空响应关键词
    if any(keyword in response for keyword in ['没有', '无', '空', 'null', 'None', '[]', '{}']):
        return []

    # 解析失败，返回默认值
    return default


def _run_breakdown_qa_sync(
    db: Session,
    task_id: str,
    plot_points: list,
    chapters_text: str,
    adapt_method: str,
    model_adapter,
    log_publisher=None
) -> dict:
    """执行剧情拆解 QA 质检（v2 版本）

    调用 breakdown_aligner skill 对拆解结果进行质量检查。

    Args:
        db: 数据库会话
        task_id: 任务 ID
        plot_points: 剧情点列表
        chapters_text: 章节文本
        adapt_method: 改编方法论
        model_adapter: 模型适配器
        log_publisher: 日志发布器

    Returns:
        dict: 质检结果
    """
    from app.ai.simple_executor import SimpleSkillExecutor

    try:
        # 格式化剧情点为 JSON 字符串
        plot_points_json = json.dumps(plot_points, ensure_ascii=False)

        # 发布 QA 开始
        if log_publisher:
            log_publisher.publish_step_start(task_id, "质检检查")

        # 调用 breakdown_aligner skill
        skill_executor = SimpleSkillExecutor(db, model_adapter, log_publisher)
        result = skill_executor.execute_skill(
            skill_name="breakdown_aligner",
            inputs={
                "plot_points": plot_points_json,
                "chapters_text": chapters_text,
                "adapt_method": adapt_method or ""
            },
            task_id=task_id
        )

        # 解析结果
        qa_status = "pending"
        qa_score = None

        if isinstance(result, dict):
            qa_status = result.get("status", "pending")
            qa_score = result.get("score")

        # 发布 QA 完成
        if log_publisher:
            if qa_status == "PASS":
                log_publisher.publish_success(
                    task_id,
                    f"质检通过！得分: {qa_score}"
                )
            else:
                log_publisher.publish_warning(
                    task_id,
                    f"质检未通过，得分: {qa_score}"
                )

        logger.info(f"QA 质检完成: status={qa_status}, score={qa_score}")

        return result if isinstance(result, dict) else {"status": "pending", "score": None}

    except Exception as e:
        logger.error(f"QA 质检失败: {e}")
        if log_publisher:
            log_publisher.publish_error(
                task_id,
                f"质检失败: {str(e)}",
                error_code="QA_ERROR"
            )
        return {
            "status": "ERROR",
            "score": 0,
            "error": str(e)
        }

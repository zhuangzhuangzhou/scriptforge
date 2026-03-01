"""剧情拆解Celery任务

包含重试机制、配额回滚和错误分类功能。

注意：此文件使用同步数据库操作，因为 Celery worker 运行在同步上下文中。
"""
import json
from datetime import datetime, timezone
import logging
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.core.database import SyncSessionLocal
from app.core.progress import update_task_progress_sync
from app.core.status import map_task_status_to_batch, TaskStatus, BatchStatus, TaskType
from app.core.credits import consume_credits_for_task_sync, consume_token_credits_sync
from app.core.exceptions import (
    AITaskException,
    RetryableError,
    QuotaExceededError,
    classify_exception,
    TaskCancelledError,
)
from app.models.ai_task import AITask
from app.models.batch import Batch
from app.models.project import Project
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


def _trigger_next_task_sync(db: Session, completed_task_id: str, project_id: str, user_id: str):
    """触发下一个批次的拆解任务（自动连续拆解模式）

    当一个批次完成后，自动查找下一个待拆解的批次并启动。
    这是"全部拆解"功能的核心逻辑。

    Args:
        db: 数据库会话
        completed_task_id: 已完成的任务ID
        project_id: 项目ID
        user_id: 用户ID
    """
    try:
        # 获取刚完成的任务信息
        completed_task = db.query(AITask).filter(AITask.id == completed_task_id).first()
        if not completed_task:
            logger.error(f"未找到已完成的任务: {completed_task_id}")
            return

        # 检查是否是自动连续拆解模式
        task_config = completed_task.config or {}
        auto_continue = task_config.get("auto_continue", False)

        if not auto_continue:
            logger.info(f"任务 {completed_task_id} 不是自动连续拆解模式，跳过触发下一个批次")
            return

        # 获取当前批次信息
        current_batch = db.query(Batch).filter(Batch.id == completed_task.batch_id).first()
        if not current_batch:
            logger.error(f"未找到当前批次: {completed_task.batch_id}")
            return

        current_batch_number = current_batch.batch_number
        logger.info(f"当前批次 {current_batch_number} 已完成，查找下一个批次...")

        # 查找下一个待拆解的批次（按 batch_number 顺序）
        next_batch = db.query(Batch).filter(
            Batch.project_id == project_id,
            Batch.batch_number > current_batch_number,
            Batch.breakdown_status.in_([BatchStatus.PENDING, BatchStatus.FAILED])
        ).order_by(Batch.batch_number).first()

        if not next_batch:
            logger.info(f"项目 {project_id} 没有更多待拆解的批次，自动连续拆解完成")
            return

        logger.info(f"找到下一个批次: batch_number={next_batch.batch_number}, batch_id={next_batch.id}")

        # 检查用户积分是否足够
        from app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.credits < 100:
            logger.warning(f"用户 {user_id} 积分不足，停止自动连续拆解")
            return

        # 扣除积分
        user.credits -= 100
        logger.info(f"用户 {user_id} 扣除100积分，剩余: {user.credits}")

        # 创建新任务
        new_task = AITask(
            project_id=project_id,
            batch_id=next_batch.id,
            task_type=TaskType.BREAKDOWN,
            status=TaskStatus.QUEUED,
            depends_on=[],
            config=task_config  # 继承配置（包含 auto_continue 标记）
        )
        db.add(new_task)
        db.flush()

        # 启动 Celery 任务
        celery_task = run_breakdown_task.delay(
            str(new_task.id),
            str(next_batch.id),
            str(project_id),
            str(user_id)
        )

        # 更新任务和批次状态
        new_task.celery_task_id = celery_task.id
        next_batch.breakdown_status = BatchStatus.QUEUED

        db.commit()

        logger.info(
            f"成功启动下一个批次: batch_number={next_batch.batch_number}, "
            f"task_id={new_task.id}, celery_task_id={celery_task.id}"
        )

        # 🔧 新增：通过 WebSocket 推送批次切换消息
        try:
            from app.core.redis_log_publisher import RedisLogPublisher
            log_publisher = RedisLogPublisher()

            # 向前一个任务的 WebSocket 连接推送批次切换消息
            log_publisher.publish_batch_switch(
                old_task_id=completed_task_id,
                new_task_id=str(new_task.id),
                new_batch_id=str(next_batch.id),
                new_batch_number=next_batch.batch_number
            )

            logger.info(f"已推送批次切换消息: {current_batch_number} -> {next_batch.batch_number}")
        except Exception as ws_error:
            # WebSocket 推送失败不影响主流程
            logger.warning(f"推送批次切换消息失败: {ws_error}")

    except Exception as e:
        logger.error(f"触发下一个批次失败: {e}", exc_info=True)
        db.rollback()


@celery_app.task(**CELERY_TASK_CONFIG)
def run_breakdown_task(self, task_id: str, batch_id: str, project_id: str, user_id: str):
    """执行Breakdown任务（同步版本，支持流式输出）

    支持：
    - 自动重试（网络错误等可重试错误）
    - 配额回滚（任务失败时返还配额）
    - 错误分类（区分可重试/不可重试错误）
    - 实时流式输出（通过 Redis Pub/Sub 推送日志）
    - 数据库连接健康检查

    注意：使用同步数据库操作，避免 greenlet 错误
    """

    def ensure_db_connection(db: Session) -> Session:
        """确保数据库连接有效，如果断开则重新创建"""
        from sqlalchemy import text
        try:
            # 执行简单查询测试连接
            db.execute(text("SELECT 1"))
            return db
        except Exception as e:
            logger.warning(f"数据库连接已断开，正在重新连接: {e}")
            try:
                db.close()
            except Exception:
                pass
            return SyncSessionLocal()

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
            status=TaskStatus.RUNNING,
            progress=0,
            current_step="初始化任务中... (0%)"
        )

        # 批次状态与任务状态保持同步：任务运行中 => batch.processing
        batch_record = db.query(Batch).filter(Batch.id == batch_id).first()
        if batch_record:
            batch_record.breakdown_status = map_task_status_to_batch(TaskStatus.RUNNING) or BatchStatus.IN_PROGRESS
            db.commit()

        # 读取任务配置
        task_record = db.query(AITask).filter(AITask.id == task_id).first()
        task_config = task_record.config if task_record else {}

        # 获取模型配置 ID（必需）
        model_id = task_config.get("model_config_id")
        if not model_id:
            raise AITaskException(
                code="CONFIG_ERROR",
                message="任务配置中缺少 model_config_id"
            )

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

        # 执行拆解前检查数据库连接
        db = ensure_db_connection(db)

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

        # 执行完成后再次检查连接，并重新查询可能失效的 ORM 对象
        db = ensure_db_connection(db)
        # 重新查询 batch_record，避免 detached 状态
        batch_record = db.query(Batch).filter(Batch.id == batch_id).first()

        # 任务完成：更新状态
        update_task_progress_sync(
            db, task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            current_step="任务完成 (100%)"
        )

        # 批次状态与任务状态保持同步：任务完成 => batch.completed
        if batch_record:
            # 检查是否首次完成（避免重试时重复累加）
            is_first_completion = not batch_record.ai_processed

            batch_record.breakdown_status = map_task_status_to_batch(TaskStatus.COMPLETED) or BatchStatus.COMPLETED
            batch_record.ai_processed = True  # 标记为已处理

            # 仅首次完成时更新项目的已处理章节数
            if is_first_completion:
                project = db.query(Project).filter(Project.id == batch_record.project_id).first()
                if project:
                    project.processed_chapters = (project.processed_chapters or 0) + batch_record.total_chapters
                    logger.info(f"项目 {project.id} 已处理章节数更新为 {project.processed_chapters}")

        # Token 计费：从 LLMCallLog 汇总该任务的 token 使用量并扣费
        # 从 task_config 中获取 model_config_id，用于查询 AIModelPricing
        token_result = consume_token_credits_sync(
            db=db,
            user_id=user_id,
            task_id=task_id,
            task_type=TaskType.BREAKDOWN,
            model_config_id=task_config.get("model_config_id")
        )

        # 统一 commit（无论是否有 Token 消耗，都要提交批次状态）
        db.commit()

        if token_result.get("token_credits", 0) > 0:
            logger.info(
                f"Token 扣费完成: input={token_result.get('input_tokens', 0)}, "
                f"output={token_result.get('output_tokens', 0)}, "
                f"credits={token_result.get('token_credits', 0)}"
            )

        # 发布任务完成消息到 logs 频道（在 commit 之后发送，确保前端查询到最新状态）
        if log_publisher:
            log_publisher.publish_task_complete(task_id, status=TaskStatus.COMPLETED, message="拆解任务执行完成")

        # 触发下一个依赖任务（顺序执行）
        _trigger_next_task_sync(db, task_id, project_id, user_id)

        return {"status": TaskStatus.COMPLETED, "task_id": task_id}

    except TaskCancelledError as e:
        _handle_task_cancelled_sync(
            db, task_id, batch_record, task_record, user_id, log_publisher, str(e)
        )
        return {"status": TaskStatus.CANCELED, "task_id": task_id}

    except QuotaExceededError as e:
        # 配额不足错误：专门处理，不重试
        _handle_quota_exceeded_sync(
            db, task_id, batch_record, task_record, user_id, e, log_publisher
        )
        raise

    except ValueError as e:
        # ValueError 通常来自 QA 解析失败，这可能是 LLM 输出格式临时异常
        # 将其转换为可重试错误，允许重试
        error_message = str(e)
        logger.warning(f"QA 解析或验证失败，将作为可重试错误处理: {error_message}")

        # 如果是 QA 相关的 ValueError，标记为可重试
        if "QA" in error_message or "质检" in error_message or "解析" in error_message:
            retryable_error = RetryableError(f"QA 解析失败，将自动重试: {error_message}", retry_after=30)
            _handle_retryable_error_sync(
                db, task_id, batch_record, task_record, retryable_error, log_publisher
            )
            raise retryable_error from e
        else:
            # 其他 ValueError 作为普通失败处理
            classified_error = AITaskException(code="VALIDATION_ERROR", message=error_message)
            _handle_task_failure_sync(
                db, task_id, batch_record, task_record, user_id, classified_error, log_publisher
            )
            raise classified_error from e

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
            raise classified_error from e  # 抛出分类后的异常，保留原始异常链
        else:
            _handle_task_failure_sync(
                db, task_id, batch_record, task_record, user_id, classified_error, log_publisher
            )
            raise classified_error from e  # 抛出分类后的异常，保留原始异常链

    finally:
        # 清理资源
        if log_publisher:
            try:
                log_publisher.close()
            except Exception as e:
                logger.warning(f"关闭 RedisLogPublisher 失败: {e}")

        # 关闭模型适配器（如果有 close 方法）
        if 'model_adapter' in locals() and hasattr(model_adapter, 'close'):
            try:
                model_adapter.close()
            except Exception as e:
                logger.warning(f"关闭 model_adapter 失败: {e}")

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
    try:
        # 如果当前事务已经 abort，先回滚
        try:
            db.rollback()
        except Exception:
            pass

        # rollback 后重新查询 ORM 对象，避免 detached 状态
        task_record = db.query(AITask).filter(AITask.id == task_id).first()
        batch_record = db.query(Batch).filter(Batch.id == task_record.batch_id).first() if task_record else None

        error_info = {
            "code": error.code,
            "message": error.message,
            "retry_count": task_record.retry_count if task_record else 0,
            "retrying_at": datetime.now(timezone.utc).isoformat(),
            "will_retry_after": error.retry_after
        }

        update_task_progress_sync(
            db, task_id,
            status=TaskStatus.RETRYING,
            error_message=json.dumps(error_info, ensure_ascii=False)
        )

        if batch_record:
            batch_record.breakdown_status = map_task_status_to_batch(TaskStatus.RETRYING) or BatchStatus.IN_PROGRESS
            db.commit()

        # 发布错误消息
        if log_publisher:
            log_publisher.publish_error(
                task_id,
                error.message,
                error_code=error.code
            )

    except Exception as e:
        # 如果更新状态失败，记录日志但不抛出异常
        logger.error(f"更新任务重试状态时出错: {e}")
        try:
            db.rollback()
        except Exception:
            pass


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

    标记任务失败，并退还预扣的基础积分。
    注意：这是 API 配额不足（非用户积分不足），任务未实际执行，应退还积分。
    """
    from app.core.quota import refund_episode_quota_sync

    # 预先提取需要的属性，避免后续访问已过期的 ORM 对象
    batch_id_str = str(batch_record.id) if batch_record else None

    try:
        # 如果当前事务已经 abort，先回滚并关闭 session，创建新 session
        # 这是为了避免 "current transaction is aborted" 错误
        try:
            db.rollback()
        except Exception:
            pass

        # 关闭当前 session 并创建新 session，确保事务状态干净
        db.close()
        db = SyncSessionLocal()

        # rollback 后重新查询 ORM 对象，避免 detached 状态
        task_record = db.query(AITask).filter(AITask.id == task_id).first()
        batch_record = db.query(Batch).filter(Batch.id == task_record.batch_id).first() if task_record else None

        # 更新任务状态
        error_info = error.to_dict()
        error_info["failed_at"] = datetime.now(timezone.utc).isoformat()

        update_task_progress_sync(
            db, task_id,
            status=TaskStatus.FAILED,
            error_message=json.dumps(error_info, ensure_ascii=False)
        )

        # 更新批次状态（智能回滚机制）
        if batch_record:
            # 检查是否有之前成功的拆解结果
            has_previous_success = _check_previous_breakdown_success(db, batch_record.id, task_id)

            if has_previous_success:
                # 有之前的成功结果，恢复为 completed 状态
                batch_record.breakdown_status = BatchStatus.COMPLETED
                logger.info(f"批次 {batch_record.id} 有之前的成功结果，状态回滚为 completed（配额不足）")

                if log_publisher:
                    log_publisher.publish_warning(
                        task_id,
                        "配额不足，但批次已恢复到之前的成功状态"
                    )
            else:
                # 没有之前的成功结果，标记为 failed
                batch_record.breakdown_status = map_task_status_to_batch(TaskStatus.FAILED) or BatchStatus.FAILED
                logger.info(f"批次 {batch_record.id} 无之前的成功结果，状态更新为 failed（配额不足）")

        db.commit()

        # 退还预扣的基础积分（任务未实际执行）
        try:
            refund_episode_quota_sync(db, user_id, 1, auto_commit=False)
            db.commit()
            logger.info(f"API配额不足，已退还预扣基础积分: user_id={user_id}, task_id={task_id}")
        except Exception as refund_error:
            logger.error(f"退还基础积分失败: {refund_error}")
            db.rollback()

        # 发布错误消息
        if log_publisher:
            log_publisher.publish_error(
                task_id,
                error.message,
                error_code=error.code
            )

    except Exception as e:
        # 如果更新状态失败，记录日志但不抛出异常
        logger.error(f"更新配额不足任务状态时出错: {e}")
        try:
            db.rollback()
        except Exception:
            pass


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

    # 预先提取需要的属性，避免后续访问已过期的 ORM 对象
    batch_id_str = str(batch_record.id) if batch_record else None

    # 如果当前事务已经 abort，先回滚并关闭 session，创建新 session
    # 这是为了避免 "current transaction is aborted" 错误
    try:
        db.rollback()
    except Exception:
        pass

    # 关闭当前 session 并创建新 session，确保事务状态干净
    db.close()
    db = SyncSessionLocal()

    # 重新查询 ORM 对象，确保状态有效
    task_record = db.query(AITask).filter(AITask.id == task_id).first()
    batch_record = db.query(Batch).filter(Batch.id == task_record.batch_id).first() if task_record else None

    # 构建超时错误信息
    timeout_info = {
        "code": "TASK_TIMEOUT",
        "message": "任务执行超时，请稍后重试或减少章节数量",
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "retry_count": task_record.retry_count if task_record else 0,
        "is_timeout": True
    }

    # 更新任务状态
    update_task_progress_sync(
        db, task_id,
        status=TaskStatus.FAILED,
        error_message=json.dumps(timeout_info),
        current_step="任务超时"
    )

    # 更新批次状态（智能回滚机制）
    if batch_record:
        # 检查是否有之前成功的拆解结果
        has_previous_success = _check_previous_breakdown_success(db, batch_record.id, task_id)

        if has_previous_success:
            # 有之前的成功结果，恢复为 completed 状态
            batch_record.breakdown_status = BatchStatus.COMPLETED
            logger.info(f"批次 {batch_record.id} 有之前的成功结果，状态回滚为 completed（超时）")

            if log_publisher:
                log_publisher.publish_warning(
                    task_id,
                    "任务超时，但批次已恢复到之前的成功状态"
                )
        else:
            # 没有之前的成功结果，标记为 failed
            batch_record.breakdown_status = map_task_status_to_batch(TaskStatus.FAILED) or BatchStatus.FAILED
            logger.info(f"批次 {batch_record.id} 无之前的成功结果，状态更新为 failed（超时）")

        db.commit()

    # 返还配额（超时场景：返还 100%）
    try:
        refund_episode_quota_sync(db, user_id, 1, auto_commit=False)
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

    积分处理策略：
    - 如果有 Token 消耗：扣除 Token 费用（已调用 API）
    - 如果无 Token 消耗：返还预扣的基础积分（任务早期失败）
    """
    from app.core.quota import refund_episode_quota_sync

    # 预先提取需要的属性，避免后续访问已过期的 ORM 对象
    batch_id_str = str(batch_record.id) if batch_record else None

    try:
        # 如果当前事务已经 abort，先回滚并关闭 session，创建新 session
        # 这是为了避免 "current transaction is aborted" 错误
        try:
            db.rollback()
        except Exception:
            pass

        # 关闭当前 session 并创建新 session，确保事务状态干净
        db.close()
        db = SyncSessionLocal()

        # rollback 后重新查询 ORM 对象，避免 detached 状态
        task_record = db.query(AITask).filter(AITask.id == task_id).first()
        batch_record = db.query(Batch).filter(Batch.id == task_record.batch_id).first() if task_record else None

        # 更新任务状态
        error_info = error.to_dict()
        error_info["failed_at"] = datetime.now(timezone.utc).isoformat()
        error_info["retry_count"] = task_record.retry_count if task_record else 0

        update_task_progress_sync(
            db, task_id,
            status=TaskStatus.FAILED,
            error_message=json.dumps(error_info, ensure_ascii=False)
        )

        # 更新批次状态（智能回滚机制）
        if batch_record:
            # 检查是否有之前成功的拆解结果
            has_previous_success = _check_previous_breakdown_success(db, batch_record.id, task_id)

            if has_previous_success:
                # 有之前的成功结果，恢复为 completed 状态
                batch_record.breakdown_status = BatchStatus.COMPLETED
                logger.info(f"批次 {batch_record.id} 有之前的成功结果，状态回滚为 completed")

                if log_publisher:
                    log_publisher.publish_warning(
                        task_id,
                        "当前任务失败，但批次已恢复到之前的成功状态"
                    )
            else:
                # 没有之前的成功结果，标记为 failed
                batch_record.breakdown_status = map_task_status_to_batch(TaskStatus.FAILED) or BatchStatus.FAILED
                logger.info(f"批次 {batch_record.id} 无之前的成功结果，状态更新为 failed")

            db.commit()

        # Token 计费：检查是否有 Token 消耗
        task_config = task_record.config if task_record else {}
        token_result = consume_token_credits_sync(
            db=db,
            user_id=user_id,
            task_id=task_id,
            task_type=TaskType.BREAKDOWN,
            model_config_id=task_config.get("model_config_id")
        )

        token_consumed = token_result.get("token_credits", 0) > 0

        if token_consumed:
            # 有 Token 消耗，扣除费用
            db.commit()
            logger.info(
                f"任务失败但仍扣除 Token 费用: input={token_result.get('input_tokens', 0)}, "
                f"output={token_result.get('output_tokens', 0)}, "
                f"credits={token_result.get('token_credits', 0)}"
            )
        else:
            # 无 Token 消耗（早期失败），返还预扣的基础积分
            try:
                refund_episode_quota_sync(db, user_id, 1, auto_commit=False)
                db.commit()
                logger.info(f"任务早期失败，已返还基础积分: user_id={user_id}, task_id={task_id}")
            except Exception as refund_error:
                logger.error(f"返还基础积分失败: {refund_error}")
                db.rollback()

        # 发布错误消息
        if log_publisher:
            log_publisher.publish_error(
                task_id,
                error.message,
                error_code=error.code
            )

    except Exception as e:
        # 如果更新状态失败，记录日志但不抛出异常
        # 确保原始错误能够被正确传播
        logger.error(f"更新任务失败状态时出错: {e}")
        try:
            db.rollback()
        except Exception:
            pass




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
    from app.models.chapter import Chapter
    from app.models.batch import Batch
    from app.models.plot_breakdown import PlotBreakdown
    from app.ai.simple_executor import SimpleAgentExecutor, SimpleSkillExecutor
    from app.core.init_ai_resources import load_layered_resources_sync
    import logging
    logger = logging.getLogger(__name__)

    # 1. 加载章节数据（10%）
    _raise_if_cancelled_sync(db, task_id)
    update_task_progress_sync(db, task_id, progress=5, current_step="章节数据加载中... (5%)")

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
    # 优化：使用数据库 JSON 查询而非加载全部数据到内存
    start_episode = 1

    # 获取当前批次的 start_chapter
    current_start_chapter = batch.start_chapter

    # 优化查询：只获取之前批次中最大的 episode 数
    # 使用 PostgreSQL 的 jsonb_array_elements 提取 plot_points 中的 episode
    from sqlalchemy import and_, func, text
    try:
        # 方案1：使用 PostgreSQL JSON 聚合函数（高效）
        max_episode_query = text("""
            SELECT COALESCE(MAX((elem->>'episode')::int), 0) as max_ep
            FROM plot_breakdowns pb
            JOIN batches b ON pb.batch_id = b.id
            CROSS JOIN LATERAL jsonb_array_elements(pb.plot_points) AS elem
            WHERE pb.project_id = :project_id
              AND b.start_chapter < :current_start_chapter
              AND elem->>'episode' IS NOT NULL
        """)
        result = db.execute(max_episode_query, {
            "project_id": project_id,
            "current_start_chapter": current_start_chapter
        }).fetchone()

        if result and result[0]:
            start_episode = result[0] + 1
    except Exception as e:
        # 回退方案：如果 JSON 查询失败，使用原始方法（兼容非 PostgreSQL）
        logger.warning(f"JSON 聚合查询失败，使用回退方案: {e}")
        previous_breakdowns = db.query(PlotBreakdown).join(
            Batch, PlotBreakdown.batch_id == Batch.id
        ).filter(
            and_(
                PlotBreakdown.project_id == project_id,
                Batch.start_chapter < current_start_chapter
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
    _raise_if_cancelled_sync(db, task_id)
    update_task_progress_sync(db, task_id, progress=12, current_step="AI Skills 加载中 ... (12%)")

    novel_type = task_config.get("novel_type")
    resource_ids = task_config.get("resource_ids", [])

    adapt_method = ""
    output_style = ""
    template = ""
    example = ""
    # 新增资源变量
    hook_types = ""
    hook_boundary_rules = ""
    genre_guidelines = ""
    qa_dimensions = ""
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
        # 新增分类处理
        if grouped_resources.get("hook_types"):
            hook_types = "\n\n---\n\n".join(grouped_resources["hook_types"])
        if grouped_resources.get("hook_rules"):
            hook_boundary_rules = "\n\n---\n\n".join(grouped_resources["hook_rules"])
        if grouped_resources.get("type_guide"):
            genre_guidelines = "\n\n---\n\n".join(grouped_resources["type_guide"])
        if grouped_resources.get("qa_dimensions"):
            qa_dimensions = "\n\n---\n\n".join(grouped_resources["qa_dimensions"])
    else:
        layered_resources = load_layered_resources_sync(db, stage="breakdown", novel_type=novel_type)
        adapt_method_parts = [layered_resources.get(k) for k in ("core", "breakdown", "type") if layered_resources.get(k)]
        adapt_method = "\n\n---\n\n".join(adapt_method_parts) if adapt_method_parts else _load_ai_resource_sync(db, task_config.get("adapt_method_id"), "adapt_method")
        output_style = _load_ai_resource_sync(db, task_config.get("output_style_id"), "output_style")
        template = _load_ai_resource_sync(db, task_config.get("template_id"), "template")
        example = _load_ai_resource_sync(db, task_config.get("example_id"), "example")

    # 未选择时加载系统默认资源
    if not hook_types:
        hook_types = _load_default_resource_sync(db, "hook_types")
    if not hook_boundary_rules:
        hook_boundary_rules = _load_default_resource_sync(db, "hook_rules")
    if not genre_guidelines:
        genre_guidelines = _load_default_resource_sync(db, "type_guide")
    if not qa_dimensions:
        qa_dimensions = _load_default_resource_sync(db, "qa_dimensions")

    update_task_progress_sync(db, task_id, progress=15, current_step="AI Skills 加载完成 (15%)")

    # 3. 执行拆解（20%-90%）
    _raise_if_cancelled_sync(db, task_id)
    update_task_progress_sync(db, task_id, progress=20, current_step="剧集拆解 Agent 正在运行中 ...(20%)")

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
        # 新增资源参数
        "hook_types": hook_types or HOOK_TYPES_COMPACT_DEFAULT,
        "hook_boundary_rules": hook_boundary_rules or HOOK_BOUNDARY_RULES_DEFAULT,
        "genre_guidelines": genre_guidelines or GENRE_GUIDELINES_DEFAULT,
        "qa_dimensions": qa_dimensions or QA_DIMENSIONS_DEFAULT,
    }

    # ============================================================
    # 执行模式分支（通过 execution_mode 参数控制）
    #
    # agent_loop：Agent 内部循环（breakdown → qa → 修复，最多3轮）
    #   - 每轮全量重生成，Token 消耗大
    #   - 不进入外部修正
    #
    # agent_single：Agent 单轮 + Skill 局部修正（推荐）
    #   - Agent 只跑1轮生成初版
    #   - 后续修正交给 _auto_fix_breakdown_sync（局部修正）
    #
    # skill_only：纯 Skill 模式
    #   - 完全不用 Agent，直接调用 Skill
    #   - 外部 QA + 局部修正
    # ============================================================
    execution_mode = task_config.get("execution_mode", "agent_single")
    logger.info(f"执行模式: {execution_mode}")

    if log_publisher:
        mode_names = {
            "agent_loop": "Agent 全量循环模式",
            "agent_single": "Agent 单轮 + Skill 修正模式",
            "skill_only": "纯 Skill 模式"
        }
        log_publisher.publish_info(
            task_id,
            f"📋 执行模式: {mode_names.get(execution_mode, execution_mode)}"
        )

    plot_points = []
    qa_status = "pending"
    qa_score = None
    qa_report = None
    used_skill_fallback = False  # 标记是否使用了 Skill 回退模式

    # -------------------- 模式分支执行 --------------------
    if execution_mode == "skill_only":
        # 纯 Skill 模式：直接调用 Skill，不走 Agent
        logger.info("skill_only 模式：直接调用 Skill")
        used_skill_fallback = True
        skill_executor = SimpleSkillExecutor(db, model_adapter, log_publisher)
        try:
            _raise_if_cancelled_sync(db, task_id)
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

        # 检查 plot_points 是否为空
        if not plot_points or len(plot_points) == 0:
            logger.error(f"skill_only 模式返回空 plot_points！")
            raise AITaskException(
                code="EMPTY_RESULT",
                message="AI 未能生成有效的剧情拆解结果",
                suggestion="这可能是由于章节内容太少或格式问题导致的。建议：1) 检查章节内容是否足够长；2) 尝试重新运行任务；3) 如果问题持续，请联系技术支持。"
            )

        update_task_progress_sync(db, task_id, progress=50, current_step="剧集拆解 Agent 拆解结束 (50%)")


        update_task_progress_sync(db, task_id, progress=55, current_step="质量检查 Agent 工作中 ...(55%)")
        # 执行 QA 质检
        logger.info("skill_only 模式：执行 QA 质检...")
        _raise_if_cancelled_sync(db, task_id)
        qa_result = _run_breakdown_qa_sync(
            db=db,
            task_id=task_id,
            plot_points=plot_points,
            chapters_text=chapters_text,
            adapt_method=adapt_method,
            model_adapter=model_adapter,
            log_publisher=log_publisher,
            hook_types=agent_context.get("hook_types"),
            hook_boundary_rules=agent_context.get("hook_boundary_rules"),
            genre_guidelines=agent_context.get("genre_guidelines"),
            qa_dimensions=agent_context.get("qa_dimensions")
        )
        qa_status = qa_result.get("qa_status", "pending")
        qa_score = qa_result.get("qa_score")
        qa_report = qa_result
        logger.info(f"skill_only 模式 QA 完成，qa_status: {qa_status}, qa_score: {qa_score}")
        update_task_progress_sync(db, task_id, progress=80, current_step="质检Agent 已完成质检 (80%)")

    else:
        # Agent 模式（agent_loop 或 agent_single）
        # 区别在于 max_iterations_override：
        #   - agent_loop: None（使用 Agent 配置的默认值，通常是3）
        #   - agent_single: 1（只跑1轮）
        max_iterations_override = 1 if execution_mode == "agent_single" else None
        logger.info(f"Agent 模式：max_iterations_override={max_iterations_override}")

        try:
            _raise_if_cancelled_sync(db, task_id)

            # 创建 Agent 执行器
            agent_executor = SimpleAgentExecutor(db, model_adapter, log_publisher)

            # 执行 breakdown_agent 工作流
            results = agent_executor.execute_agent(
                agent_name="breakdown_agent",
                context=agent_context,
                task_id=task_id,
                max_iterations_override=max_iterations_override
            )

            # 从 Agent 结果中提取数据
            plot_points = results.get("plot_points", [])
            qa_result = results.get("qa_result", {})

            # 添加诊断日志：记录 results 的所有键名
            logger.info(f"[breakdown_tasks] results 所有键: {list(results.keys())}")

            # 尝试从 breakdown 中获取 plot_points
            breakdown_data = results.get("breakdown", {})
            if breakdown_data and isinstance(breakdown_data, dict):
                breakdown_plot_points = breakdown_data.get("plot_points", [])
                logger.info(f"[breakdown_tasks] breakdown.plot_points 长度: {len(breakdown_plot_points)}")
                # 如果 plot_points 为空但 breakdown 有数据，使用 breakdown 的数据
                if (not plot_points or len(plot_points) == 0) and breakdown_plot_points:
                    logger.info(f"[breakdown_tasks] 使用 breakdown.plot_points 作为最终结果")
                    plot_points = breakdown_plot_points

            logger.info(f"[breakdown_tasks] qa_result 类型: {type(qa_result).__name__}, qa_result 内容: {qa_result}")

            # 兼容 qa_result 可能存储在 qa 键下
            if not qa_result:
                qa_result = results.get("qa", {})
                logger.info(f"[breakdown_tasks] 从 qa 键获取: {qa_result}")

            qa_status = qa_result.get("qa_status", qa_result.get("status", "pending"))
            qa_score = qa_result.get("qa_score", qa_result.get("score"))
            qa_report = qa_result

            logger.info(f"[breakdown_tasks] 提取后的 qa_status={qa_status}, qa_score={qa_score}")

            # 检查 plot_points 是否为空，为空则抛出异常
            if not plot_points or len(plot_points) == 0:
                logger.error(f"Agent 返回空 plot_points！results 键: {list(results.keys())}")
                if "plot_points" in results:
                    logger.error(f"plot_points 值: {results.get('plot_points')}")
                raise AITaskException(
                    code="EMPTY_RESULT",
                    message="AI 未能生成有效的剧情拆解结果",
                    suggestion="这可能是由于章节内容太少或格式问题导致的。建议：1) 检查章节内容是否足够长；2) 尝试重新运行任务；3) 如果问题持续，请联系技术支持。"
                )

            update_task_progress_sync(db, task_id, progress=50, current_step="剧集拆解 Agent 拆解结束 (50%)")
            logger.info(f"Agent 执行完成，plot_points: {len(plot_points)}，qa_status: {qa_status}")

        except Exception as e:
            # Agent 执行失败，回退到 Skill 模式
            agent_error_msg = str(e)
            logger.warning(f"Agent 执行失败，回退到 Skill 直接调用: {agent_error_msg}")
            used_skill_fallback = True

            # 通过 WebSocket 通知用户发生了回退
            if log_publisher:
                log_publisher.publish_warning(
                    task_id,
                    f"⚠️ Agent 模式执行异常，已自动切换到 Skill 模式继续处理（原因: {agent_error_msg[:100]}）"
                )

            skill_executor = SimpleSkillExecutor(db, model_adapter, log_publisher)
            try:
                _raise_if_cancelled_sync(db, task_id)
                plot_points = skill_executor.execute_skill(
                    skill_name="webtoon_breakdown",
                    inputs=agent_context,
                    task_id=task_id
                )
                if isinstance(plot_points, dict):
                    plot_points = plot_points.get("plot_points", plot_points.get("results", []))
            except Exception as e2:
                logger.error(f"Skill 执行失败: {e2}")
                raise AITaskException(code="SKILL_EXECUTION_ERROR", message=str(e2))

            # 检查 plot_points 是否为空
            if not plot_points or len(plot_points) == 0:
                logger.error(f"Skill 回退模式返回空 plot_points！原始 Agent 错误: {agent_error_msg}")
                raise AITaskException(
                    code="EMPTY_RESULT",
                    message="AI 未能生成有效的剧情拆解结果",
                    suggestion="这可能是由于章节内容太少或格式问题导致的。建议：1) 检查章节内容是否足够长；2) 尝试重新运行任务；3) 如果问题持续，请联系技术支持。"
                )

            update_task_progress_sync(db, task_id, progress=50, current_step="[Skill回退模式] 拆解结束 (50%)")
            # 执行 QA 质检
            logger.info("回退到 Skill 模式，执行 QA 质检...")
            _raise_if_cancelled_sync(db, task_id)
            qa_result = _run_breakdown_qa_sync(
                db=db,
                task_id=task_id,
                plot_points=plot_points,
                chapters_text=chapters_text,
                adapt_method=adapt_method,
                model_adapter=model_adapter,
                log_publisher=log_publisher,
                hook_types=agent_context.get("hook_types"),
                hook_boundary_rules=agent_context.get("hook_boundary_rules"),
                genre_guidelines=agent_context.get("genre_guidelines"),
                qa_dimensions=agent_context.get("qa_dimensions")
            )
            qa_status = qa_result.get("qa_status", "pending")
            qa_score = qa_result.get("qa_score")
            qa_report = qa_result
            # 记录回退原因到 qa_report
            if qa_report is None:
                qa_report = {}
            qa_report["skill_fallback"] = True
            qa_report["fallback_reason"] = agent_error_msg[:200]
            logger.info(f"Skill + QA 模式完成，qa_status: {qa_status}, qa_score: {qa_score}")
            update_task_progress_sync(db, task_id, progress=80, current_step="质检Agent 已完成质检 (80%)")

    # -------------------- 补充质检（Agent 模式可能跳过 QA）--------------------
    # Agent 工作流中 QA 步骤可能因为条件不满足被跳过
    # 补充质检条件：非回退模式 且 (qa_status 为 pending 或 qa_report 为空/无效)
    needs_supplementary_qa = (
        not used_skill_fallback and
        (qa_status == "pending" or not qa_report or not qa_report.get("qa_status"))
    )
    if needs_supplementary_qa:
        logger.info("Agent 模式无有效 QA 结果，补充执行质检...")
        _raise_if_cancelled_sync(db, task_id)
        qa_result = _run_breakdown_qa_sync(
            db=db,
            task_id=task_id,
            plot_points=plot_points,
            chapters_text=chapters_text,
            adapt_method=adapt_method,
            model_adapter=model_adapter,
            log_publisher=log_publisher,
            hook_types=agent_context.get("hook_types"),
            hook_boundary_rules=agent_context.get("hook_boundary_rules"),
            genre_guidelines=agent_context.get("genre_guidelines"),
            qa_dimensions=agent_context.get("qa_dimensions")
        )
        qa_status = qa_result.get("qa_status", "pending")
        qa_score = qa_result.get("qa_score")
        qa_report = qa_result

    # 确保 plot_points 是列表
    if not isinstance(plot_points, list):
        plot_points = [plot_points] if plot_points else []

    # -------------------- 自动修正循环 --------------------
    # agent_loop 模式：禁用外部修正（Agent 内部已经循环质检了）
    # agent_single / skill_only 模式：启用外部修正（局部修正）
    max_auto_fix_retries = task_config.get("max_auto_fix_retries", 3)
    auto_fix_enabled = task_config.get("auto_fix_on_fail", True)

    # agent_loop 模式禁用外部修正
    if execution_mode == "agent_loop" and not used_skill_fallback:
        auto_fix_enabled = False
        logger.info("agent_loop 模式：禁用外部自动修正")

    fix_attempt = 0

    # 标准化 qa_status（统一转为大写）
    normalized_qa_status = qa_status.upper() if isinstance(qa_status, str) else "PENDING"
    logger.info(f"质检状态标准化: 原始={qa_status}, 标准化={normalized_qa_status}")

    # 判断是否需要自动修正（FAIL 或得分低于 60 分）
    needs_fix = (
        normalized_qa_status == "FAIL" or
        (qa_score is not None and qa_score < 60)
    )

    # 自动修正循环：质检不通过时反复修正，直到通过或达到最大次数
    while (auto_fix_enabled and
           needs_fix and
           fix_attempt < max_auto_fix_retries and
           qa_report):

        fix_attempt += 1
        _raise_if_cancelled_sync(db, task_id)
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

        # 从 QA 报告中提取修正指令
        fix_instructions = _extract_fix_instructions_from_qa_report(qa_report)

        if not fix_instructions:
            logger.info("无法提取修正指令，跳过自动修正")
            break

        # 执行自动修正：根据 QA 反馈修改 plot_points
        plot_points = _auto_fix_breakdown_sync(
            plot_points=plot_points,
            fix_instructions=fix_instructions,
            chapters_text=chapters_text,
            model_adapter=model_adapter,
            log_publisher=log_publisher,
            task_id=task_id,
            db=db,
            adapt_method=adapt_method
        )

        # 修正后重新执行质检
        logger.info(f"第 {fix_attempt} 次修正完成，重新执行质检...")
        _raise_if_cancelled_sync(db, task_id)
        qa_result = _run_breakdown_qa_sync(
            db=db,
            task_id=task_id,
            plot_points=plot_points,
            chapters_text=chapters_text,
            adapt_method=adapt_method,
            model_adapter=model_adapter,
            log_publisher=log_publisher,
            hook_types=agent_context.get("hook_types"),
            hook_boundary_rules=agent_context.get("hook_boundary_rules"),
            genre_guidelines=agent_context.get("genre_guidelines"),
            qa_dimensions=agent_context.get("qa_dimensions")
        )
        qa_status = qa_result.get("qa_status", "pending")
        qa_score = qa_result.get("qa_score")
        qa_report = qa_result

        logger.info(f"第 {fix_attempt} 次修正后质检结果: status={qa_status}, score={qa_score}")

        # 重新计算是否需要继续修正
        normalized_qa_status = qa_status.upper() if isinstance(qa_status, str) else "PENDING"
        needs_fix = (
            normalized_qa_status == "FAIL" or
            (qa_score is not None and qa_score < 60)
        )

        # 质检通过，退出循环
        if not needs_fix:
            if log_publisher:
                log_publisher.publish_success(
                    task_id,
                    f"第 {fix_attempt} 次修正后质检通过！得分: {qa_score}"
                )
            break

    # 记录最终修正次数（用于数据分析）
    if fix_attempt > 0:
        if qa_report is None:
            qa_report = {}
        qa_report["auto_fix_attempts"] = fix_attempt
        normalized_final_status = qa_status.upper() if isinstance(qa_status, str) else "PENDING"
        qa_report["auto_fix_success"] = normalized_final_status == "PASS" or (qa_score is not None and qa_score >= 60)

    update_task_progress_sync(db, task_id, progress=90, current_step=f"拆解完成，生成 {len(plot_points)} 个剧情点 (90%)")

    # -------------------- 第五步：保存结果到数据库 --------------------
    # 标准化 qa_status（前端期望 'PASS' | 'FAIL' | 'ERROR' | 'pending'）
    if isinstance(qa_status, str):
        upper_status = qa_status.upper()
        if upper_status in ("PASS", "FAIL", "ERROR"):
            normalized_qa_status_for_db = upper_status
        else:
            normalized_qa_status_for_db = "pending"
    else:
        normalized_qa_status_for_db = "pending"

    # 诊断日志：记录保存到数据库的值
    logger.info(f"[breakdown_tasks] 保存数据库: plot_points={len(plot_points)}, qa_status={normalized_qa_status_for_db}, qa_score={qa_score}")

# 获取 ai_model_id（来自 project.breakdown_model_id，指向 ai_models 表）
    ai_model_id = task_config.get("model_config_id")

    # 创建 PlotBreakdown 记录
    breakdown = PlotBreakdown(
        batch_id=batch_id,
        project_id=project_id,
        task_id=task_id,
        ai_model_id=ai_model_id,
        model_config_id=None,
        plot_points=plot_points,
        format_version=3,
        consistency_status="pending",
        qa_status=normalized_qa_status_for_db,
        qa_score=qa_score,
        qa_report=qa_report,
        used_adapt_method_id=task_config.get("adapt_method_id"),
    )

    db.add(breakdown)
    db.commit()

    # 更新进度并返回结果
    update_task_progress_sync(db, task_id, progress=95, current_step="拆解结果已保存 (95%)")

    return {
        "breakdown_id": str(breakdown.id),
        "format_version": 3,
        "plot_points_count": len(plot_points),
        "qa_status": qa_status,
        "qa_score": qa_score,
        "use_agent": not used_skill_fallback,  # 实际是否使用了 Agent 模式
        "skill_fallback": used_skill_fallback,  # 是否使用了 Skill 回退
        "fallback_reason": qa_report.get("fallback_reason") if qa_report and used_skill_fallback else None,
    }


def _raise_if_cancelled_sync(db: Session, task_id: str) -> None:
    task = db.query(AITask).filter(AITask.id == task_id).first()
    if task and task.status in (TaskStatus.CANCELLING, TaskStatus.CANCELED, "cancelled"):
        raise TaskCancelledError("任务已被取消")


def _handle_task_cancelled_sync(
    db: Session,
    task_id: str,
    batch_record,
    task_record,
    user_id: str,
    log_publisher=None,
    message: str = "任务已被取消"
):
    """处理任务取消

    积分处理策略：
    - 检查是否已在 API 端处理过积分（通过 task.result.api_handled_credits 标记）
    - 如果已处理，跳过积分操作
    - 如果未处理：有 Token 消耗则扣除费用，无 Token 消耗则返还预扣积分
    """
    from app.core.quota import refund_episode_quota_sync

    try:
        # 如果当前事务已经 abort，先回滚
        try:
            db.rollback()
        except Exception:
            pass

        # rollback 后重新查询 ORM 对象，避免 detached 状态
        task_record = db.query(AITask).filter(AITask.id == task_id).first()
        batch_record = db.query(Batch).filter(Batch.id == task_record.batch_id).first() if task_record else None

        # 检查是否已在 API 端处理过积分（防止重复扣费）
        api_handled_credits = False
        if task_record and task_record.result and isinstance(task_record.result, dict):
            api_handled_credits = task_record.result.get("api_handled_credits", False)

        # 更新任务状态为 canceled
        if task_record:
            task_record.status = TaskStatus.CANCELED
            task_record.current_step = "用户已取消"
            task_record.error_message = None

        # 批次状态与任务状态保持同步：任务取消 => batch.pending
        if batch_record:
            batch_record.breakdown_status = map_task_status_to_batch(TaskStatus.CANCELED) or BatchStatus.PENDING

        db.commit()

        # 如果已在 API 端处理过积分，跳过积分操作
        if api_handled_credits:
            logger.info(f"任务取消：积分已在 API 端处理，跳过 Celery 回调中的积分操作: task_id={task_id}")
        else:
            # 积分处理：检查是否有 Token 消耗
            task_config = task_record.config if task_record else {}
            token_result = consume_token_credits_sync(
                db=db,
                user_id=user_id,
                task_id=task_id,
                task_type=TaskType.BREAKDOWN,
                model_config_id=task_config.get("model_config_id")
            )

            token_consumed = token_result.get("token_credits", 0) > 0

            if token_consumed:
                # 有 Token 消耗，扣除费用
                db.commit()
                logger.info(
                    f"任务取消但仍扣除 Token 费用: input={token_result.get('input_tokens', 0)}, "
                    f"output={token_result.get('output_tokens', 0)}, "
                    f"credits={token_result.get('token_credits', 0)}"
                )
            else:
                # 无 Token 消耗，返还预扣的基础积分
                try:
                    refund_episode_quota_sync(db, user_id, 1, auto_commit=False)
                    db.commit()
                    logger.info(f"任务取消，已返还基础积分: user_id={user_id}, task_id={task_id}")
                except Exception as refund_error:
                    logger.error(f"返还基础积分失败: {refund_error}")
                    db.rollback()

        if log_publisher:
            try:
                log_publisher.publish_warning(task_id, message)
                log_publisher.publish_task_complete(task_id, status=TaskStatus.CANCELED, message=message)
            except Exception:
                pass

    except Exception as e:
        # 如果更新状态失败，记录日志但不抛出异常
        logger.error(f"处理任务取消时出错: {e}")
        try:
            db.rollback()
        except Exception:
            pass



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


def _check_previous_breakdown_success(db: Session, batch_id: str, current_task_id: str) -> bool:
    """检查批次是否有之前成功的拆解结果

    Args:
        db: 数据库会话
        batch_id: 批次 ID
        current_task_id: 当前失败的任务 ID

    Returns:
        bool: 如果有之前成功的拆解结果返回 True，否则返回 False
    """
    from app.models.plot_breakdown import PlotBreakdown
    from app.models.ai_task import AITask

    try:
        # 查找该批次下所有成功完成的任务（排除当前失败的任务）
        successful_tasks = db.query(AITask).filter(
            AITask.batch_id == batch_id,
            AITask.id != current_task_id,
            AITask.status == TaskStatus.COMPLETED
        ).all()

        if not successful_tasks:
            return False

        # 检查是否有对应的有效拆解结果
        for task in successful_tasks:
            breakdown = db.query(PlotBreakdown).filter(
                PlotBreakdown.batch_id == batch_id,
                PlotBreakdown.task_id == task.id,
                PlotBreakdown.plot_points.isnot(None)  # 有有效的剧情点数据
            ).first()

            if breakdown and breakdown.plot_points:
                # 检查剧情点数量是否合理（至少有1个）
                if isinstance(breakdown.plot_points, list) and len(breakdown.plot_points) > 0:
                    logger.info(
                        f"批次 {batch_id} 找到之前的成功结果: "
                        f"breakdown_id={breakdown.id}, "
                        f"plot_points={len(breakdown.plot_points)}, "
                        f"qa_status={breakdown.qa_status}"
                    )
                    return True

        return False

    except Exception as e:
        logger.error(f"检查之前的拆解结果失败: {e}")
        return False


def _update_batch_status_safely(
    batch,
    task,
    new_status: str,
    db,
    logger
) -> None:
    """
    安全地更新批次状态，应用智能回滚机制

    核心逻辑：
    1. 根据任务类型确定要更新的状态字段（breakdown_status 或 script_status）
    2. 如果要设置为 failed，检查是否有之前的成功结果
    3. 有成功结果则恢复为 completed，保护用户已有成果

    Args:
        batch: 批次对象
        task: 任务对象（用于获取 task_type）
        new_status: 新状态（BatchStatus 常量）
        db: 数据库会话
        logger: 日志对象
    """
    from app.core.status import BatchStatus, TaskStatus, TaskType

    # 1. 根据任务类型确定要更新的字段
    task_type = task.task_type

    if task_type == TaskType.BREAKDOWN:
        status_field = "breakdown_status"
    elif task_type == TaskType.EPISODE_SCRIPT:
        status_field = "script_status"
    else:
        logger.warning(f"未知任务类型: {task_type}，默认更新 breakdown_status")
        status_field = "breakdown_status"

    # 2. 如果要设置为 failed，检查是否有之前的成功结果（仅对 breakdown 任务）
    if new_status == BatchStatus.FAILED and task_type == TaskType.BREAKDOWN:
        has_success = _check_previous_breakdown_success(db, batch.id, task.id)
        if has_success:
            new_status = BatchStatus.COMPLETED
            logger.info(f"批次 {batch.id} 有之前的成功结果，{status_field} 恢复为 completed")
        else:
            logger.info(f"批次 {batch.id} 无之前的成功结果，{status_field} 更新为 failed")

    # 3. 更新状态
    old_status = getattr(batch, status_field)
    setattr(batch, status_field, new_status)
    logger.info(f"批次 {batch.id} 的 {status_field}: {old_status} → {new_status}")


def _validate_status_consistency(batch, task, logger) -> None:
    """
    验证状态字段与任务类型的一致性

    目的：在任务完成后检查批次状态是否正确更新，及时发现状态管理问题

    Args:
        batch: 批次对象
        task: 任务对象
        logger: 日志对象
    """
    from app.core.status import BatchStatus, TaskStatus, TaskType

    task_type = task.task_type
    task_status = task.status

    if task_type == TaskType.BREAKDOWN:
        # 拆解任务应该更新 breakdown_status
        if task_status == TaskStatus.COMPLETED:
            if batch.breakdown_status == BatchStatus.COMPLETED:
                logger.info(f"✅ 批次 {batch.id} 拆解状态正确: {batch.breakdown_status}")
            else:
                logger.warning(
                    f"⚠️ 批次 {batch.id} 拆解任务已完成，但 breakdown_status 为 {batch.breakdown_status}"
                )
        elif task_status == TaskStatus.FAILED:
            if batch.breakdown_status in [BatchStatus.FAILED, BatchStatus.COMPLETED]:
                logger.info(f"✅ 批次 {batch.id} 拆解失败状态正确: {batch.breakdown_status}")
            else:
                logger.warning(
                    f"⚠️ 批次 {batch.id} 拆解任务失败，但 breakdown_status 为 {batch.breakdown_status}"
                )

    elif task_type == TaskType.EPISODE_SCRIPT:
        # 剧本任务应该更新 script_status
        if task_status == TaskStatus.COMPLETED:
            if batch.script_status == BatchStatus.COMPLETED:
                logger.info(f"✅ 批次 {batch.id} 剧本状态正确: {batch.script_status}")
            else:
                logger.warning(
                    f"⚠️ 批次 {batch.id} 剧本任务已完成，但 script_status 为 {batch.script_status}"
                )

        # 关键检查：剧本任务不应该影响 breakdown_status
        if batch.breakdown_status == BatchStatus.FAILED and task_status == TaskStatus.FAILED:
            logger.error(
                f"❌ 批次 {batch.id} 剧本任务失败，但错误地将 breakdown_status 设置为 failed！"
            )


def _extract_fix_instructions_from_qa_report(qa_report: dict) -> str:
    """从 QA 报告中提取修正指令

    支持新格式（结构化文本解析后的 dict）和旧格式（JSON 解析后的 dict）。
    将问题列表和修复指引组合成提示词，用于自动修正。

    Args:
        qa_report: QA 质检报告

    Returns:
        str: 格式化的修正指令文本
    """
    if not qa_report:
        return ""

    # 检查是否是新格式（dimensions 是 list 且包含 fix_suggestion）
    dimensions = qa_report.get("dimensions", [])
    if isinstance(dimensions, list) and dimensions:
        first_dim = dimensions[0] if dimensions else {}
        if isinstance(first_dim, dict) and "fix_suggestion" in first_dim:
            # 新格式：使用 format_qa_result_to_text
            from app.ai.simple_executor import format_qa_result_to_text
            return format_qa_result_to_text(qa_report)

    # 旧格式：保持原有逻辑
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

    # 3. 提取各维度的详细问题
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
    task_id: str = None,
    db: Session = None,
    adapt_method: str = ""
) -> list:
    """根据质检反馈自动修正剧情点（复用 webtoon_breakdown Skill 的修复模式）

    优化版本：
    - 复用 webtoon_breakdown Skill，使用 previous_plot_points 和 qa_feedback 参数触发修复模式
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
        db: 数据库会话（可选，用于调用 Skill）
        adapt_method: 改编方法论（可选）

    Returns:
        list: 修正后的剧情点 JSON 数组
    """
    from app.ai.simple_executor import format_plot_points_to_text, parse_text_plot_points, format_qa_feedback_to_text

    step_name = "自动修正剧情点"

    if log_publisher and task_id:
        log_publisher.publish_step_start(task_id, step_name)

    # 解析修正指令
    instructions_list = []
    instructions_text = ""

    if isinstance(fix_instructions, list):
        instructions_list = fix_instructions
        instructions_text = format_qa_feedback_to_text(fix_instructions)
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

    # 优先使用 webtoon_breakdown Skill 进行修复（如果有 db 会话）
    if db is not None:
        try:
            from app.ai.simple_executor import SimpleSkillExecutor

            skill_executor = SimpleSkillExecutor(db, model_adapter, log_publisher)

            # 调用 webtoon_breakdown Skill（修复模式）
            result = skill_executor.execute_skill(
                skill_name="webtoon_breakdown",
                inputs={
                    "previous_plot_points": plot_points,  # 上一轮结果，触发修复模式
                    "qa_feedback": instructions_text,  # 质检反馈
                    "chapters_text": chapters_text[:5000],  # 限制长度
                    "adapt_method": adapt_method or "",
                    "output_style": "",  # 修复模式下可为空
                    "template": "",  # 修复模式下可为空
                    "example": "",  # 修复模式下可为空
                    "start_chapter": 1,  # 修复模式下使用默认值
                    "end_chapter": 1,  # 修复模式下使用默认值
                    "start_episode": 1  # 修复模式下使用默认值
                },
                task_id=task_id
            )

            # 确保返回列表
            if isinstance(result, list) and result:
                if log_publisher and task_id:
                    log_publisher.publish_step_end(
                        task_id, step_name,
                        {"status": "success", "method": "skill_repair", "count": len(result)}
                    )
                return result

            logger.warning("webtoon_breakdown Skill 返回空结果，回退到直接调用模型")

        except Exception as e:
            logger.warning(f"调用 webtoon_breakdown Skill 失败，回退到直接调用模型: {e}")

    # 回退：直接调用模型（兼容没有 db 会话的情况）
    plot_points_text = format_plot_points_to_text(plot_points)

    prompt = f"""你是一个专业的剧情拆解修正专家。请根据质检反馈修正以下剧情点。

## 当前剧情点
{plot_points_text}

## 质检修正指令
{instructions_text}

## 原文参考
{chapters_text[:3000]}
{"..." if len(chapters_text) > 3000 else ""}

## 修正要求
1. 严格按照修正指令进行修改
2. 只修改需要修正的部分，不要改动正确的内容
3. 确保修正后的内容与原文一致
4. 每个剧情点必须包含：场景、角色、事件、情绪钩子类型、集数

## 输出格式（必须严格遵循）
每个剧情点占一行，使用 | 分隔各字段，格式如下：
【剧情N】场景地点|角色A/角色B|事件描述|情绪钩子类型|第X集|第Y章

请直接输出修正后的完整剧情点列表，每行一个，不要输出 JSON 或其他格式。
"""

    try:
        full_response = ""
        for chunk in model_adapter.stream_generate(prompt):
            if log_publisher and task_id:
                log_publisher.publish_stream_chunk(task_id, step_name, chunk)
            full_response += chunk

        # 优先尝试结构化文本格式解析
        if '【剧情' in full_response:
            result = parse_text_plot_points(full_response)
            if result:
                if log_publisher and task_id:
                    log_publisher.publish_step_end(
                        task_id, step_name,
                        {"status": "success", "method": "ai_fix_text", "count": len(result)}
                    )
                return result

        # 回退到 JSON 解析
        from app.ai.simple_executor import parse_llm_response
        result = parse_llm_response(full_response, default=plot_points)

        # 确保返回列表
        if isinstance(result, dict):
            result = result.get("plot_points", result.get("results", [result]))
        if not isinstance(result, list):
            result = [result]

        # 防止返回空列表导致数据丢失
        if not result or len(result) == 0:
            logger.warning("AI 修正返回空结果，保留原始剧情点")
            if log_publisher and task_id:
                log_publisher.publish_warning(
                    task_id,
                    "修正结果为空，已保留原始剧情点"
                )
            return plot_points

        if log_publisher and task_id:
            log_publisher.publish_step_end(
                task_id, step_name,
                {"status": "success", "method": "ai_fix_json", "count": len(result)}
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


def _format_qa_report_for_console(qa_result: dict) -> str:
    """将 QA 结果格式化为易读的文本（用于 Console Logger 显示）

    Args:
        qa_result: QA 结果字典

    Returns:
        str: 格式化后的质检报告文本
    """
    if not qa_result:
        return "质检结果为空"

    lines = []
    lines.append("【质检报告】")

    # 总分和状态
    score = qa_result.get("qa_score", 0)
    status = qa_result.get("qa_status", "pending")
    status_icon = "✅ PASS" if status == "PASS" else "❌ FAIL"
    lines.append(f"总分：{score}/100")
    lines.append(f"状态：{status_icon}")
    lines.append("")

    # 各维度评分
    lines.append("【维度评分】")
    dimensions = qa_result.get("dimensions", [])
    if dimensions:
        for idx, dim in enumerate(dimensions, 1):
            name = dim.get("name", "")
            dim_score = dim.get("score", 0)
            # max_score = dim.get("max_score", 12.5)  # 不再显示满分
            passed = dim.get("passed", False)
            # 状态: 通过/未通过/失败
            if passed:
                status = "通过"
            else:
                status = "未通过"
            lines.append(f"【维度{idx}】{name} 评分 {dim_score} {status}")
    else:
        lines.append("（无维度评分数据）")

    return "\n".join(lines)


def _run_breakdown_qa_sync(
    db: Session,
    task_id: str,
    plot_points: list,
    chapters_text: str,
    adapt_method: str,
    model_adapter,
    log_publisher=None,
    hook_types: str = "",
    hook_boundary_rules: str = "",
    genre_guidelines: str = "",
    qa_dimensions: str = ""
) -> dict:
    """执行剧情拆解 QA 质检

    调用 breakdown_aligner skill 对拆解结果进行质量检查。
    只支持结构化文本 QA 报告格式，解析失败直接报错。

    Args:
        db: 数据库会话
        task_id: 任务 ID
        plot_points: 剧情点列表
        chapters_text: 章节文本
        adapt_method: 改编方法论
        model_adapter: 模型适配器
        log_publisher: 日志发布器
        hook_types: 钩子类型定义文档内容
        hook_boundary_rules: 钩子边界规则文档内容
        genre_guidelines: 类型特性指南文档内容
        qa_dimensions: 质检维度定义文档内容

    Returns:
        dict: 质检结果

    Raises:
        ValueError: QA 报告解析失败
    """
    from app.ai.simple_executor import SimpleSkillExecutor, parse_text_qa_result

    try:
        # 调用 breakdown_aligner skill
        skill_executor = SimpleSkillExecutor(db, model_adapter, log_publisher)
        result = skill_executor.execute_skill(
            skill_name="breakdown_aligner",
            inputs={
                "plot_points": plot_points,
                "chapters_text": chapters_text,
                "adapt_method": adapt_method or "",
                "hook_types": hook_types or HOOK_TYPES_COMPACT_DEFAULT,
                "hook_boundary_rules": hook_boundary_rules or HOOK_BOUNDARY_RULES_DEFAULT,
                "genre_guidelines": genre_guidelines or GENRE_GUIDELINES_DEFAULT,
                "qa_dimensions": qa_dimensions or QA_DIMENSIONS_DEFAULT
            },
            task_id=task_id
        )

        # QA 结果解析：优先结构化文本格式，支持降级处理
        if isinstance(result, str):
            if '【质检报告】' in result:
                result = parse_text_qa_result(result)
                # 降级处理：如果解析不完整，使用默认值而非报错
                if not result.get("qa_status"):
                    # 根据分数推断状态
                    score = result.get("qa_score")
                    if score is not None:
                        result["qa_status"] = "PASS" if score >= 70 else "FAIL"
                    else:
                        result["qa_status"] = "FAIL"  # 无分数默认失败
                    logger.warning(f"QA 报告缺少 qa_status，已根据分数推断为: {result['qa_status']}")
                if result.get("qa_score") is None:
                    result["qa_score"] = 0  # 默认0分
                    logger.warning("QA 报告缺少 qa_score，已设置默认值: 0")
            else:
                # LLM 没有按照要求的格式输出，尝试降级处理
                logger.warning(f"QA 报告格式错误：未找到【质检报告】标记。响应片段: {result[:200]}...")
                if log_publisher:
                    log_publisher.publish_warning(
                        task_id,
                        "质检输出格式不标准，已使用降级处理"
                    )
                # 降级方案：创建默认的失败报告
                result = {
                    "qa_status": "FAIL",
                    "qa_score": 0,
                    "dimensions": [],
                    "issues": [{"description": "QA 报告格式不符合要求，无法解析"}],
                    "fix_instructions": [],
                    "degraded": True,  # 标记为降级处理
                    "raw_response": result[:500]  # 保留原始响应片段用于调试
                }

        # 兼容 list 类型（可能是解析器误判，尝试提取 dict）
        if isinstance(result, list):
            if len(result) == 1 and isinstance(result[0], dict):
                result = result[0]
                logger.warning("QA 结果为单元素 list，已自动提取 dict")
            elif len(result) == 0:
                error_msg = "QA 结果为空列表，解析失败"
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                # list 中有多个元素，说明解析器把 QA 报告误判为剧情点了
                error_msg = f"QA 结果类型错误：解析器可能误判为剧情点格式。结果数量: {len(result)}"
                logger.error(error_msg)
                raise ValueError(error_msg)

        # 验证结果是 dict 类型
        if not isinstance(result, dict):
            error_msg = f"QA 结果类型错误：期望 dict，实际 {type(result).__name__}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        qa_status = result.get("qa_status", "pending")
        qa_score = result.get("qa_score")

        # 发布 QA 完成
        if log_publisher:
            # 发布格式化质检报告
            formatted_text = _format_qa_report_for_console(result)
            log_publisher.publish_formatted_chunk(
                task_id=task_id,
                step_name="质检报告",
                formatted_text=formatted_text
            )

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
        return result

    except ValueError:
        # ValueError 直接抛出，不要吞掉
        raise
    except Exception as e:
        logger.error(f"QA 质检失败: {e}")
        if log_publisher:
            log_publisher.publish_error(
                task_id,
                f"质检失败: {str(e)}",
                error_code="QA_ERROR"
            )
        raise ValueError(f"QA 质检执行失败: {str(e)}") from e


# ==================== 默认资源加载辅助函数 ====================

def _load_default_resource_sync(db: Session, category: str) -> str:
    """加载指定分类的系统默认资源

    当用户没有选择特定资源时，自动加载系统内置的默认资源。

    Args:
        db: 数据库会话
        category: 资源分类（hook_types/hook_rules/type_guide/qa_dimensions）

    Returns:
        str: 资源内容，如果不存在则返回空字符串
    """
    from app.models.ai_resource import AIResource

    resource = db.query(AIResource).filter(
        AIResource.category == category,
        AIResource.is_builtin == True,
        AIResource.is_active == True
    ).first()

    return resource.content if resource else ""


# ==================== 向后兼容默认值常量 ====================
# 当数据库资源不存在时，使用这些硬编码默认值

HOOK_TYPES_COMPACT_DEFAULT = """
【爽感类】打脸蓄力、打脸爽点、碾压爽点、绝境反杀、装X成功、以弱胜强
【震撼类】身份曝光、真相揭露、反转冲击、背叛揭露、阴谋曝光
【虐心类】虐心痛点、生离死别、误会虐心、牺牲奉献、无奈抉择
【悬念类】悬念设置、伏笔埋设、危机预告、神秘出现
【成长类】金手指觉醒、实力突破、获得宝物、人物结交、拜师学艺
【情感类】心动瞬间、表白告白、误会和解、守护承诺、甜蜜互动
【冲突类】正面对决、危机降临、被陷害、势力对抗、生死危机
""".strip()

HOOK_BOUNDARY_RULES_DEFAULT = """
【易混淆钩子区分】
- 打脸蓄力 vs 打脸爽点：主角"被打脸"=蓄力，主角"打别人脸"=爽点
- 碾压爽点 vs 打脸爽点：有"之前被看不起"的铺垫=打脸，无铺垫直接碾压=碾压
- 真相揭露 vs 身份曝光：揭露的是"事"=真相，揭露的是"人"=身份
- 悬念设置 vs 真相揭露：观众"更好奇"=悬念，观众"恍然大悟"=真相
- 人物结交 vs 打脸蓄力：对方态度"友好"=结交，对方态度"敌意"=蓄力
""".strip()

GENRE_GUIDELINES_DEFAULT = """
【都市爽文类】
- 必保留：打脸场景、身份反转、实力碾压
- 必删除：日常生活、感情纠葛（除非是核心线）
- 节奏要求：快节奏，每集必须有爽点

【悬疑推理类】
- 必保留：线索铺设、真相揭露、反转
- 必删除：无关的日常、过多的心理描写
- 节奏要求：信息密度高，每集必须有新线索或新悬念

【言情甜宠类】
- 必保留：互动场景、情感升温、误会与和解
- 必删除：与感情线无关的支线
- 节奏要求：甜虐交替，每集必须有心动或心痛瞬间

【玄幻修仙类】
- 必保留：战斗场景、实力提升、宝物获取
- 必删除：修炼过程的详细描述、世界观解释
- 节奏要求：升级打怪节奏，每集必须有战斗或突破

【重生复仇类】
- 必保留：复仇计划推进、打脸前世仇人、改变命运
- 必删除：前世回忆（除非是关键信息）
- 节奏要求：复仇进度推进，每集必须有复仇成果
""".strip()

QA_DIMENSIONS_DEFAULT = """
【角色定义】
你是"网文改编漫剧剧情拆解质量校验员(breakdown-aligner)"，负责对剧情拆解结果进行多维度质量检查。

核心职责：确保拆解结果符合改编方法论要求、验证剧情点的完整性和准确性、检查钩子类型和分集标注的合理性、输出可执行的修改建议。

【检查步骤】
第一步：读取基准文档（改编方法论 adapt-method.md + 原文 + 待检查内容）
第二步：执行 8 维度检查
第三步：汇总问题
第四步：输出结果（PASS/FAIL）

【通过标准】总分 ≥ 70 分，优秀标准 ≥ 85 分，任一维度 0 分自动不及格

【维度1：冲突强度评估】
强度评判标准：⭐⭐⭐ 高强度（改变主角命运、大幅改变格局、生死攸关）| ⭐⭐ 中强度（推动剧情发展、影响人物关系）| ⭐ 低强度（日常冲突、小摩擦、铺垫性质）
评分标准：12.5分=所有高强度冲突都符合标准 | 8-10分=个别偏差 | 5-7分=多个不准确 | 0-4分=严重误判

【维度2：情绪钩子识别】
强度评分标准：10分="卧槽！"（身份大反转、绝境反杀、真相揭露）| 8-9分=爽/虐/急（打脸爽点、虐心痛点、悬念高潮）| 6-7分=有感觉（小打脸、小甜蜜、小悬念）| 4-5分=一般（日常互动、铺垫情节）
评分标准：12.5分=全部正确 | 8-10分=个别有误 | 5-7分=多个错误 | 0-4分=大量错误
自检要点：是否有易混淆钩子标注错误？10分钩子是否真的能让观众"卧槽"？

【维度3：冲突密度达标性】
密度标准：高潮章节=核心冲突5+，高强度钩子6-8个 | 过渡章节=核心冲突2-4，高强度钩子3-5个 | 铺垫章节=核心冲突0-2，高强度钩子1-2个（需说明铺垫目的）
评分标准：12.5分=符合预期 | 8-10分=略低可接受 | 5-7分=偏低影响观感 | 0-4分=严重不足

【维度4：分集标注合理性】
分集规则：10分钩子=必须单独成集作为集尾 | 8-9分=建议单独成集或作为集尾 | 6-7分=可与其他合并
每集剧情点合理数量：1-3个
评分标准：12.5分=节奏完美 | 8-10分=个别略有问题 | 5-7分=多集节奏不当 | 0-4分=分集混乱

【维度5：压缩策略正确性】
必删清单：❌ 环境描写超过20字 | ❌ 纯心理独白 | ❌ 与主线无关的过渡场景 | ❌ 支线剧情（除非伏笔）| ❌ 重复情绪渲染
必留清单：✅ 冲突对话 | ✅ 动作场景 | ✅ 情绪爆点 | ✅ 悬念设置 | ✅ 人物关系变化
评分标准：12.5分=完美执行 | 8-10分=个别有待商榷 | 5-7分=该删没删/该留没留 | 0-4分=严重误判

【维度6：剧情点内容完整性】
数据格式：剧情点序号|场景|角色|剧情|钩子|第X集
完整性要求：场景具体到地点 | 角色=主角+关键配角 | 剧情30-50字动作+结果 | 钩子使用标准类型 | 集数用"第X集"格式
评分标准：12.5分=全部完整 | 8-10分=个别略不清楚 | 5-7分=多个缺失 | 0-4分=大量不完整

【维度7：原文还原准确性】
核查方法：对照原文检查每个剧情点 | 验证角色关系 | 确认事件顺序 | 检查是否有虚构内容
评分标准：12.5分=完全忠实 | 8-10分=个别出入 | 5-7分=多处不符 | 0-4分=严重曲解

【维度8：类型特性符合度】
各类型必保留/必删除：
- 都市爽文：必保留=打脸场景、身份反转、实力碾压 | 必删除=日常生活、无关感情线
- 悬疑推理：必保留=线索铺设、真相揭露、反转 | 必删除=无关日常、过多心理描写
- 言情甜宠：必保留=互动场景、情感升温、误会和解 | 必删除=与感情线无关支线
- 玄幻修仙：必保留=战斗场景、实力提升、宝物获取 | 必删除=修炼细节、世界观解释
- 重生复仇：必保留=复仇推进、打脸仇人、改变命运 | 必删除=前世回忆（除非关键）
评分标准：12.5分=完全符合 | 8-10分=基本符合 | 5-7分=把握不准 | 0-4分=严重偏离

【输出格式】
**【重要】必须严格按照以下格式输出，禁止使用 Markdown 格式（如 ###、** 等）**

【质检报告】
总分：XX
状态：通过/不通过

【维度1】冲突强度评估 评分 XX 通过/未通过
说明：简要说明

【维度2】情绪钩子识别 评分 XX 通过/未通过
说明：简要说明

...（维度3-8同理）

【修改清单】
1. 【剧情X】钩子类型错误：'原钩子' → '新钩子'，原因
2. 【剧情Y】分集不合理：第X集 → 第Y集，原因

**格式要点**：
- 维度格式：`【维度N】名称 评分 XX 通过/未通过`（N为阿拉伯数字1-8）
- 状态词：只能使用"通过"或"未通过"（不要用"良好"、"需调整"等）
- 评分：只写数字，不要写"/12.5分"
- 禁止使用 Markdown 格式（###、**、- 等）
- 禁止添加额外符号（⭐、✓、✗等）

**正确示例**：
【质检报告】
总分：75
状态：通过

【维度1】冲突强度评估 评分 10 通过
说明：核心冲突识别准确，高强度冲突标注正确

【维度2】情绪钩子识别 评分 6 未通过
说明：第3个剧情点钩子类型有误

【修改清单】
1. 【剧情3】钩子类型错误：'打脸蓄力' → '人物结交'，因为对方态度友好

**错误示例**（禁止使用）：
❌ ### 维度1：冲突强度评估 ⭐⭐⭐
❌ **评估结果**：8/10分
❌ 【维度1】冲突强度评估 10/12.5分 ✓ 良好
""".strip()

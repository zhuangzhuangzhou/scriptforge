"""剧情拆解Celery任务

包含重试机制、配额回滚和错误分类功能。
"""
import json
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.progress import update_task_progress
from app.core.credits import CreditsService, BREAKDOWN_BASE_CREDITS
from app.core.exceptions import (
    AITaskException,
    RetryableError,
    QuotaExceededError,
    classify_exception,
)
from app.ai.adapters import get_adapter
from app.ai.pipeline_executor import PipelineExecutor
from app.models.ai_task import AITask
from app.models.batch import Batch
from app.models.user import User
from sqlalchemy import select


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
    """执行Breakdown任务

    支持：
    - 自动重试（网络错误等可重试错误）
    - 配额回滚（任务失败时返还配额）
    - 错误分类（区分可重试/不可重试错误）
    """

    async def _run():
        # 为每个任务创建独立的数据库引擎和会话，避免事件循环冲突
        engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with AsyncSessionLocal() as db:
            batch_record = None
            task_record = None

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

            except Exception as e:
                # 未知错误：分类后处理
                classified_error = classify_exception(e)
                if isinstance(classified_error, RetryableError):
                    await _handle_retryable_error(
                        db, task_id, batch_record, task_record, classified_error
                    )
                    raise
                else:
                    await _handle_task_failure(
                        db, task_id, batch_record, task_record, user_id, classified_error
                    )
                    raise

    return asyncio.run(_run())


async def _handle_retryable_error(
    db,
    task_id: str,
    batch_record,
    task_record,
    error: RetryableError
):
    """处理可重试错误

    更新状态为retrying，等待Celery自动重试。
    """
    error_info = {
        "code": error.code,
        "message": error.message,
        "retry_count": task_record.retry_count if task_record else 0,
        "retrying_at": datetime.utcnow().isoformat(),
        "will_retry_after": error.retry_after
    }

    await update_task_progress(
        db, task_id,
        status="retrying",
        error_message=json.dumps(error_info)
    )

    if batch_record:
        batch_record.breakdown_status = "pending"
        await db.commit()


async def _handle_quota_exceeded(
    db,
    task_id: str,
    batch_record,
    task_record,
    user_id: str,
    error: QuotaExceededError
):
    """处理配额不足错误

    标记任务失败，回滚已消耗的配额。
    """
    # 回滚配额
    await _refund_quota(db, user_id)

    # 更新任务状态
    error_info = error.to_dict()
    error_info["failed_at"] = datetime.utcnow().isoformat()

    await update_task_progress(
        db, task_id,
        status="failed",
        error_message=json.dumps(error_info)
    )

    # 更新批次状态
    if batch_record:
        batch_record.breakdown_status = "failed"
        await db.commit()


async def _handle_task_failure(
    db,
    task_id: str,
    batch_record,
    task_record,
    user_id: str,
    error: AITaskException
):
    """处理任务失败（不可重试的错误）

    更新状态，记录错误信息，回滚配额。
    """
    # 回滚配额
    await _refund_quota(db, user_id)

    # 更新任务状态
    error_info = error.to_dict()
    error_info["failed_at"] = datetime.utcnow().isoformat()
    error_info["retry_count"] = task_record.retry_count if task_record else 0

    await update_task_progress(
        db, task_id,
        status="failed",
        error_message=json.dumps(error_info)
    )

    # 更新批次状态
    if batch_record:
        batch_record.breakdown_status = "failed"
        await db.commit()


async def _refund_quota(db, user_id: str):
    """回滚用户配额

    从User记录中恢复已消耗的配额。
    """
    from app.core.quota import QuotaService

    try:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user:
            quota_service = QuotaService(db)
            await quota_service.refund_episode_quota(user, 1)
            await db.commit()
    except Exception as e:
        # 配额回滚失败不应阻止错误传播
        print(f"配额回滚失败: {e}")


# 导入asyncio（Celery任务中使用）
import asyncio

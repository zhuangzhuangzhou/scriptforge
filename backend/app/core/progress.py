"""任务进度更新服务"""
from datetime import datetime
from typing import Optional
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_task import AITask
from app.models.pipeline import PipelineExecution
import json
import redis
from app.core.config import settings


async def update_task_progress(
    db: AsyncSession,
    task_id: str,
    progress: Optional[int] = None,
    current_step: Optional[str] = None,
    status: Optional[str] = None,
    error_message: Optional[str] = None,
    retry_count: Optional[int] = None,
) -> None:
    """
    更新 AITask 表的进度信息

    Args:
        db: 数据库会话
        task_id: 任务ID
        progress: 进度百分比 (0-100)
        current_step: 当前步骤描述
        status: 任务状态 (queued, blocked, running, retrying, completed, failed, canceled)
        error_message: 错误信息
        retry_count: 重试次数
    """
    ai_task_statuses = {
        "pending",
        "queued",
        "blocked",
        "running",
        "retrying",
        "completed",
        "failed",
        "canceled",
        "in_progress",
    }
    ai_task_transitions = {
        "pending": {"queued", "running", "canceled"},
        "queued": {"running", "blocked", "canceled", "failed"},  # 允许从 queued 直接失败
        "blocked": {"queued", "canceled"},
        "running": {"retrying", "completed", "failed", "canceled"},
        "retrying": {"running", "failed", "canceled"},
        "in_progress": {"retrying", "completed", "failed", "canceled"},
    }

    update_data = {}
    current_status = None
    current_retry_count = None

    if status is not None:
        if status not in ai_task_statuses:
            raise ValueError(f"无效的任务状态: {status}")
        result = await db.execute(
            select(AITask.status, AITask.retry_count).where(AITask.id == task_id)
        )
        row = result.first()
        if row:
            current_status = row[0]
            current_retry_count = row[1]
        if current_status in ai_task_transitions:
            allowed = ai_task_transitions[current_status]
            if status != current_status and status not in allowed:
                raise ValueError(f"不允许的任务状态流转: {current_status} -> {status}")

    if progress is not None:
        update_data["progress"] = progress

    if current_step is not None:
        update_data["current_step"] = current_step

    if status is not None:
        update_data["status"] = status
        # 状态变更时更新时间戳
        if status == "running":
            update_data["started_at"] = datetime.utcnow()
        elif status in ("completed", "failed", "canceled"):
            update_data["completed_at"] = datetime.utcnow()

    if error_message is not None:
        update_data["error_message"] = error_message

    if retry_count is not None:
        update_data["retry_count"] = retry_count
    elif status == "retrying":
        update_data["retry_count"] = (current_retry_count or 0) + 1

    if update_data:
        stmt = update(AITask).where(AITask.id == task_id).values(**update_data)
        await db.execute(stmt)
        await db.commit()


async def update_pipeline_execution(
    db: AsyncSession,
    execution_id: str,
    progress: Optional[int] = None,
    current_step: Optional[str] = None,
    status: Optional[str] = None,
    error_message: Optional[str] = None,
    result: Optional[dict] = None,
) -> None:
    """
    更新 PipelineExecution 表的进度信息

    Args:
        db: 数据库会话
        execution_id: 执行ID
        progress: 进度百分比 (0-100)
        current_step: 当前步骤描述
        status: 任务状态 (pending, running, completed, failed)
        error_message: 错误信息
        result: 执行结果
    """
    update_data = {}

    if progress is not None:
        update_data["progress"] = progress

    if current_step is not None:
        update_data["current_step"] = current_step

    if status is not None:
        update_data["status"] = status
        # 状态变更时更新时间戳
        if status == "running":
            update_data["started_at"] = datetime.utcnow()
        elif status in ("completed", "failed"):
            update_data["completed_at"] = datetime.utcnow()

    if error_message is not None:
        update_data["error_message"] = error_message

    if result is not None:
        update_data["result"] = result

    if update_data:
        stmt = update(PipelineExecution).where(PipelineExecution.id == execution_id).values(**update_data)
        await db.execute(stmt)
        await db.commit()


# ============================================================================
# 同步版本（用于 Celery 任务）
# ============================================================================

from sqlalchemy.orm import Session


def _publish_progress_to_redis(task_id: str, task: AITask) -> None:
    """发布任务进度到 Redis Pub/Sub

    Args:
        task_id: 任务 ID
        task: 任务对象
    """
    try:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2
        )

        # 构建进度消息
        progress_data = {
            "task_id": str(task_id),
            "status": task.status,
            "progress": task.progress or 0,
            "current_step": task.current_step or "",
            "error_message": task.error_message,
            "retry_count": task.retry_count or 0,
            "depends_on": task.depends_on or [],
            "updated_at": datetime.utcnow().isoformat()
        }

        # 发布到 Redis 频道
        channel = f"breakdown:progress:{task_id}"
        redis_client.publish(channel, json.dumps(progress_data, ensure_ascii=False))
        redis_client.close()

    except Exception as e:
        # Redis 发布失败不应影响任务执行
        print(f"[Progress] 发布到 Redis 失败: {e}")


def update_task_progress_sync(
    db: Session,
    task_id: str,
    progress: Optional[int] = None,
    current_step: Optional[str] = None,
    status: Optional[str] = None,
    error_message: Optional[str] = None,
    retry_count: Optional[int] = None,
) -> None:
    """
    更新 AITask 表的进度信息（同步版本，用于 Celery）

    Args:
        db: 同步数据库会话
        task_id: 任务ID
        progress: 进度百分比 (0-100)
        current_step: 当前步骤描述
        status: 任务状态 (queued, blocked, running, retrying, completed, failed, canceled)
        error_message: 错误信息
        retry_count: 重试次数
    """
    ai_task_statuses = {
        "pending",
        "queued",
        "blocked",
        "running",
        "retrying",
        "completed",
        "failed",
        "canceled",
        "in_progress",
    }
    ai_task_transitions = {
        "pending": {"queued", "running", "canceled"},
        "queued": {"running", "blocked", "canceled", "failed"},  # 允许从 queued 直接失败
        "blocked": {"queued", "canceled"},
        "running": {"retrying", "completed", "failed", "canceled"},
        "retrying": {"running", "failed", "canceled"},
        "in_progress": {"retrying", "completed", "failed", "canceled"},
    }

    # 查询当前任务
    task = db.query(AITask).filter(AITask.id == task_id).first()
    if not task:
        return

    # 验证状态转换
    if status is not None:
        if status not in ai_task_statuses:
            raise ValueError(f"无效的任务状态: {status}")
        
        current_status = task.status
        if current_status in ai_task_transitions:
            allowed = ai_task_transitions[current_status]
            if status != current_status and status not in allowed:
                raise ValueError(f"不允许的任务状态流转: {current_status} -> {status}")

    # 更新字段
    if progress is not None:
        task.progress = progress

    if current_step is not None:
        task.current_step = current_step

    if status is not None:
        task.status = status
        # 状态变更时更新时间戳
        if status == "running" and not task.started_at:
            task.started_at = datetime.utcnow()
        elif status in ("completed", "failed", "canceled"):
            task.completed_at = datetime.utcnow()

    if error_message is not None:
        task.error_message = error_message

    if retry_count is not None:
        task.retry_count = retry_count
    elif status == "retrying":
        task.retry_count = (task.retry_count or 0) + 1

    # 提交更改
    db.commit()

    # 发布进度更新到 Redis（用于 WebSocket 实时推送）
    _publish_progress_to_redis(task_id, task)

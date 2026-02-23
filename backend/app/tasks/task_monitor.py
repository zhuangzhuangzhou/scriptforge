"""任务监控和自动终止机制

定期检查长时间运行的任务，自动终止超时任务
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.core.database import SyncSessionLocal
from app.models.ai_task import AITask
from app.models.batch import Batch
from app.core.status import TaskStatus, BatchStatus
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)

# 任务超时阈值（秒）
TASK_TIMEOUT_THRESHOLD = 3600  # 1小时
TASK_STALE_THRESHOLD = 1800    # 30分钟无更新视为停滞


def check_and_terminate_stuck_tasks():
    """检查并终止卡住的任务

    检查条件：
    1. 状态为 running 或 processing
    2. 创建时间超过 TASK_TIMEOUT_THRESHOLD
    3. 或者更新时间超过 TASK_STALE_THRESHOLD（停滞）
    """
    db = SyncSessionLocal()
    try:
        now = datetime.now(timezone.utc)
        timeout_time = now - timedelta(seconds=TASK_TIMEOUT_THRESHOLD)
        stale_time = now - timedelta(seconds=TASK_STALE_THRESHOLD)

        # 查询超时或停滞的任务
        query = select(AITask).where(
            and_(
                AITask.status.in_([TaskStatus.RUNNING, TaskStatus.IN_PROGRESS, TaskStatus.QUEUED]),
                # 条件1: 创建时间超过1小时
                # 或条件2: 更新时间超过30分钟（停滞）
                (AITask.created_at < timeout_time) | (AITask.updated_at < stale_time)
            )
        )

        result = db.execute(query)
        stuck_tasks = result.scalars().all()

        if not stuck_tasks:
            logger.info("没有发现卡住的任务")
            return

        logger.warning(f"发现 {len(stuck_tasks)} 个卡住的任务，准备终止")

        for task in stuck_tasks:
            try:
                _terminate_stuck_task(db, task, now)
            except Exception as e:
                logger.error(f"终止任务 {task.id} 失败: {e}")
                continue

        db.commit()
        logger.info(f"成功终止 {len(stuck_tasks)} 个卡住的任务")

    except Exception as e:
        logger.error(f"检查卡住任务失败: {e}")
        db.rollback()
    finally:
        db.close()


def _terminate_stuck_task(db: Session, task: AITask, now: datetime):
    """终止单个卡住的任务

    Args:
        db: 数据库会话
        task: 任务对象
        now: 当前时间
    """
    task_id = str(task.id)
    created_at = task.created_at.replace(tzinfo=timezone.utc) if task.created_at else now
    updated_at = task.updated_at.replace(tzinfo=timezone.utc) if task.updated_at else now

    running_time = (now - created_at).total_seconds()
    idle_time = (now - updated_at).total_seconds()

    # 判断终止原因
    if running_time > TASK_TIMEOUT_THRESHOLD:
        reason = f"任务运行超时（运行时间: {int(running_time/60)} 分钟）"
    else:
        reason = f"任务停滞无响应（停滞时间: {int(idle_time/60)} 分钟）"

    logger.warning(
        f"终止卡住的任务: task_id={task_id}, "
        f"status={task.status}, progress={task.progress}, "
        f"running_time={int(running_time/60)}min, "
        f"idle_time={int(idle_time/60)}min, "
        f"reason={reason}"
    )

    # 1. 更新任务状态为 failed
    task.status = TaskStatus.FAILED
    task.error_message = f"系统自动终止: {reason}"
    task.updated_at = now

    # 2. 安全更新关联批次状态（应用智能回滚机制）
    if task.batch_id:
        batch = db.query(Batch).filter(Batch.id == task.batch_id).first()
        if batch and batch.breakdown_status in [BatchStatus.IN_PROGRESS, BatchStatus.QUEUED]:
            from app.tasks.breakdown_tasks import _update_batch_status_safely
            _update_batch_status_safely(
                batch=batch,
                task=task,
                new_status=BatchStatus.FAILED,
                db=db,
                logger=logger
            )
            batch.updated_at = now

    # 3. 尝试终止 Celery 任务（如果有 celery_task_id）
    if task.celery_task_id:
        try:
            celery_app.control.revoke(task.celery_task_id, terminate=True)
            logger.info(f"已发送 Celery 终止信号: celery_task_id={task.celery_task_id}")
        except Exception as e:
            logger.warning(f"终止 Celery 任务失败: {e}")

    # 4. 发布 Redis 通知（如果需要）
    try:
        from app.core.redis_log_publisher import RedisLogPublisher
        log_publisher = RedisLogPublisher()
        log_publisher.publish_task_complete(
            task_id,
            status=TaskStatus.FAILED,
            message=f"任务已被系统自动终止: {reason}"
        )
    except Exception as e:
        logger.warning(f"发布 Redis 通知失败: {e}")


@celery_app.task(name="monitor_and_terminate_stuck_tasks")
def monitor_and_terminate_stuck_tasks():
    """Celery 定时任务：监控并终止卡住的任务

    每 5 分钟执行一次
    """
    logger.info("开始检查卡住的任务...")
    check_and_terminate_stuck_tasks()
    logger.info("任务检查完成")

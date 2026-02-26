"""状态常量与映射规则（单一来源）"""
from typing import Optional


# AITask.status	  Batch.breakdown_status	            解释
# queued	      queued	                            任务已排队
# running /       retrying / in_progress	in_progress	拆解执行中
# completed	      completed	                            拆解完成
# failed	      failed	                            拆解失败
# canceled	      pending（或 failed）	                 取消后批次可重新提交


class TaskType:
    """任务类型常量 - 避免字符串硬编码导致的不一致问题"""
    BREAKDOWN = "breakdown"
    EPISODE_SCRIPT = "episode_script"
    CONSISTENCY_CHECK = "consistency_check"

    # 所有有效的任务类型集合
    ALL = {BREAKDOWN, EPISODE_SCRIPT, CONSISTENCY_CHECK}


class TaskStatus:
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    IN_PROGRESS = "in_progress"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

    RUNNING_SET = {RUNNING, RETRYING, IN_PROGRESS}
    ACTIVE_SET = {QUEUED, RUNNING, RETRYING, IN_PROGRESS, CANCELLING}


class BatchStatus:
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"  # 与 TaskStatus.IN_PROGRESS 统一
    COMPLETED = "completed"
    FAILED = "failed"


def normalize_task_status(status: Optional[str]) -> Optional[str]:
    if status == "processing":
        return TaskStatus.RUNNING
    if status == "cancelled":
        return TaskStatus.CANCELED
    return status


def map_task_status_to_batch(status: Optional[str]) -> Optional[str]:
    normalized = normalize_task_status(status)
    if normalized in (TaskStatus.QUEUED,):
        return BatchStatus.QUEUED
    if normalized in TaskStatus.RUNNING_SET or normalized == TaskStatus.CANCELLING:
        return BatchStatus.IN_PROGRESS
    if normalized == TaskStatus.COMPLETED:
        return BatchStatus.COMPLETED
    if normalized == TaskStatus.FAILED:
        return BatchStatus.FAILED
    if normalized == TaskStatus.CANCELED:
        return BatchStatus.PENDING
    return None

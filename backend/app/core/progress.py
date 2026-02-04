"""任务进度更新服务"""
from datetime import datetime
from typing import Optional
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_task import AITask


async def update_task_progress(
    db: AsyncSession,
    task_id: str,
    progress: Optional[int] = None,
    current_step: Optional[str] = None,
    status: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    """
    更新 AITask 表的进度信息

    Args:
        db: 数据库会话
        task_id: 任务ID
        progress: 进度百分比 (0-100)
        current_step: 当前步骤描述
        status: 任务状态 (pending, running, completed, failed)
        error_message: 错误信息
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

    if update_data:
        stmt = update(AITask).where(AITask.id == task_id).values(**update_data)
        await db.execute(stmt)
        await db.commit()

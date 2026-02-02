from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.models.batch import Batch
from app.models.ai_task import AITask
from app.api.v1.auth import get_current_user
from app.tasks.breakdown_tasks import run_breakdown_task

router = APIRouter()


class BreakdownStartRequest(BaseModel):
    """启动拆解请求"""
    batch_id: str
    model_config_id: Optional[str] = None


@router.post("/start")
async def start_breakdown(
    request: BreakdownStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """启动剧情拆解"""
    # 验证批次存在
    result = await db.execute(select(Batch).where(Batch.id == request.batch_id))
    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="批次不存在"
        )

    # 创建AI任务
    task = AITask(
        project_id=batch.project_id,
        batch_id=batch.id,
        task_type="breakdown",
        status="pending",
        config={"model_config_id": request.model_config_id}
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 启动Celery异步任务
    celery_task = run_breakdown_task.delay(
        str(task.id),
        str(batch.id),
        str(batch.project_id)
    )

    # 更新任务的celery_task_id
    task.celery_task_id = celery_task.id
    task.status = "in_progress"
    await db.commit()

    return {"task_id": str(task.id), "status": "in_progress"}


@router.get("/tasks/{task_id}")
async def get_breakdown_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取拆解任务状态"""
    result = await db.execute(select(AITask).where(AITask.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )

    return {
        "task_id": str(task.id),
        "status": task.status,
        "progress": task.progress,
        "current_step": task.current_step,
        "error_message": task.error_message
    }


@router.get("/results/{batch_id}")
async def get_breakdown_results(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取拆解结果"""
    from app.models.plot_breakdown import PlotBreakdown

    result = await db.execute(
        select(PlotBreakdown).where(PlotBreakdown.batch_id == batch_id)
    )
    breakdown = result.scalar_one_or_none()

    if not breakdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="拆解结果不存在"
        )

    return {
        "batch_id": str(breakdown.batch_id),
        "conflicts": breakdown.conflicts,
        "plot_hooks": breakdown.plot_hooks,
        "characters": breakdown.characters,
        "scenes": breakdown.scenes,
        "emotions": breakdown.emotions,
        "consistency_status": breakdown.consistency_status
    }

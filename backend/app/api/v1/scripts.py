from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.models.batch import Batch
from app.models.ai_task import AITask
from app.models.plot_breakdown import PlotBreakdown
from app.api.v1.auth import get_current_user

router = APIRouter()


class ScriptGenerateRequest(BaseModel):
    """生成剧本请求"""
    batch_id: str
    model_config_id: Optional[str] = None


@router.post("/generate")
async def generate_script(
    request: ScriptGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """生成剧本"""
    # 验证批次存在
    result = await db.execute(select(Batch).where(Batch.id == request.batch_id))
    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="批次不存在"
        )

    # 验证拆解结果存在
    result = await db.execute(
        select(PlotBreakdown).where(PlotBreakdown.batch_id == request.batch_id)
    )
    breakdown = result.scalar_one_or_none()

    if not breakdown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先完成剧情拆解"
        )

    # 创建AI任务
    from app.tasks.script_tasks import run_script_task

    task = AITask(
        project_id=batch.project_id,
        batch_id=batch.id,
        task_type="script",
        status="pending",
        config={"model_config_id": request.model_config_id, "breakdown_id": str(breakdown.id)}
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 启动Celery异步任务
    celery_task = run_script_task.delay(
        str(task.id),
        str(batch.id),
        str(batch.project_id),
        str(breakdown.id)
    )

    task.celery_task_id = celery_task.id
    task.status = "in_progress"
    await db.commit()

    return {"task_id": str(task.id), "status": "in_progress"}

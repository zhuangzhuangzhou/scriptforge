from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.models.user import User
from app.models.batch import Batch
from app.models.project import Project
from app.models.ai_task import AITask
from app.models.plot_breakdown import PlotBreakdown
from app.models.script import Script
from app.api.v1.auth import get_current_user
from app.core.quota import QuotaService

router = APIRouter()


class ScriptGenerateRequest(BaseModel):
    """生成剧本请求"""
    batch_id: str
    model_config_id: Optional[str] = None
    selected_skills: Optional[List[str]] = None
    pipeline_id: Optional[str] = None


class ScriptResponse(BaseModel):
    id: str
    project_id: str
    batch_id: str
    plot_breakdown_id: Optional[str] = None
    episode_number: int
    title: Optional[str] = None
    content: dict
    word_count: int
    scene_count: int
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("", response_model=List[ScriptResponse])
async def list_scripts(
    project_id: Optional[str] = None,
    batch_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取剧本列表"""
    query = select(Script).join(Project).where(Project.user_id == current_user.id)

    if project_id:
        query = query.where(Script.project_id == project_id)
    if batch_id:
        query = query.where(Script.batch_id == batch_id)

    query = query.order_by(Script.created_at.desc())
    result = await db.execute(query)
    scripts = result.scalars().all()
    return scripts


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(
    script_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取单个剧本"""
    result = await db.execute(
        select(Script).join(Project).where(
            Script.id == script_id,
            Project.user_id == current_user.id
        )
    )
    script = result.scalar_one_or_none()

    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="剧本不存在"
        )

    return script


@router.post("/generate")
async def generate_script(
    request: ScriptGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """生成剧本"""
    # 验证批次存在且属于当前用户
    result = await db.execute(
        select(Batch).join(Project).where(
            Batch.id == request.batch_id,
            Project.user_id == current_user.id
        )
    )
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

    # 检查剧集配额
    quota_service = QuotaService(db)
    quota = await quota_service.check_episode_quota(current_user)
    if not quota["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"剧集配额已用尽，本月已使用 {quota['used']}/{quota['limit']} 集"
        )

    # 消耗剧集配额
    await quota_service.consume_episode_quota(current_user)

    # 创建AI任务
    from app.tasks.script_tasks import run_script_task

    dep_result = await db.execute(
        select(AITask)
        .where(
            AITask.batch_id == batch.id,
            AITask.task_type == "breakdown"
        )
        .order_by(AITask.created_at.desc())
    )
    dep_task = dep_result.scalar_one_or_none()
    depends_on = [str(dep_task.id)] if dep_task else []

    task = AITask(
        project_id=batch.project_id,
        batch_id=batch.id,
        task_type="script",
        status="queued",
        depends_on=depends_on,
        config={
            "model_config_id": request.model_config_id,
            "breakdown_id": str(breakdown.id),
            "selected_skills": request.selected_skills or [],
            "pipeline_id": request.pipeline_id
        }
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 启动Celery异步任务
    celery_task = run_script_task.delay(
        str(task.id),
        str(batch.id),
        str(batch.project_id),
        str(breakdown.id),
        str(current_user.id)
    )

    task.celery_task_id = celery_task.id
    await db.commit()

    return {"task_id": str(task.id), "status": "queued"}

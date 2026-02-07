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
from app.api.v1.auth import get_current_user
from app.tasks.breakdown_tasks import run_breakdown_task
from app.core.quota import QuotaService

router = APIRouter()


class BreakdownStartRequest(BaseModel):
    """启动拆解请求"""
    batch_id: str
    model_config_id: Optional[str] = None
    selected_skills: Optional[List[str]] = None
    pipeline_id: Optional[str] = None


@router.post("/start")
async def start_breakdown(
    request: BreakdownStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """启动剧情拆解"""
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
    task = AITask(
        project_id=batch.project_id,
        batch_id=batch.id,
        task_type="breakdown",
        status="queued",
        depends_on=[],
        config={
            "model_config_id": request.model_config_id,
            "selected_skills": request.selected_skills or [],
            "pipeline_id": request.pipeline_id
        }
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 启动Celery异步任务
    celery_task = run_breakdown_task.delay(
        str(task.id),
        str(batch.id),
        str(batch.project_id),
        str(current_user.id)
    )

    # 更新任务的celery_task_id
    task.celery_task_id = celery_task.id
    await db.commit()

    return {"task_id": str(task.id), "status": "queued"}


@router.get("/tasks/{task_id}")
async def get_breakdown_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取拆解任务状态"""
    result = await db.execute(
        select(AITask).join(Project).where(
            AITask.id == task_id,
            Project.user_id == current_user.id
        )
    )
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
        "error_message": task.error_message,
        "retry_count": task.retry_count,
        "depends_on": task.depends_on or []
    }


@router.post("/start-all")
async def start_all_breakdowns(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量启动所有未拆解批次"""
    # 验证项目归属
    project_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    # 获取所有 pending 状态的批次
    pending_batches = await db.execute(
        select(Batch).where(
            Batch.project_id == project_id,
            Batch.breakdown_status == 'pending'
        ).order_by(Batch.batch_number)
    )
    batches = pending_batches.scalars().all()

    if not batches:
        return {"task_ids": [], "total": 0, "message": "没有待拆解的批次"}

    # 检查剧集配额
    quota_service = QuotaService(db)
    quota = await quota_service.check_episode_quota(current_user)
    if not quota["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"剧集配额已用尽，本月已使用 {quota['used']}/{quota['limit']} 集"
        )

    task_ids = []
    for batch in batches:
        # 消耗剧集配额
        await quota_service.consume_episode_quota(current_user)

        # 创建AI任务
        task = AITask(
            project_id=batch.project_id,
            batch_id=batch.id,
            task_type="breakdown",
            status="queued",
            depends_on=[],
            config={}
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        # 启动Celery异步任务
        celery_task = run_breakdown_task.delay(
            str(task.id),
            str(batch.id),
            str(batch.project_id),
            str(current_user.id)
        )

        task.celery_task_id = celery_task.id
        await db.commit()

        task_ids.append(str(task.id))

    return {"task_ids": task_ids, "total": len(task_ids)}


@router.post("/start-continue")
async def start_continue_breakdown(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """继续拆解：从第一个 pending 批次开始"""
    # 验证项目归属
    project_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    # 获取第一个 pending 状态的批次
    pending_batch = await db.execute(
        select(Batch).where(
            Batch.project_id == project_id,
            Batch.breakdown_status == 'pending'
        ).order_by(Batch.batch_number).limit(1)
    )
    batch = pending_batch.scalar_one_or_none()

    if not batch:
        return {"task_id": None, "batch_id": None, "message": "没有待拆解的批次"}

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
    task = AITask(
        project_id=batch.project_id,
        batch_id=batch.id,
        task_type="breakdown",
        status="queued",
        depends_on=[],
        config={}
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 启动Celery异步任务
    celery_task = run_breakdown_task.delay(
        str(task.id),
        str(batch.id),
        str(batch.project_id),
        str(current_user.id)
    )

    task.celery_task_id = celery_task.id
    await db.commit()

    return {"task_id": str(task.id), "batch_id": str(batch.id), "status": "queued"}


@router.get("/results/{batch_id}")
async def get_breakdown_results(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取拆解结果"""
    from app.models.plot_breakdown import PlotBreakdown

    # 验证批次属于当前用户
    result = await db.execute(
        select(PlotBreakdown).join(Batch).join(Project).where(
            PlotBreakdown.batch_id == batch_id,
            Project.user_id == current_user.id
        )
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
        "consistency_status": breakdown.consistency_status,
        "consistency_score": breakdown.consistency_score,
        "consistency_results": breakdown.consistency_results,
        "qa_status": breakdown.qa_status,
        "qa_report": breakdown.qa_report,
        "used_adapt_method_id": breakdown.used_adapt_method_id
    }

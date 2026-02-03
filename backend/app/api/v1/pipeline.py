from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from app.core.database import get_db
from app.models.user import User
from app.models.pipeline import Pipeline, PipelineStage, PipelineExecution
from app.api.v1.auth import get_current_user

router = APIRouter()


class PipelineCreateRequest(BaseModel):
    """创建Pipeline请求"""
    name: str
    description: Optional[str] = None
    stages: Optional[List[dict]] = None


class PipelineUpdateRequest(BaseModel):
    """更新Pipeline请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    stages: Optional[List[dict]] = None
    config: Optional[dict] = None


class PipelineExecuteRequest(BaseModel):
    """执行Pipeline请求"""
    project_id: str
    batch_id: Optional[str] = None


@router.get("/pipelines")
async def get_pipelines(
    skip: int = 0,
    limit: int = 20,
    include_default: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取Pipeline列表"""
    # 获取用户的Pipelines
    user_query = select(Pipeline).where(
        Pipeline.user_id == current_user.id,
        Pipeline.is_active == True
    ).offset(skip).limit(limit)

    user_result = await db.execute(user_query)
    user_pipelines = user_result.scalars().all()

    # 获取默认Pipelines
    default_pipelines = []
    if include_default:
        default_query = select(Pipeline).where(
            Pipeline.is_default == True,
            Pipeline.is_active == True
        )
        default_result = await db.execute(default_query)
        default_pipelines = default_result.scalars().all()

    return {
        "user_pipelines": user_pipelines,
        "default_pipelines": default_pipelines,
        "total": len(user_pipelines) + len(default_pipelines)
    }


@router.post("/pipelines")
async def create_pipeline(
    request: PipelineCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建Pipeline"""
    pipeline = Pipeline(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        stages_config=request.stages or []
    )

    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)

    # 创建默认Stages
    if request.stages:
        for i, stage_data in enumerate(request.stages):
            stage = PipelineStage(
                pipeline_id=pipeline.id,
                name=stage_data.get("name", f"stage_{i}"),
                display_name=stage_data.get("display_name", f"Stage {i+1}"),
                skills=stage_data.get("skills", []),
                order=i
            )
            db.add(stage)

    await db.commit()

    return pipeline


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取Pipeline详情"""
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline不存在"
        )

    # 获取Stages
    stages_result = await db.execute(
        select(PipelineStage).where(PipelineStage.pipeline_id == pipeline_id).order_by(PipelineStage.order)
    )
    stages = stages_result.scalars().all()

    return {
        "pipeline": pipeline,
        "stages": stages
    }


@router.put("/pipelines/{pipeline_id}")
async def update_pipeline(
    pipeline_id: str,
    request: PipelineUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新Pipeline"""
    result = await db.execute(
        select(Pipeline).where(
            Pipeline.id == pipeline_id,
            Pipeline.user_id == current_user.id
        )
    )
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline不存在或无权限"
        )

    if request.name is not None:
        pipeline.name = request.name
    if request.description is not None:
        pipeline.description = request.description
    if request.config is not None:
        pipeline.config = request.config
    if request.stages is not None:
        pipeline.stages_config = request.stages

    pipeline.version += 1
    await db.commit()
    await db.refresh(pipeline)

    return pipeline


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除Pipeline"""
    result = await db.execute(
        select(Pipeline).where(
            Pipeline.id == pipeline_id,
            Pipeline.user_id == current_user.id,
            Pipeline.is_default == False
        )
    )
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline不存在或为默认Pipeline"
        )

    pipeline.is_active = False
    await db.commit()

    return {"message": "Pipeline已删除"}


@router.post("/pipelines/{pipeline_id}/execute")
async def execute_pipeline(
    pipeline_id: str,
    request: PipelineExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """执行Pipeline"""
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline不存在"
        )

    # 创建执行记录
    execution = PipelineExecution(
        pipeline_id=pipeline.id,
        project_id=request.project_id,
        status="pending"
    )

    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # TODO: 启动Celery任务执行Pipeline
    # celery_task = run_pipeline_task.delay(str(execution.id))

    return {
        "execution_id": str(execution.id),
        "status": "pending"
    }


@router.get("/pipelines/{pipeline_id}/executions")
async def get_pipeline_executions(
    pipeline_id: str,
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取Pipeline执行历史"""
    result = await db.execute(
        select(PipelineExecution).where(
            PipelineExecution.pipeline_id == pipeline_id
        ).order_by(PipelineExecution.created_at.desc()).offset(skip).limit(limit)
    )
    executions = result.scalars().all()

    return {"executions": executions}

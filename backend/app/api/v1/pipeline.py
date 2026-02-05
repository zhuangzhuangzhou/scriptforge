from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from app.core.database import get_db
from app.models.user import User
from app.models.pipeline import Pipeline, PipelineStage, PipelineExecution, PipelineExecutionLog
from app.models.project import Project
from app.api.v1.auth import get_current_user
from app.tasks.pipeline_tasks import run_pipeline_task

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
    breakdown_id: Optional[str] = None


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
                description=stage_data.get("description"),
                skills=stage_data.get("skills", []),
                skills_order=stage_data.get("skills_order"),
                config=stage_data.get("config", {}),
                input_mapping=stage_data.get("input_mapping"),
                output_mapping=stage_data.get("output_mapping"),
                order=stage_data.get("order", i)
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

    if not pipeline.is_default and pipeline.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权执行此Pipeline"
        )

    if not pipeline.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline已禁用"
        )

    # 检查Pipeline阶段是否需要 batch_id / breakdown_id
    stages_result = await db.execute(
        select(PipelineStage).where(PipelineStage.pipeline_id == pipeline_id).order_by(PipelineStage.order)
    )
    stages = stages_result.scalars().all()

    # 如果没有 PipelineStage，则回退使用 stages_config
    stage_names = [s.name for s in stages]
    if not stage_names:
        stage_names = [s.get("name") for s in (pipeline.stages_config or []) if s.get("name")]

    if "breakdown" in stage_names and not request.batch_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="执行 breakdown 阶段需要 batch_id"
        )
    if "script" in stage_names and not request.batch_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="执行 script 阶段需要 batch_id"
        )
    if "script" in stage_names and "breakdown" not in stage_names and not request.breakdown_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="执行 script 阶段需要 breakdown_id"
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

    # 启动Celery任务执行Pipeline
    celery_task = run_pipeline_task.delay(
        str(execution.id),
        str(pipeline.id),
        str(request.project_id),
        str(request.batch_id) if request.batch_id else None,
        str(request.breakdown_id) if request.breakdown_id else None,
        str(current_user.id)
    )

    execution.celery_task_id = celery_task.id
    await db.commit()

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


@router.get("/pipelines/{pipeline_id}/executions/{execution_id}")
async def get_pipeline_execution(
    pipeline_id: str,
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取单次Pipeline执行详情"""
    pipeline_result = await db.execute(
        select(Pipeline).where(Pipeline.id == pipeline_id)
    )
    pipeline = pipeline_result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline不存在"
        )

    if not pipeline.is_default and pipeline.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此Pipeline"
        )

    result = await db.execute(
        select(PipelineExecution).where(
            PipelineExecution.pipeline_id == pipeline_id,
            PipelineExecution.id == execution_id
        )
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="执行记录不存在"
        )

    return {
        "id": str(execution.id),
        "pipeline_id": str(execution.pipeline_id),
        "project_id": str(execution.project_id) if execution.project_id else None,
        "status": execution.status,
        "progress": execution.progress,
        "current_stage": execution.current_stage,
        "current_step": execution.current_step,
        "result": execution.result,
        "error_message": execution.error_message,
        "celery_task_id": execution.celery_task_id,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "created_at": execution.created_at.isoformat() if execution.created_at else None
    }


@router.get("/pipelines/executions/{execution_id}")
async def get_pipeline_execution_by_id(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """按 execution_id 获取执行详情（用户维度）"""
    exec_result = await db.execute(
        select(PipelineExecution).where(PipelineExecution.id == execution_id)
    )
    execution = exec_result.scalar_one_or_none()

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="执行记录不存在"
        )

    pipeline_result = await db.execute(
        select(Pipeline).where(Pipeline.id == execution.pipeline_id)
    )
    pipeline = pipeline_result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline不存在"
        )

    if pipeline.is_default:
        if not execution.project_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此执行记录"
            )
        project_result = await db.execute(
            select(Project).where(Project.id == execution.project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project or project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此执行记录"
            )
    elif pipeline.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此执行记录"
        )

    return {
        "id": str(execution.id),
        "pipeline_id": str(execution.pipeline_id),
        "project_id": str(execution.project_id) if execution.project_id else None,
        "status": execution.status,
        "progress": execution.progress,
        "current_stage": execution.current_stage,
        "current_step": execution.current_step,
        "result": execution.result,
        "error_message": execution.error_message,
        "celery_task_id": execution.celery_task_id,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "created_at": execution.created_at.isoformat() if execution.created_at else None
    }


@router.get("/pipelines/executions/{execution_id}/logs")
async def get_pipeline_execution_logs_by_id(
    execution_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """按 execution_id 获取执行日志（用户维度）"""
    exec_result = await db.execute(
        select(PipelineExecution).where(PipelineExecution.id == execution_id)
    )
    execution = exec_result.scalar_one_or_none()

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="执行记录不存在"
        )

    pipeline_result = await db.execute(
        select(Pipeline).where(Pipeline.id == execution.pipeline_id)
    )
    pipeline = pipeline_result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline不存在"
        )

    if pipeline.is_default:
        if not execution.project_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此执行记录"
            )
        project_result = await db.execute(
            select(Project).where(Project.id == execution.project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project or project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此执行记录"
            )
    elif pipeline.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此执行记录"
        )

    result = await db.execute(
        select(PipelineExecutionLog)
        .where(PipelineExecutionLog.execution_id == execution_id)
        .order_by(PipelineExecutionLog.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "id": str(log.id),
                "execution_id": str(log.execution_id),
                "stage": log.stage,
                "event": log.event,
                "message": log.message,
                "detail": log.detail,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ],
        "skip": skip,
        "limit": limit
    }

@router.get("/pipelines/{pipeline_id}/executions/{execution_id}/logs")
async def get_pipeline_execution_logs(
    pipeline_id: str,
    execution_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取Pipeline执行日志"""
    pipeline_result = await db.execute(
        select(Pipeline).where(Pipeline.id == pipeline_id)
    )
    pipeline = pipeline_result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline不存在"
        )

    if not pipeline.is_default and pipeline.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此Pipeline"
        )

    # 校验执行记录存在
    exec_result = await db.execute(
        select(PipelineExecution).where(
            PipelineExecution.id == execution_id,
            PipelineExecution.pipeline_id == pipeline_id
        )
    )
    execution = exec_result.scalar_one_or_none()
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="执行记录不存在"
        )

    result = await db.execute(
        select(PipelineExecutionLog)
        .where(PipelineExecutionLog.execution_id == execution_id)
        .order_by(PipelineExecutionLog.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "id": str(log.id),
                "execution_id": str(log.execution_id),
                "stage": log.stage,
                "event": log.event,
                "message": log.message,
                "detail": log.detail,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ],
        "skip": skip,
        "limit": limit
    }

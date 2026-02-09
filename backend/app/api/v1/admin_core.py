from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.models.pipeline import Pipeline, PipelineExecution, PipelineExecutionLog
from app.models.project import Project

router = APIRouter()

# 在文件末尾注册模型管理子路由，避免循环导入


def check_admin(current_user: User = Depends(get_current_user)):
    """检查是否为管理员"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


class UserUpdateRequest(BaseModel):
    """更新用户请求"""
    is_active: Optional[bool] = None
    role: Optional[str] = None
    balance: Optional[float] = None
    tier: Optional[str] = None


@router.get("/users")
async def get_users(
    skip: int = 0,
    limit: int = 20,
    keyword: Optional[str] = None,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取用户列表"""
    query = select(User)

    if keyword:
        query = query.where(
            (User.username.ilike(f"%{keyword}%")) |
            (User.email.ilike(f"%{keyword}%"))
        )

    result = await db.execute(
        query.offset(skip).limit(limit)
    )
    users = result.scalars().all()

    # 获取总数
    count_query = select(func.count(User.id))
    if keyword:
        count_query = count_query.where(
            (User.username.ilike(f"%{keyword}%")) |
            (User.email.ilike(f"%{keyword}%"))
        )

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return {
        "users": users,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """更新用户状态"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    if request.is_active is not None:
        user.is_active = request.is_active
    if request.role is not None:
        user.role = request.role
    if request.balance is not None:
        user.balance = request.balance
    if request.tier is not None:
        user.tier = request.tier

    await db.commit()
    await db.refresh(user)

    return user


@router.get("/stats")
async def get_system_stats(
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取系统统计信息"""
    from app.models.project import Project
    from app.models.ai_task import AITask

    # 统计用户数
    user_count = await db.execute(select(func.count(User.id)))
    total_users = user_count.scalar()

    # 统计活跃用户数
    active_user_count = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_user_count.scalar()

    # 统计项目数
    project_count = await db.execute(select(func.count(Project.id)))
    total_projects = project_count.scalar()

    # 统计AI任务数
    task_count = await db.execute(select(func.count(AITask.id)))
    total_tasks = task_count.scalar()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_projects": total_projects,
        "total_tasks": total_tasks
    }


@router.get("/pipelines/executions")
async def get_pipeline_executions_admin(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    pipeline_id: Optional[str] = None,
    project_id: Optional[str] = None,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员：获取Pipeline执行列表"""
    query = (
        select(PipelineExecution, Pipeline, Project)
        .join(Pipeline, PipelineExecution.pipeline_id == Pipeline.id)
        .outerjoin(Project, PipelineExecution.project_id == Project.id)
    )

    if status:
        query = query.where(PipelineExecution.status == status)
    if pipeline_id:
        query = query.where(PipelineExecution.pipeline_id == pipeline_id)
    if project_id:
        query = query.where(PipelineExecution.project_id == project_id)

    count_query = select(func.count(PipelineExecution.id))
    if status:
        count_query = count_query.where(PipelineExecution.status == status)
    if pipeline_id:
        count_query = count_query.where(PipelineExecution.pipeline_id == pipeline_id)
    if project_id:
        count_query = count_query.where(PipelineExecution.project_id == project_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(
        query.order_by(PipelineExecution.created_at.desc()).offset(skip).limit(limit)
    )
    rows = result.all()

    executions = []
    for execution, pipeline, project in rows:
        executions.append({
            "id": str(execution.id),
            "pipeline_id": str(execution.pipeline_id),
            "pipeline_name": pipeline.name if pipeline else None,
            "project_id": str(execution.project_id) if execution.project_id else None,
            "project_name": project.name if project else None,
            "status": execution.status,
            "progress": execution.progress,
            "current_stage": execution.current_stage,
            "current_step": execution.current_step,
            "error_message": execution.error_message,
            "created_at": execution.created_at.isoformat() if execution.created_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None
        })

    return {
        "executions": executions,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/pipelines/executions/{execution_id}")
async def get_pipeline_execution_admin(
    execution_id: str,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员：获取单次Pipeline执行详情"""
    result = await db.execute(
        select(PipelineExecution, Pipeline, Project)
        .join(Pipeline, PipelineExecution.pipeline_id == Pipeline.id)
        .outerjoin(Project, PipelineExecution.project_id == Project.id)
        .where(PipelineExecution.id == execution_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="执行记录不存在"
        )

    execution, pipeline, project = row

    return {
        "id": str(execution.id),
        "pipeline_id": str(execution.pipeline_id),
        "pipeline_name": pipeline.name if pipeline else None,
        "project_id": str(execution.project_id) if execution.project_id else None,
        "project_name": project.name if project else None,
        "status": execution.status,
        "progress": execution.progress,
        "current_stage": execution.current_stage,
        "current_step": execution.current_step,
        "result": execution.result,
        "error_message": execution.error_message,
        "celery_task_id": execution.celery_task_id,
        "created_at": execution.created_at.isoformat() if execution.created_at else None,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None
    }


@router.get("/pipelines/executions/{execution_id}/logs")
async def get_pipeline_execution_logs_admin(
    execution_id: str,
    skip: int = 0,
    limit: int = 200,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员：获取Pipeline执行日志"""
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


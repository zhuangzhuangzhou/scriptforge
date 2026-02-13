from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.models.pipeline import Pipeline, PipelineExecution, PipelineExecutionLog
from app.models.project import Project
from app.models.ai_task import AITask
from app.models.batch import Batch

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


# ==================== 任务日志管理 API ====================

@router.get("/tasks")
async def get_tasks(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = Query(None, description="任务状态: queued, running, completed, failed"),
    task_type: Optional[str] = Query(None, description="任务类型: breakdown, script, consistency_check"),
    project_id: Optional[str] = Query(None, description="项目ID"),
    date_from: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员：获取AI任务列表"""
    query = (
        select(AITask, Project, Batch)
        .outerjoin(Project, AITask.project_id == Project.id)
        .outerjoin(Batch, AITask.batch_id == Batch.id)
    )

    # 构建筛选条件
    conditions = []
    if status:
        conditions.append(AITask.status == status)
    if task_type:
        conditions.append(AITask.task_type == task_type)
    if project_id:
        conditions.append(AITask.project_id == project_id)
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            conditions.append(AITask.created_at >= from_date)
        except ValueError:
            pass
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            conditions.append(AITask.created_at < to_date)
        except ValueError:
            pass
    if keyword:
        conditions.append(
            or_(
                AITask.current_step.ilike(f"%{keyword}%"),
                AITask.error_message.ilike(f"%{keyword}%")
            )
        )

    if conditions:
        query = query.where(and_(*conditions))

    # 统计总数
    count_conditions = conditions.copy() if conditions else []
    count_query = select(func.count(AITask.id))
    if count_conditions:
        count_query = count_query.where(and_(*count_conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 状态统计
    status_stats = {}
    for s in ["queued", "running", "completed", "failed"]:
        stat_query = select(func.count(AITask.id)).where(AITask.status == s)
        stat_result = await db.execute(stat_query)
        status_stats[s] = stat_result.scalar() or 0

    # 获取任务列表
    result = await db.execute(
        query.order_by(AITask.created_at.desc()).offset(skip).limit(limit)
    )
    rows = result.all()

    tasks = []
    for task, project, batch in rows:
        tasks.append({
            "id": str(task.id),
            "task_type": task.task_type,
            "status": task.status,
            "progress": task.progress,
            "current_step": task.current_step,
            "error_message": task.error_message,
            "retry_count": task.retry_count,
            "project_id": str(task.project_id) if task.project_id else None,
            "project_name": project.name if project else None,
            "batch_id": str(task.batch_id) if task.batch_id else None,
            "batch_name": batch.name if batch else None,
            "celery_task_id": task.celery_task_id,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        })

    return {
        "tasks": tasks,
        "total": total,
        "skip": skip,
        "limit": limit,
        "status_summary": status_stats
    }


@router.get("/tasks/{task_id}")
async def get_task_detail(
    task_id: str,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员：获取任务详情"""
    result = await db.execute(
        select(AITask, Project, Batch)
        .outerjoin(Project, AITask.project_id == Project.id)
        .outerjoin(Batch, AITask.batch_id == Batch.id)
        .where(AITask.id == task_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )

    task, project, batch = row

    # 计算执行时长
    duration = None
    if task.started_at and task.completed_at:
        duration = (task.completed_at - task.started_at).total_seconds()

    return {
        "id": str(task.id),
        "task_type": task.task_type,
        "status": task.status,
        "progress": task.progress,
        "current_step": task.current_step,
        "error_message": task.error_message,
        "retry_count": task.retry_count,
        "config": task.config,
        "result": task.result,
        "depends_on": task.depends_on,
        "project_id": str(task.project_id) if task.project_id else None,
        "project_name": project.name if project else None,
        "batch_id": str(task.batch_id) if task.batch_id else None,
        "batch_name": batch.name if batch else None,
        "celery_task_id": task.celery_task_id,
        "duration": duration,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None
    }


@router.get("/tasks/{task_id}/logs")
async def get_task_logs(
    task_id: str,
    skip: int = 0,
    limit: int = 200,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员：获取任务执行日志"""
    # 先获取任务，找到关联的 PipelineExecution
    task_result = await db.execute(
        select(AITask).where(AITask.id == task_id)
    )
    task = task_result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )

    # 通过 celery_task_id 查找 PipelineExecution
    logs = []
    total = 0

    if task.celery_task_id:
        # 查找关联的 PipelineExecution
        exec_result = await db.execute(
            select(PipelineExecution)
            .where(PipelineExecution.celery_task_id == task.celery_task_id)
        )
        execution = exec_result.scalar_one_or_none()

        if execution:
            # 获取执行日志
            log_count = await db.execute(
                select(func.count(PipelineExecutionLog.id))
                .where(PipelineExecutionLog.execution_id == execution.id)
            )
            total = log_count.scalar() or 0

            log_result = await db.execute(
                select(PipelineExecutionLog)
                .where(PipelineExecutionLog.execution_id == execution.id)
                .order_by(PipelineExecutionLog.created_at.asc())
                .offset(skip)
                .limit(limit)
            )
            log_rows = log_result.scalars().all()

            logs = [
                {
                    "id": str(log.id),
                    "stage": log.stage,
                    "event": log.event,
                    "message": log.message,
                    "detail": log.detail,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                for log in log_rows
            ]

    return {
        "task_id": str(task.id),
        "logs": logs,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/logs/stats")
async def get_logs_stats(
    period: str = Query("day", description="统计周期: day, week, month"),
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员：获取日志统计"""
    now = datetime.utcnow()

    # 根据周期确定时间范围
    if period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:  # day
        start_date = now - timedelta(days=1)

    # 总任务数
    total_query = select(func.count(AITask.id)).where(AITask.created_at >= start_date)
    total_result = await db.execute(total_query)
    total_tasks = total_result.scalar() or 0

    # 成功任务数
    success_query = select(func.count(AITask.id)).where(
        and_(AITask.created_at >= start_date, AITask.status == "completed")
    )
    success_result = await db.execute(success_query)
    success_tasks = success_result.scalar() or 0

    # 成功率
    success_rate = round(success_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0

    # 按类型统计
    type_stats = {}
    for task_type in ["breakdown", "script", "consistency_check"]:
        type_query = select(func.count(AITask.id)).where(
            and_(AITask.created_at >= start_date, AITask.task_type == task_type)
        )
        type_result = await db.execute(type_query)
        type_stats[task_type] = type_result.scalar() or 0

    # 每日趋势（最近7天）
    daily_trend = []
    for i in range(7):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_total = await db.execute(
            select(func.count(AITask.id)).where(
                and_(AITask.created_at >= day_start, AITask.created_at < day_end)
            )
        )
        day_success = await db.execute(
            select(func.count(AITask.id)).where(
                and_(
                    AITask.created_at >= day_start,
                    AITask.created_at < day_end,
                    AITask.status == "completed"
                )
            )
        )

        daily_trend.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "total": day_total.scalar() or 0,
            "success": day_success.scalar() or 0
        })

    daily_trend.reverse()

    return {
        "period": period,
        "total_tasks": total_tasks,
        "success_tasks": success_tasks,
        "success_rate": success_rate,
        "tasks_by_type": type_stats,
        "daily_trend": daily_trend
    }



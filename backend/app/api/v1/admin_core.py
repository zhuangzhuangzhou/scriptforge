from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime, timedelta, timezone
from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.models.pipeline import Pipeline, PipelineExecution, PipelineExecutionLog
from app.models.project import Project
from app.models.ai_task import AITask
from app.core.status import TaskStatus
from app.models.batch import Batch
from app.models.api_log import APILog
from app.models.llm_call_log import LLMCallLog
from app.api.v1.admin.helpers import check_admin

router = APIRouter()


# 敏感字段列表，日志中需要脱敏
SENSITIVE_FIELDS = ['password', 'token', 'secret', 'api_key', 'api_secret', 'authorization', 'cookie']


def sanitize_log_data(data: any) -> any:
    """脱敏日志数据中的敏感信息

    Args:
        data: 原始数据（字符串、字典或列表）

    Returns:
        脱敏后的数据
    """
    if data is None:
        return None

    # 如果是字符串，尝试解析为 JSON
    if isinstance(data, str):
        try:
            import json
            parsed = json.loads(data)
            sanitized = sanitize_log_data(parsed)
            return json.dumps(sanitized)
        except (json.JSONDecodeError, TypeError):
            # 不是 JSON，直接检查是否包含敏感信息
            lower_data = data.lower()
            for field in SENSITIVE_FIELDS:
                if field in lower_data:
                    return "[REDACTED - contains sensitive data]"
            return data

    # 如果是字典，递归处理
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            lower_key = key.lower()
            if any(field in lower_key for field in SENSITIVE_FIELDS):
                result[key] = "***"
            else:
                result[key] = sanitize_log_data(value)
        return result

    # 如果是列表，递归处理每个元素
    if isinstance(data, list):
        return [sanitize_log_data(item) for item in data]

    # 其他类型直接返回
    return data


def escape_like(value: str) -> str:
    """转义 LIKE 查询中的特殊字符，防止 SQL 注入"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class UserUpdateRequest(BaseModel):
    """更新用户请求"""
    model_config = {"extra": "forbid"}  # 禁止额外字段

    is_active: Optional[bool] = None
    role: Optional[Literal["admin", "user"]] = None
    credits: Optional[int] = Field(None, ge=0, description="积分余额，必须大于等于0")
    tier: Optional[Literal["FREE", "BASIC", "PRO", "ENTERPRISE"]] = None


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
        escaped_keyword = escape_like(keyword)
        query = query.where(
            (User.username.ilike(f"%{escaped_keyword}%", escape="\\")) |
            (User.email.ilike(f"%{escaped_keyword}%", escape="\\"))
        )

    result = await db.execute(
        query.offset(skip).limit(limit)
    )
    users = result.scalars().all()

    # 获取总数
    count_query = select(func.count(User.id))
    if keyword:
        escaped_keyword = escape_like(keyword)
        count_query = count_query.where(
            (User.username.ilike(f"%{escaped_keyword}%", escape="\\")) |
            (User.email.ilike(f"%{escaped_keyword}%", escape="\\"))
        )

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # 返回简化字段，隐藏敏感信息和废弃字段
    return {
        "users": [
            {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "tier": user.tier,
                "credits": user.credits,  # 使用积分余额
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
            }
            for user in users
        ],
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
    if request.credits is not None:
        user.credits = request.credits  # 使用积分替代旧算力余额
    if request.tier is not None:
        user.tier = request.tier

    await db.commit()
    await db.refresh(user)

    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "tier": user.tier,
        "credits": user.credits,
        "is_active": user.is_active
    }


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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"开始日期格式错误，应为 YYYY-MM-DD"
            )
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            conditions.append(AITask.created_at < to_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"结束日期格式错误，应为 YYYY-MM-DD"
            )
    if keyword:
        escaped_keyword = escape_like(keyword)
        conditions.append(
            or_(
                AITask.current_step.ilike(f"%{escaped_keyword}%", escape="\\"),
                AITask.error_message.ilike(f"%{escaped_keyword}%", escape="\\")
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

    # 状态统计（使用单次 GROUP BY 查询替代循环查询）
    status_query = (
        select(AITask.status, func.count(AITask.id))
        .group_by(AITask.status)
    )
    status_result = await db.execute(status_query)
    status_stats = {s: 0 for s in [TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.COMPLETED, TaskStatus.FAILED]}
    for row in status_result.all():
        if row[0] in status_stats:
            status_stats[row[0]] = row[1]

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
            "batch_number": batch.batch_number if batch else None,
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
        "batch_name": f"第 {batch.batch_number} 批次" if batch else None,
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
    now = datetime.now(timezone.utc)

    # 根据周期确定时间范围
    if period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:  # day
        start_date = now - timedelta(days=1)

    # 使用单次查询获取总数和成功数
    stats_query = select(
        func.count(AITask.id).label("total"),
        func.count(case((AITask.status == TaskStatus.COMPLETED, 1))).label("success")
    ).where(AITask.created_at >= start_date)
    stats_result = await db.execute(stats_query)
    stats_row = stats_result.first()
    total_tasks = stats_row[0] or 0
    success_tasks = stats_row[1] or 0

    # 成功率
    success_rate = round(success_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0

    # 按类型统计（使用单次 GROUP BY 查询）
    type_query = (
        select(AITask.task_type, func.count(AITask.id))
        .where(AITask.created_at >= start_date)
        .group_by(AITask.task_type)
    )
    type_result = await db.execute(type_query)
    type_stats = {"breakdown": 0, "script": 0, "consistency_check": 0}
    for row in type_result.all():
        if row[0] in type_stats:
            type_stats[row[0]] = row[1]

    # 每日趋势（使用单次查询获取7天数据）
    seven_days_ago = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_query = (
        select(
            func.date_trunc('day', AITask.created_at).label("day"),
            func.count(AITask.id).label("total"),
            func.count(case((AITask.status == TaskStatus.COMPLETED, 1))).label("success")
        )
        .where(AITask.created_at >= seven_days_ago)
        .group_by(func.date_trunc('day', AITask.created_at))
        .order_by(func.date_trunc('day', AITask.created_at))
    )
    daily_result = await db.execute(daily_query)
    daily_data = {row[0].strftime("%Y-%m-%d"): {"total": row[1], "success": row[2]} for row in daily_result.all()}

    # 填充缺失的日期
    daily_trend = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        data = daily_data.get(day, {"total": 0, "success": 0})
        daily_trend.append({
            "date": day,
            "total": data["total"],
            "success": data["success"]
        })

    return {
        "period": period,
        "total_tasks": total_tasks,
        "success_tasks": success_tasks,
        "success_rate": success_rate,
        "tasks_by_type": type_stats,
        "daily_trend": daily_trend
    }


# ==================== API 请求日志 ====================

@router.get("/api-logs")
async def get_api_logs(
    skip: int = 0,
    limit: int = 50,
    method: Optional[str] = Query(None, description="请求方法: GET, POST, PUT, DELETE"),
    path: Optional[str] = Query(None, description="请求路径（模糊匹配）"),
    status_code: Optional[int] = Query(None, description="状态码"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    date_from: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员：获取 API 请求日志"""
    query = select(APILog, User).outerjoin(User, APILog.user_id == User.id)

    # 构建筛选条件
    conditions = []
    if method:
        conditions.append(APILog.method == method.upper())
    if path:
        escaped_path = escape_like(path)
        conditions.append(APILog.path.ilike(f"%{escaped_path}%", escape="\\"))
    if status_code:
        conditions.append(APILog.status_code == status_code)
    if user_id:
        conditions.append(APILog.user_id == user_id)
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            conditions.append(APILog.created_at >= from_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="开始日期格式错误，应为 YYYY-MM-DD"
            )
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            conditions.append(APILog.created_at < to_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="结束日期格式错误，应为 YYYY-MM-DD"
            )

    if conditions:
        query = query.where(and_(*conditions))

    # 统计总数
    count_query = select(func.count(APILog.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 获取日志列表
    result = await db.execute(
        query.order_by(APILog.created_at.desc()).offset(skip).limit(limit)
    )
    rows = result.all()

    logs = []
    for log, user in rows:
        logs.append({
            "id": str(log.id),
            "method": log.method,
            "path": log.path,
            "query_params": log.query_params,
            "request_body": sanitize_log_data(getattr(log, 'request_body', None)),
            "user_id": str(log.user_id) if log.user_id else None,
            "username": user.username if user else None,
            "user_ip": log.user_ip,
            "user_agent": log.user_agent,
            "status_code": log.status_code,
            "response_body": sanitize_log_data(getattr(log, 'response_body', None)),
            "response_time": log.response_time,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat() if log.created_at else None
        })

    return {
        "logs": logs,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/api-logs/stats")
async def get_api_logs_stats(
    period: str = Query("day", description="统计周期: day, week, month"),
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员：获取 API 请求统计"""
    now = datetime.now(timezone.utc)

    # 根据周期确定时间范围
    if period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:  # day
        start_date = now - timedelta(days=1)

    # 使用单次查询获取所有统计数据
    stats_query = select(
        func.count(APILog.id).label("total"),
        func.count(case((and_(APILog.status_code >= 200, APILog.status_code < 300), 1))).label("success"),
        func.count(case((APILog.status_code >= 400, 1))).label("error"),
        func.avg(APILog.response_time).label("avg_time")
    ).where(APILog.created_at >= start_date)
    stats_result = await db.execute(stats_query)
    stats_row = stats_result.first()
    total_requests = stats_row[0] or 0
    success_requests = stats_row[1] or 0
    error_requests = stats_row[2] or 0
    avg_response_time = round(stats_row[3] or 0, 1)

    # 按方法统计（使用单次 GROUP BY 查询）
    method_query = (
        select(APILog.method, func.count(APILog.id))
        .where(APILog.created_at >= start_date)
        .group_by(APILog.method)
    )
    method_result = await db.execute(method_query)
    method_stats = {"GET": 0, "POST": 0, "PUT": 0, "DELETE": 0}
    for row in method_result.all():
        if row[0] in method_stats:
            method_stats[row[0]] = row[1]

    # 热门路径 Top 10
    top_paths_query = (
        select(APILog.path, func.count(APILog.id).label("count"))
        .where(APILog.created_at >= start_date)
        .group_by(APILog.path)
        .order_by(func.count(APILog.id).desc())
        .limit(10)
    )
    top_paths_result = await db.execute(top_paths_query)
    top_paths = [{"path": row[0], "count": row[1]} for row in top_paths_result.all()]

    return {
        "period": period,
        "total_requests": total_requests,
        "success_requests": success_requests,
        "error_requests": error_requests,
        "avg_response_time": avg_response_time,
        "requests_by_method": method_stats,
        "top_paths": top_paths
    }


# ==================== LLM 调用日志 ====================

@router.get("/llm-logs")
async def get_llm_logs(
    skip: int = 0,
    limit: int = 50,
    provider: Optional[str] = Query(None, description="提供商: openai, anthropic"),
    model_name: Optional[str] = Query(None, description="模型名称"),
    skill_name: Optional[str] = Query(None, description="Skill 名称"),
    task_id: Optional[str] = Query(None, description="任务ID"),
    status: Optional[str] = Query(None, description="状态: success, error"),
    date_from: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员：获取 LLM 调用日志"""
    query = select(LLMCallLog, User).outerjoin(User, LLMCallLog.user_id == User.id)

    # 构建筛选条件
    conditions = []
    if provider:
        conditions.append(LLMCallLog.provider == provider)
    if model_name:
        escaped_model = escape_like(model_name)
        conditions.append(LLMCallLog.model_name.ilike(f"%{escaped_model}%", escape="\\"))
    if skill_name:
        escaped_skill = escape_like(skill_name)
        conditions.append(LLMCallLog.skill_name.ilike(f"%{escaped_skill}%", escape="\\"))
    if task_id:
        conditions.append(LLMCallLog.task_id == task_id)
    if status:
        conditions.append(LLMCallLog.status == status)
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            conditions.append(LLMCallLog.created_at >= from_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="开始日期格式错误，应为 YYYY-MM-DD"
            )
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            conditions.append(LLMCallLog.created_at < to_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="结束日期格式错误，应为 YYYY-MM-DD"
            )

    if conditions:
        query = query.where(and_(*conditions))

    # 统计总数
    count_query = select(func.count(LLMCallLog.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 获取日志列表
    result = await db.execute(
        query.order_by(LLMCallLog.created_at.desc()).offset(skip).limit(limit)
    )
    rows = result.all()

    logs = []
    for log, user in rows:
        # 从 extra_metadata.request 中提取 prompt_preview
        request_data = log.extra_metadata.get("request") if log.extra_metadata else None
        if request_data:
            # 提取最后一条 user 消息作为 preview
            messages = request_data.get("messages", [])
            user_messages = [m.get("content", "") for m in messages if m.get("role") == "user"]
            prompt_preview = user_messages[-1] if user_messages else ""
        else:
            prompt_preview = ""

        logs.append({
            "id": str(log.id),
            "task_id": str(log.task_id) if log.task_id else None,
            "user_id": str(log.user_id) if log.user_id else None,
            "username": user.username if user else None,
            "provider": log.provider,
            "model_name": log.model_name,
            "skill_name": log.skill_name,
            "stage": log.stage,
            "prompt_preview": prompt_preview[:200] + "..." if len(prompt_preview) > 200 else prompt_preview,
            "response_preview": log.response[:200] + "..." if log.response and len(log.response) > 200 else log.response,
            "prompt_tokens": log.prompt_tokens,
            "response_tokens": log.response_tokens,
            "total_tokens": log.total_tokens,
            "latency_ms": log.latency_ms,
            "status": log.status,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat() if log.created_at else None
        })

    return {
        "logs": logs,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/llm-logs/{log_id}")
async def get_llm_log_detail(
    log_id: str,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员：获取 LLM 调用详情（包含完整 prompt 和 response）"""
    result = await db.execute(
        select(LLMCallLog, User)
        .outerjoin(User, LLMCallLog.user_id == User.id)
        .where(LLMCallLog.id == log_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="日志不存在"
        )

    log, user = row

    # LLM 日志的 metadata 包含 request/response，不需要脱敏
    # 因为这是管理员查看的日志，记录的是发送给 LLM 的内容，不是系统敏感信息

    return {
        "id": str(log.id),
        "task_id": str(log.task_id) if log.task_id else None,
        "user_id": str(log.user_id) if log.user_id else None,
        "username": user.username if user else None,
        "project_id": str(log.project_id) if log.project_id else None,
        "provider": log.provider,
        "model_name": log.model_name,
        "skill_name": log.skill_name,
        "stage": log.stage,
        # prompt 字段已废弃，数据存储在 metadata.request 中
        "response": log.response,
        "prompt_tokens": log.prompt_tokens,
        "response_tokens": log.response_tokens,
        "total_tokens": log.total_tokens,
        "temperature": log.temperature,
        "max_tokens": log.max_tokens,
        "latency_ms": log.latency_ms,
        "status": log.status,
        "error_message": log.error_message,
        "metadata": log.extra_metadata,  # 返回原始 metadata，包含完整 request
        "created_at": log.created_at.isoformat() if log.created_at else None
    }


@router.get("/llm-logs/stats/summary")
async def get_llm_logs_stats(
    period: str = Query("day", description="统计周期: day, week, month"),
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员：获取 LLM 调用统计"""
    now = datetime.now(timezone.utc)

    # 根据周期确定时间范围
    if period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:  # day
        start_date = now - timedelta(days=1)

    # 使用单次查询获取所有统计数据
    stats_query = select(
        func.count(LLMCallLog.id).label("total"),
        func.count(case((LLMCallLog.status == "success", 1))).label("success"),
        func.sum(LLMCallLog.total_tokens).label("tokens"),
        func.avg(LLMCallLog.latency_ms).label("avg_latency")
    ).where(LLMCallLog.created_at >= start_date)
    stats_result = await db.execute(stats_query)
    stats_row = stats_result.first()
    total_calls = stats_row[0] or 0
    success_calls = stats_row[1] or 0
    total_tokens = stats_row[2] or 0
    avg_latency = round(stats_row[3] or 0, 1)

    # 按提供商统计（使用单次 GROUP BY 查询）
    provider_query = (
        select(LLMCallLog.provider, func.count(LLMCallLog.id))
        .where(LLMCallLog.created_at >= start_date)
        .group_by(LLMCallLog.provider)
    )
    provider_result = await db.execute(provider_query)
    provider_stats = {"openai": 0, "anthropic": 0, "gemini": 0}
    for row in provider_result.all():
        if row[0] in provider_stats:
            provider_stats[row[0]] = row[1]

    # 按模型统计 Top 5
    model_stats_query = (
        select(LLMCallLog.model_name, func.count(LLMCallLog.id).label("count"))
        .where(LLMCallLog.created_at >= start_date)
        .group_by(LLMCallLog.model_name)
        .order_by(func.count(LLMCallLog.id).desc())
        .limit(5)
    )
    model_stats_result = await db.execute(model_stats_query)
    top_models = [{"model": row[0], "count": row[1]} for row in model_stats_result.all()]

    # 按 Skill 统计 Top 5
    skill_stats_query = (
        select(LLMCallLog.skill_name, func.count(LLMCallLog.id).label("count"))
        .where(and_(LLMCallLog.created_at >= start_date, LLMCallLog.skill_name.isnot(None)))
        .group_by(LLMCallLog.skill_name)
        .order_by(func.count(LLMCallLog.id).desc())
        .limit(5)
    )
    skill_stats_result = await db.execute(skill_stats_query)
    top_skills = [{"skill": row[0], "count": row[1]} for row in skill_stats_result.all()]

    return {
        "period": period,
        "total_calls": total_calls,
        "success_calls": success_calls,
        "error_calls": total_calls - success_calls,
        "total_tokens": total_tokens,
        "avg_latency_ms": avg_latency,
        "calls_by_provider": provider_stats,
        "top_models": top_models,
        "top_skills": top_skills
    }

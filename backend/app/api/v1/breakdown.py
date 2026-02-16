from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from app.core.database import get_db
from app.models.user import User
from app.models.batch import Batch
from app.models.project import Project
from app.models.ai_task import AITask
from app.models.ai_resource import AIResource
from app.api.v1.auth import get_current_user
from app.core.celery_app import celery_app
from app.tasks.breakdown_tasks import run_breakdown_task
from app.core.quota import QuotaService, refund_episode_quota_sync
from app.core.status import normalize_task_status, TaskStatus, BatchStatus

router = APIRouter()


_normalize_task_status = normalize_task_status


class BreakdownStartRequest(BaseModel):
    """启动拆解请求"""
    batch_id: str
    # model_config_id 不再需要，从项目配置读取
    selected_skills: Optional[List[str]] = None
    pipeline_id: Optional[str] = None
    # 小说类型（用于加载类型专属文档）
    novel_type: Optional[str] = None
    # 新版：资源 ID 列表（支持多选）
    resource_ids: Optional[List[str]] = None
    # 旧版：单个资源 ID（保留兼容）
    adapt_method_id: Optional[str] = None
    output_style_id: Optional[str] = None
    template_id: Optional[str] = None
    example_id: Optional[str] = None
    # 旧配置 key（已废弃，保留兼容）
    adapt_method_key: Optional[str] = None
    quality_rule_key: Optional[str] = None
    output_style_key: Optional[str] = None
    # 执行模式：agent_loop(Agent全量循环), agent_single(Agent单轮+Skill修正), skill_only(纯Skill)
    execution_mode: Optional[str] = Field(
        default="agent_single",
        pattern="^(agent_loop|agent_single|skill_only)$",
        description="执行模式: agent_loop(Agent全量循环), agent_single(Agent单轮+Skill修正), skill_only(纯Skill)"
    )


class BatchStartRequest(BaseModel):
    """批量启动拆解请求"""
    project_id: str
    # 新版：资源 ID 列表（支持多选）
    resource_ids: Optional[List[str]] = None
    # 旧版：单个资源 ID（保留兼容）
    adapt_method_id: Optional[str] = None
    output_style_id: Optional[str] = None
    template_id: Optional[str] = None
    # 旧配置 key（已废弃，保留兼容）
    adapt_method_key: Optional[str] = "adapt_method_default"
    quality_rule_key: Optional[str] = "qa_breakdown_default"
    output_style_key: Optional[str] = "output_style_default"
    # 并发控制
    concurrent_limit: Optional[int] = Field(default=3, ge=1, le=10)


class TaskRetryRequest(BaseModel):
    """任务重试请求"""
    new_config: Optional[dict] = None


class PlotPointStatusUpdate(BaseModel):
    """剧情点状态更新请求"""
    status: str = Field(..., pattern="^(used|unused)$")


@router.post("/start")
async def start_breakdown(
    request: BreakdownStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """启动剧情拆解

    优化：
    - 配额在任务成功启动后才消耗
    - 使用事务保证数据一致性
    - 防止重复提交
    - 更新批次状态
    """
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
            detail="批次不存在或无权访问"
        )
    
    # 获取项目配置（包含模型 ID）
    project_result = await db.execute(
        select(Project).where(Project.id == batch.project_id)
    )
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )
    
    # 检查项目是否配置了拆解模型
    if not project.breakdown_model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="项目未配置剧情拆解模型，请先在项目设置中选择模型"
        )

    # 检查是否已有任务在执行（防止重复提交）
    # 移除 CANCELLING，因为取消中的任务可能永远不会结束（Celery回调卡住）
    # 我们会在下面单独处理 CANCELLING 状态的任务
    active_statuses = [TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.RETRYING, TaskStatus.IN_PROGRESS]
    existing_task_result = await db.execute(
        select(AITask).where(
            AITask.batch_id == request.batch_id,
            AITask.status.in_(active_statuses)
        )
    )
    existing_task = existing_task_result.scalar_one_or_none()

    if existing_task:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"该批次已有任务在执行中，任务ID: {existing_task.id}"
        )

    # 检查是否有取消中的任务（CANCELLING），这些任务可能永远不会结束
    # 需要自动清理超时的取消任务
    cancelling_task_result = await db.execute(
        select(AITask).where(
            AITask.batch_id == request.batch_id,
            AITask.status == TaskStatus.CANCELLING
        )
    )
    cancelling_task = cancelling_task_result.scalar_one_or_none()

    if cancelling_task:
        # 检查取消任务是否超时（超过30分钟视为僵尸任务）
        CANCELLING_TIMEOUT = timedelta(minutes=30)
        now = datetime.now(timezone.utc)
        task_age = now - cancelling_task.updated_at

        if task_age > CANCELLING_TIMEOUT:
            # 超时的取消任务，自动标记为已取消
            print(f"检测到超时的取消任务 {cancelling_task.id}（已存在 {task_age}），自动清理")
            cancelling_task.status = TaskStatus.CANCELLED
            cancelling_task.error_message = "任务取消超时，自动标记为已取消"
            # 同时更新批次状态为 pending
            batch.breakdown_status = BatchStatus.PENDING
            await db.flush()
            print(f"已将任务 {cancelling_task.id} 标记为 cancelled，批次状态更新为 pending")
        else:
            # 取消中的任务还未超时，提示用户
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"该批次有任务正在取消中，请稍候再试（已等待 {task_age.seconds // 60} 分钟）"
            )
    
    # 如果批次状态是 failed，允许重新提交（清理旧的失败任务记录）
    if batch.breakdown_status == BatchStatus.FAILED:
        # 查找失败的任务记录
        failed_task_result = await db.execute(
            select(AITask).where(
                AITask.batch_id == request.batch_id,
                AITask.status == TaskStatus.FAILED
            )
        )
        failed_tasks = failed_task_result.scalars().all()
        # 注意：不删除失败任务记录，保留用于历史追溯
        # 只是允许创建新任务

    # 锁定用户记录，防止并发请求导致积分超支
    user_result = await db.execute(
        select(User).where(User.id == current_user.id).with_for_update()
    )
    locked_user = user_result.scalar_one()

    # 检查积分（纯积分制）
    quota_service = QuotaService(db)
    credits_check = await quota_service.check_credits(locked_user, "breakdown")
    if not credits_check["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"积分不足: 需要 {credits_check['cost']}，余额 {credits_check['balance']}"
        )

    # 消耗积分（预扣）
    await quota_service.consume_credits(locked_user, "breakdown", "剧情拆解")

    # 构建任务配置
    task_config = {
        "model_config_id": str(project.breakdown_model_id),  # 从项目配置读取
        "selected_skills": request.selected_skills or [],
        "pipeline_id": request.pipeline_id,
        "execution_mode": request.execution_mode or "agent_single",  # 执行模式
    }

    # 添加小说类型（优先使用请求参数，否则从项目配置读取）
    novel_type = request.novel_type or project.novel_type
    if novel_type:
        task_config["novel_type"] = novel_type

    # 新版：资源 ID 列表（优先使用）
    if request.resource_ids:
        task_config["resource_ids"] = request.resource_ids

    # 旧版：单个资源 ID（保留兼容）
    if request.adapt_method_id:
        task_config["adapt_method_id"] = request.adapt_method_id
    if request.output_style_id:
        task_config["output_style_id"] = request.output_style_id
    if request.template_id:
        task_config["template_id"] = request.template_id
    if request.example_id:
        task_config["example_id"] = request.example_id

    # 兼容旧配置 key
    if request.adapt_method_key:
        task_config["adapt_method_key"] = request.adapt_method_key
    if request.quality_rule_key:
        task_config["quality_rule_key"] = request.quality_rule_key
    if request.output_style_key:
        task_config["output_style_key"] = request.output_style_key

    # 创建AI任务
    task = AITask(
        project_id=batch.project_id,
        batch_id=batch.id,
        task_type="breakdown",
        status=TaskStatus.QUEUED,
        depends_on=[],
        config=task_config
    )
    db.add(task)
    await db.flush()  # 获取 task.id

    # 启动Celery异步任务
    try:
        celery_task = run_breakdown_task.delay(
            str(task.id),
            str(batch.id),
            str(batch.project_id),
            str(current_user.id)
        )
        
        # 更新任务的celery_task_id
        task.celery_task_id = celery_task.id
        
    except Exception as celery_error:
        # Celery 连接失败，回滚配额和任务
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"任务队列服务不可用，请稍后重试"
        )

    # 更新批次状态
    batch.breakdown_status = BatchStatus.QUEUED
    
    # 提交事务
    await db.commit()
    await db.refresh(task)

    return {"task_id": str(task.id), "status": TaskStatus.QUEUED}


@router.get("/batch/{batch_id}/current-task")
async def get_batch_current_task(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取批次当前正在执行的任务 ID

    用于页面加载时自动连接正在处理的任务。
    """
    # 验证批次归属
    batch_result = await db.execute(
        select(Batch).join(Project).where(
            Batch.id == batch_id,
            Project.user_id == current_user.id
        )
    )
    batch = batch_result.scalar_one_or_none()

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="批次不存在"
        )

    # 查询正在执行的任务（任务级状态）
    task_result = await db.execute(
        select(AITask).where(
            AITask.batch_id == batch_id,
            AITask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.IN_PROGRESS, TaskStatus.RETRYING, TaskStatus.CANCELLING])
        ).order_by(AITask.created_at.desc()).limit(1)
    )
    task = task_result.scalar_one_or_none()

    if not task:
        return {"task_id": None, "status": batch.breakdown_status}

    return {
        "task_id": str(task.id),
        "status": _normalize_task_status(task.status),
        "progress": task.progress,
        "current_step": task.current_step
    }


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

    # 解析并人性化错误信息
    error_display = None
    if task.error_message:
        error_display = _humanize_error_message(task.error_message)

    return {
        "task_id": str(task.id),
        "status": _normalize_task_status(task.status),
        "progress": task.progress,
        "current_step": task.current_step,
        "error_message": task.error_message,  # 保留原始错误信息
        "error_display": error_display,  # 人性化错误信息
        "retry_count": task.retry_count,
        "depends_on": task.depends_on or []
    }


def _humanize_error_message(error_message: str) -> dict:
    """将技术错误信息转换为用户友好的提示

    Args:
        error_message: 原始错误信息（JSON字符串或普通字符串）

    Returns:
        包含人性化错误信息的字典
    """
    import json
    import re
    from datetime import datetime

    # 尝试解析JSON格式的错误信息
    try:
        if error_message.startswith('{'):
            error_data = json.loads(error_message)
        else:
            error_data = {"message": error_message}
    except:
        error_data = {"message": error_message}
    
    code = error_data.get("code", "UNKNOWN_ERROR")
    message = error_data.get("message", "")
    
    # 定义错误类型和对应的人性化提示
    error_patterns = {
        "greenlet_spawn": {
            "title": "系统配置问题",
            "description": "后台任务执行环境配置异常，这是一个技术问题。",
            "suggestion": "请联系技术支持或稍后重试。我们正在修复这个问题。",
            "icon": "⚙️",
            "severity": "error"
        },
        "QUOTA_EXCEEDED": {
            "title": "配额不足",
            "description": "您的剧集配额已用完。",
            "suggestion": "请升级套餐或等待下月配额重置。",
            "icon": "📊",
            "severity": "warning"
        },
        "MODEL_ERROR": {
            "title": "AI模型错误",
            "description": "AI模型处理时出现问题。",
            "suggestion": "请检查模型配置或稍后重试。",
            "icon": "🤖",
            "severity": "error"
        },
        "NETWORK_ERROR": {
            "title": "网络连接问题",
            "description": "无法连接到AI服务。",
            "suggestion": "请检查网络连接或稍后重试。",
            "icon": "🌐",
            "severity": "warning"
        },
        "TIMEOUT": {
            "title": "处理超时",
            "description": "任务处理时间过长。",
            "suggestion": "请尝试减少章节数量或稍后重试。",
            "icon": "⏱️",
            "severity": "warning"
        },
        "PERMISSION_DENIED": {
            "title": "权限不足",
            "description": "您没有权限执行此操作。",
            "suggestion": "请检查您的账户权限。",
            "icon": "🔒",
            "severity": "error"
        },
        "DATA_NOT_FOUND": {
            "title": "数据不存在",
            "description": "找不到相关的批次或章节数据。",
            "suggestion": "请确认数据已正确上传。",
            "icon": "📁",
            "severity": "error"
        },
        "NO_CREDENTIAL": {
            "title": "模型凭证缺失",
            "description": "没有找到有效的 API 凭证配置。",
            "suggestion": "请在模型配置中添加工 API Key。",
            "icon": "🔑",
            "severity": "error"
        },
        "CREDENTIAL_INVALID": {
            "title": "凭证无效",
            "description": "提供的 API 凭证无效或已过期。",
            "suggestion": "请更新模型的 API Key 配置。",
            "icon": "🔐",
            "severity": "error"
        }
    }
    
    # 匹配错误类型
    matched_error = None
    for pattern, error_info in error_patterns.items():
        if pattern in code:
            matched_error = error_info
            break
        if pattern.lower() in message.lower():
            matched_error = error_info
            break

    # 特殊处理：检测"凭证"相关错误（即使 code 不包含这些关键词）
    if not matched_error:
        if "没有可用的凭证" in message or "no available credential" in message.lower():
            matched_error = error_patterns["NO_CREDENTIAL"]
            # 从消息中提取模型名称
            model_match = re.search(r':\s*(\S+)$', message)
            if model_match:
                model_name = model_match.group(1)
                matched_error = {
                    **matched_error,
                    "description": f"模型 {model_name} 没有可用的 API 凭证"
                }
        elif "凭证无效" in message or "credential" in message.lower():
            matched_error = error_patterns.get("CREDENTIAL_INVALID", error_patterns["MODEL_ERROR"])
        elif "api" in message.lower() and ("key" in message.lower() or "无效" in message or "expired" in message.lower()):
            matched_error = error_patterns["CREDENTIAL_INVALID"]
    
    # 如果没有匹配到，使用默认错误信息
    if not matched_error:
        # 检查是否是SQLAlchemy相关错误
        if "sqlalchemy" in message.lower() or "greenlet" in message.lower():
            matched_error = error_patterns["greenlet_spawn"]
        else:
            matched_error = {
                "title": "任务执行失败",
                "description": "处理过程中遇到了问题。",
                "suggestion": "请稍后重试，如果问题持续存在，请联系技术支持。",
                "icon": "❌",
                "severity": "error"
            }
    
    # 提取失败时间
    failed_at = error_data.get("failed_at", "")
    if failed_at:
        try:
            dt = datetime.fromisoformat(failed_at.replace('Z', '+00:00'))
            failed_at_display = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            failed_at_display = failed_at
    else:
        failed_at_display = None
    
    return {
        "title": matched_error["title"],
        "description": matched_error["description"],
        "suggestion": matched_error["suggestion"],
        "icon": matched_error["icon"],
        "severity": matched_error["severity"],
        "failed_at": failed_at_display,
        "retry_count": error_data.get("retry_count", 0),
        "code": code,
        "original_message": message,
        "technical_details": message if len(message) < 300 else message[:300] + "..."
    }


@router.get("/tasks/{task_id}/logs")
async def get_task_execution_logs(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取任务执行日志（包括 LLM 调用详情）

    返回：
    - execution_logs: Pipeline 执行日志列表
    - llm_calls: LLM 调用统计
    - timeline: 时间线视图
    """
    # 验证任务归属
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

    # 查询 Pipeline 执行记录
    from app.models.pipeline import PipelineExecution, PipelineExecutionLog

    # 通过 project_id 查询最近的 Pipeline 执行记录
    exec_result = await db.execute(
        select(PipelineExecution).where(
            PipelineExecution.project_id == task.project_id
        ).order_by(PipelineExecution.created_at.desc()).limit(1)
    )
    execution = exec_result.scalar_one_or_none()

    if not execution:
        return {
            "task_id": task_id,
            "execution_logs": [],
            "llm_calls": {
                "total": 0,
                "stages": []
            },
            "timeline": []
        }

    # 查询执行日志
    logs_result = await db.execute(
        select(PipelineExecutionLog).where(
            PipelineExecutionLog.execution_id == execution.id
        ).order_by(PipelineExecutionLog.created_at)
    )
    logs = logs_result.scalars().all()

    # 解析 LLM 调用信息
    llm_calls = {
        "total": 0,
        "stages": []
    }

    timeline = []
    for log in logs:
        timeline.append({
            "timestamp": log.created_at.isoformat() if log.created_at else None,
            "stage": log.stage,
            "event": log.event,
            "message": log.message,
            "detail": log.detail
        })

        # 统计 LLM 调用（validator_result 事件表示 LLM 调用）
        if log.event == "validator_result" and log.detail:
            llm_calls["total"] += 1
            stage_info = {
                "stage": log.stage,
                "validator": log.detail.get("validator_name") if isinstance(log.detail, dict) else None,
                "status": log.detail.get("status") if isinstance(log.detail, dict) else None,
                "score": log.detail.get("score") if isinstance(log.detail, dict) else None,
                "timestamp": log.created_at.isoformat() if log.created_at else None
            }
            llm_calls["stages"].append(stage_info)

    return {
        "task_id": task_id,
        "execution_id": str(execution.id),
        "execution_logs": timeline,
        "llm_calls": llm_calls,
        "timeline": timeline
    }


@router.post("/start-all")
async def start_all_breakdowns(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量启动所有未拆解批次

    优化：
    - 配额在所有任务成功启动后才消耗
    - 使用事务保证原子性
    - 防止重复提交
    - 更新批次状态
    - 校验批次连续性（防止跳集拆解）
    """
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
            detail="项目不存在或无权访问"
        )

    # 检查项目是否配置了拆解模型
    if not project.breakdown_model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="项目未配置剧情拆解模型，请先在项目设置中选择模型"
        )

    # 获取所有 pending 状态的批次
    pending_batches = await db.execute(
        select(Batch).where(
            Batch.project_id == project_id,
            Batch.breakdown_status == BatchStatus.PENDING
        ).order_by(Batch.batch_number)
    )
    batches = pending_batches.scalars().all()

    if not batches:
        return {"task_ids": [], "total": 0, "message": "没有待拆解的批次"}

    # 校验第一个批次与上一批次的连续性
    first_batch = batches[0]
    prev_batch_result = await db.execute(
        select(Batch).where(
            Batch.project_id == project_id,
            Batch.batch_number < first_batch.batch_number
        ).order_by(Batch.batch_number.desc()).limit(1)
    )
    prev_batch = prev_batch_result.scalar_one_or_none()

    if prev_batch and prev_batch.breakdown_status != BatchStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"上一批次（第{prev_batch.batch_number}集）尚未完成拆解，无法批量拆解"
        )

    # 检查每个批次是否已有任务在执行
    batch_ids = [batch.id for batch in batches]
    existing_tasks_result = await db.execute(
        select(AITask).where(
            AITask.batch_id.in_(batch_ids),
            AITask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.RETRYING, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLING])
        )
    )
    existing_tasks = existing_tasks_result.scalars().all()

    if existing_tasks:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"部分批次已有任务在执行中，任务数: {len(existing_tasks)}"
        )

    # 锁定用户记录
    user_result = await db.execute(
        select(User).where(User.id == current_user.id).with_for_update()
    )
    locked_user = user_result.scalar_one()

    # 检查积分（纯积分制）
    quota_service = QuotaService(db)
    required_credits = len(batches) * 100  # breakdown 每次 100 积分
    credits_check = await quota_service.check_credits(locked_user, "breakdown")

    if not credits_check["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"积分不足: 需要 {credits_check['cost']}，余额 {credits_check['balance']}"
        )

    # 检查积分是否足够批量任务
    if credits_check["balance"] < required_credits:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"积分不足: 需要 {required_credits}，余额 {credits_check['balance']}"
        )

    task_ids = []
    failed_batches = []

    for batch in batches:
        try:
            # 消耗积分（预扣）
            await quota_service.consume_credits(locked_user, "breakdown", "剧情拆解")

            # 创建AI任务
            task = AITask(
                project_id=batch.project_id,
                batch_id=batch.id,
                task_type="breakdown",
                status=TaskStatus.QUEUED,
                depends_on=[],
                config={
                    "model_config_id": str(project.breakdown_model_id),  # 从项目配置读取
                    "adapt_method_key": "adapt_method_default",
                    "quality_rule_key": "qa_breakdown_default",
                    "output_style_key": "output_style_default"
                }
            )
            db.add(task)
            await db.flush()  # 获取 task.id

            # 启动Celery异步任务
            try:
                celery_task = run_breakdown_task.delay(
                    str(task.id),
                    str(batch.id),
                    str(batch.project_id),
                    str(current_user.id)
                )
                task.celery_task_id = celery_task.id
            except Exception as celery_error:
                # Celery 提交失败，标记任务为失败
                import json
                task.status = TaskStatus.FAILED
                task.error_message = json.dumps({
                    "code": "CELERY_UNAVAILABLE",
                    "message": "任务队列服务不可用，请稍后重试",
                    "failed_at": datetime.utcnow().isoformat(),
                    "retry_count": 0
                })
                batch.breakdown_status = BatchStatus.FAILED
                failed_batches.append(str(batch.id))
                continue

            # 更新批次状态
            batch.breakdown_status = BatchStatus.QUEUED
            task_ids.append(str(task.id))

        except Exception:
            # 单个批次处理失败
            failed_batches.append(str(batch.id))
            continue

    # 提交事务
    await db.commit()

    if failed_batches:
        return {
            "task_ids": task_ids,
            "total": len(task_ids),
            "failed": len(failed_batches),
            "message": f"成功启动 {len(task_ids)} 个任务，{len(failed_batches)} 个失败"
        }

    return {"task_ids": task_ids, "total": len(task_ids)}


@router.post("/continue/{project_id}")
async def start_continue_breakdown(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """继续拆解：从第一个 pending 批次开始

    优化：
    - 配额在任务成功启动后才消耗
    - 使用事务保证数据一致性
    - 防止重复提交
    - 更新批次状态
    - 校验上一批次是否已完成（防止跳集拆解）
    """
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
            detail="项目不存在或无权访问"
        )

    # 检查项目是否配置了拆解模型
    if not project.breakdown_model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="项目未配置剧情拆解模型，请先在项目设置中选择模型"
        )

    # 获取第一个 pending 状态的批次
    pending_batch = await db.execute(
        select(Batch).where(
            Batch.project_id == project_id,
            Batch.breakdown_status == BatchStatus.PENDING
        ).order_by(Batch.batch_number).limit(1)
    )
    batch = pending_batch.scalar_one_or_none()

    if not batch:
        return {"task_id": None, "batch_id": None, "message": "没有待拆解的批次"}

    # 校验上一批次是否已完成（防止跳集拆解）
    prev_batch_result = await db.execute(
        select(Batch).where(
            Batch.project_id == project_id,
            Batch.batch_number < batch.batch_number
        ).order_by(Batch.batch_number.desc()).limit(1)
    )
    prev_batch = prev_batch_result.scalar_one_or_none()

    if prev_batch and prev_batch.breakdown_status != BatchStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"上一批次（第{prev_batch.batch_number}集）尚未完成拆解，请先完成后再继续"
        )

    # 检查是否已有任务在执行（防止重复提交）
    # 移除 CANCELLING，因为取消中的任务可能永远不会结束
    active_statuses = [TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.RETRYING, TaskStatus.IN_PROGRESS]
    existing_task_result = await db.execute(
        select(AITask).where(
            AITask.batch_id == batch.id,
            AITask.status.in_(active_statuses)
        )
    )
    existing_task = existing_task_result.scalar_one_or_none()

    if existing_task:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"该批次已有任务在执行中，任务ID: {existing_task.id}"
        )

    # 检查是否有取消中的任务（CANCELLING）
    cancelling_task_result = await db.execute(
        select(AITask).where(
            AITask.batch_id == batch.id,
            AITask.status == TaskStatus.CANCELLING
        )
    )
    cancelling_task = cancelling_task_result.scalar_one_or_none()

    if cancelling_task:
        # 检查取消任务是否超时（超过30分钟视为僵尸任务）
        CANCELLING_TIMEOUT = timedelta(minutes=30)
        now = datetime.now(timezone.utc)
        task_age = now - cancelling_task.updated_at

        if task_age > CANCELLING_TIMEOUT:
            # 超时的取消任务，自动标记为已取消
            print(f"[continue_all] 检测到超时的取消任务 {cancelling_task.id}，自动清理")
            cancelling_task.status = TaskStatus.CANCELLED
            cancelling_task.error_message = "任务取消超时，自动标记为已取消"
            batch.breakdown_status = BatchStatus.PENDING
            await db.flush()
        else:
            # 取消中的任务还未超时
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"该批次有任务正在取消中，请稍候再试"
            )

    # 如果批次状态是 failed，允许重新提交
    if batch.breakdown_status == BatchStatus.FAILED:
        # 允许创建新任务，不删除失败任务记录（保留历史）
        pass

    # 锁定用户记录
    user_result = await db.execute(
        select(User).where(User.id == current_user.id).with_for_update()
    )
    locked_user = user_result.scalar_one()

    # 检查积分（纯积分制）
    quota_service = QuotaService(db)
    credits_check = await quota_service.check_credits(locked_user, "breakdown")
    if not credits_check["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"积分不足: 需要 {credits_check['cost']}，余额 {credits_check['balance']}"
        )

    # 消耗积分（预扣）
    await quota_service.consume_credits(locked_user, "breakdown", "剧情拆解")

    # 创建AI任务
    task = AITask(
        project_id=batch.project_id,
        batch_id=batch.id,
        task_type="breakdown",
        status=TaskStatus.QUEUED,
        depends_on=[],
        config={
            "model_config_id": str(project.breakdown_model_id),  # 从项目配置读取
            "adapt_method_key": "adapt_method_default",
            "quality_rule_key": "qa_breakdown_default",
            "output_style_key": "output_style_default"
        }
    )
    db.add(task)
    await db.flush()  # 获取 task.id

    # 启动Celery异步任务
    try:
        celery_task = run_breakdown_task.delay(
            str(task.id),
            str(batch.id),
            str(batch.project_id),
            str(current_user.id)
        )
        task.celery_task_id = celery_task.id
    except Exception:
        # Celery 连接失败，回滚配额和任务
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="任务队列服务不可用，请稍后重试"
        )

    # 更新批次状态
    batch.breakdown_status = BatchStatus.QUEUED

    # 提交事务
    await db.commit()
    await db.refresh(task)

    return {"task_id": str(task.id), "batch_id": str(batch.id), "status": TaskStatus.QUEUED}


@router.get("/available-configs")
async def get_available_configs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取拆解可用的配置列表（从 AIResource 读取）"""
    from app.models.ai_resource import AIResource

    # 从 AIResource 获取配置，按 category 分组
    result = await db.execute(
        select(AIResource).where(
            AIResource.is_active == True,
            AIResource.category.in_(['methodology', 'qa_rules', 'output_style'])
        ).order_by(AIResource.category, AIResource.name)
    )
    all_resources = result.scalars().all()

    # 按分类分组
    adapt_methods = []
    quality_rules = []
    output_styles = []

    for resource in all_resources:
        config_info = {
            "key": resource.name,
            "description": resource.description or resource.name,
            "is_custom": False,
            "resource_id": str(resource.id)
        }

        if resource.category == "methodology":
            adapt_methods.append(config_info)
        elif resource.category == "qa_rules":
            quality_rules.append(config_info)
        elif resource.category == "output_style":
            output_styles.append(config_info)

    return {
        "adapt_methods": adapt_methods,
        "quality_rules": quality_rules,
        "output_styles": output_styles
    }


@router.get("/results/{batch_id}")
async def get_breakdown_results(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取拆解结果

    根据 format_version 返回不同结构：
    - format_version == 2: 返回 plot_points（新统一格式）
    - format_version == 1: 返回 6 个字段（旧格式）
    """
    from app.models.plot_breakdown import PlotBreakdown

    # 验证批次属于当前用户，并获取最新的拆解结果
    result = await db.execute(
        select(PlotBreakdown).join(Batch).join(Project).where(
            PlotBreakdown.batch_id == batch_id,
            Project.user_id == current_user.id
        ).order_by(PlotBreakdown.created_at.desc())  # 按创建时间降序，获取最新的
    )
    breakdown = result.scalars().first()  # 使用 first() 而不是 scalar_one_or_none()

    if not breakdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="拆解结果不存在"
        )

    # 根据 format_version 返回不同结构
    if breakdown.format_version == 2:
        # 新格式：返回 plot_points
        return {
            "id": str(breakdown.id),
            "batch_id": str(breakdown.batch_id),
            "format_version": 2,
            "plot_points": breakdown.plot_points,
            "qa_status": breakdown.qa_status,
            "qa_score": breakdown.qa_score,
            "qa_report": breakdown.qa_report,
            "qa_retry_count": breakdown.qa_retry_count,
            "used_adapt_method_id": breakdown.used_adapt_method_id,
            "created_at": breakdown.created_at.isoformat() if breakdown.created_at else None
        }
    else:
        # 旧格式：返回 6 个字段
        return {
            "id": str(breakdown.id),
            "batch_id": str(breakdown.batch_id),
            "format_version": 1,
            "conflicts": breakdown.conflicts,
            "plot_hooks": breakdown.plot_hooks,
            "characters": breakdown.characters,
            "scenes": breakdown.scenes,
            "emotions": breakdown.emotions,
            "episodes": breakdown.episodes,
            "consistency_status": breakdown.consistency_status,
            "consistency_score": breakdown.consistency_score,
            "qa_status": breakdown.qa_status,
            "qa_report": breakdown.qa_report,
            "created_at": breakdown.created_at.isoformat() if breakdown.created_at else None
        }


@router.patch("/results/{batch_id}/plot-points/{point_id}/status")
async def update_plot_point_status(
    batch_id: str,
    point_id: int,
    request: PlotPointStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新剧情点状态（used/unused）

    仅适用于 format_version == 2 的拆解结果。
    """
    from app.models.plot_breakdown import PlotBreakdown

    # 验证批次属于当前用户
    result = await db.execute(
        select(PlotBreakdown).join(Batch).join(Project).where(
            PlotBreakdown.batch_id == batch_id,
            Project.user_id == current_user.id
        ).order_by(PlotBreakdown.created_at.desc())
    )
    breakdown = result.scalars().first()

    if not breakdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="拆解结果不存在"
        )

    # 检查是否为新格式
    if breakdown.format_version != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此操作仅适用于 format_version == 2 的拆解结果"
        )

    # 检查 plot_points 是否存在
    if not breakdown.plot_points or not isinstance(breakdown.plot_points, list):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="拆解结果中不存在剧情点"
        )

    # 查找并更新对应的剧情点
    updated = False
    updated_points = []
    for point in breakdown.plot_points:
        if point.get("id") == point_id:
            new_point = {**point, "status": request.status}
            updated_points.append(new_point)
            updated = True
        else:
            updated_points.append(point)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到 id 为 {point_id} 的剧情点"
        )

    # 更新 plot_points
    breakdown.plot_points = updated_points
    await db.commit()
    await db.refresh(breakdown)

    return {
        "message": "剧情点状态更新成功",
        "point_id": point_id,
        "status": request.status
    }


@router.get("/results/{batch_id}/adapt-methods")
async def get_adapt_methods(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取可用的改编方法论列表

    查询 ai_resources 表中 category='adapt_method' 且 is_active=True 的资源。
    返回公共资源和用户自己的资源。
    """
    from sqlalchemy import or_

    # 验证批次归属（只需要验证用户有权限访问该项目）
    batch_result = await db.execute(
        select(Batch).join(Project).where(
            Batch.id == batch_id,
            Project.user_id == current_user.id
        )
    )
    batch = batch_result.scalar_one_or_none()

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="批次不存在或无权访问"
        )

    # 查询可用的改编方法论
    result = await db.execute(
        select(AIResource).where(
            AIResource.category == "adapt_method",
            AIResource.is_active == True,
            or_(
                AIResource.visibility == "public",
                AIResource.owner_id == current_user.id
            )
        ).order_by(AIResource.is_builtin.desc(), AIResource.name)
    )
    resources = result.scalars().all()

    return {
        "adapt_methods": [
            {
                "id": str(r.id),
                "name": r.name,
                "display_name": r.display_name,
                "description": r.description,
                "is_builtin": r.is_builtin,
                "is_custom": r.owner_id is not None,
                "version": r.version
            }
            for r in resources
        ],
        "total": len(resources)
    }


@router.post("/batch-start")
async def start_batch_breakdown(
    request: BatchStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量启动拆解（增强版）

    功能：
    - 支持自定义配置参数
    - 跳过已完成的批次
    - 配额预检查
    - 防止重复提交
    - 返回任务列表和批量信息
    """
    # 验证项目归属
    project_result = await db.execute(
        select(Project).where(
            Project.id == request.project_id,
            Project.user_id == current_user.id
        )
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在或无权访问"
        )
    
    # 检查项目是否配置了拆解模型
    if not project.breakdown_model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="项目未配置剧情拆解模型，请先在项目设置中选择模型"
        )

    # 获取所有未完成的批次（pending 或 failed）
    result = await db.execute(
        select(Batch).where(
            Batch.project_id == request.project_id,
            Batch.breakdown_status.in_([BatchStatus.PENDING, BatchStatus.FAILED])
        ).order_by(Batch.batch_number)
    )
    batches = result.scalars().all()

    if not batches:
        return {
            "task_ids": [],
            "total": 0,
            "message": "没有待拆解或可重试的批次",
            "project_id": request.project_id
        }

    # 检查每个批次是否已有任务在执行
    batch_ids = [batch.id for batch in batches]
    existing_tasks_result = await db.execute(
        select(AITask).where(
            AITask.batch_id.in_(batch_ids),
            AITask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.RETRYING, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLING])
        )
    )
    existing_tasks = existing_tasks_result.scalars().all()

    if existing_tasks:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"部分批次已有任务在执行中，任务数: {len(existing_tasks)}"
        )

    # 构建任务配置
    task_config = {}

    # 新版：资源 ID 列表（优先使用）
    if request.resource_ids:
        task_config["resource_ids"] = request.resource_ids

    # 旧版：单个资源 ID（保留兼容）
    if request.adapt_method_id:
        task_config["adapt_method_id"] = request.adapt_method_id
    if request.output_style_id:
        task_config["output_style_id"] = request.output_style_id
    if request.template_id:
        task_config["template_id"] = request.template_id

    # 兼容旧版 key
    if request.adapt_method_key:
        task_config["adapt_method_key"] = request.adapt_method_key
    if request.quality_rule_key:
        task_config["quality_rule_key"] = request.quality_rule_key
    if request.output_style_key:
        task_config["output_style_key"] = request.output_style_key

    # 锁定用户记录
    user_result = await db.execute(
        select(User).where(User.id == current_user.id).with_for_update()
    )
    locked_user = user_result.scalar_one()

    # 积分预检查（纯积分制）
    required_credits = len(batches) * 100  # breakdown 每次 100 积分
    quota_service = QuotaService(db)
    credits_check = await quota_service.check_credits(locked_user, "breakdown")

    if credits_check["balance"] < required_credits:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"积分不足: 需要 {required_credits}，余额 {credits_check['balance']}"
        )

    task_ids = []
    failed_batches = []

    for batch in batches:
        try:
            # 消耗积分（预扣）
            await quota_service.consume_credits(locked_user, "breakdown", "剧情拆解")

            # 创建AI任务
            task = AITask(
                project_id=batch.project_id,
                batch_id=batch.id,
                task_type="breakdown",
                status=TaskStatus.QUEUED,
                depends_on=[],
                config={
                    "model_config_id": str(project.breakdown_model_id),  # 从项目配置读取
                    **task_config  # 包含 adapt_method_key 等
                }
            )
            db.add(task)
            await db.flush()  # 获取 task.id

            # 启动Celery任务
            try:
                celery_task = run_breakdown_task.delay(
                    str(task.id),
                    str(batch.id),
                    str(batch.project_id),
                    str(current_user.id)
                )
                task.celery_task_id = celery_task.id
            except Exception:
                # Celery 提交失败
                failed_batches.append(str(batch.id))
                continue

            # 更新批次状态
            batch.breakdown_status = BatchStatus.QUEUED
            task_ids.append(str(task.id))

        except Exception:
            failed_batches.append(str(batch.id))
            continue

    # 提交事务
    await db.commit()

    if failed_batches:
        return {
            "task_ids": task_ids,
            "total": len(task_ids),
            "failed": len(failed_batches),
            "project_id": request.project_id,
            "config": task_config,
            "message": f"已启动 {len(task_ids)} 个任务，{len(failed_batches)} 个失败"
        }

    return {
        "task_ids": task_ids,
        "total": len(task_ids),
        "project_id": request.project_id,
        "config": task_config,
        "message": f"已启动 {len(task_ids)} 个拆解任务"
    }


@router.get("/batch-progress/{project_id}")
async def get_batch_progress(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目批量拆解进度

    返回：
    - total_batches: 批次总数
    - completed: 已完成数
    - in_progress: 进行中数
    - pending: 待处理数
    - failed: 失败数
    - overall_progress: 整体进度百分比
    - task_details: 各任务详细状态列表
    """
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

    # 获取所有批次
    batches_result = await db.execute(
        select(Batch).where(Batch.project_id == project_id).order_by(Batch.batch_number)
    )
    batches = batches_result.scalars().all()

    # 获取批次ID列表
    batch_ids = [b.id for b in batches]

    # 获取对应的任务
    tasks_result = await db.execute(
        select(AITask).where(
            AITask.batch_id.in_(batch_ids),
            AITask.task_type == "breakdown"
        )
    )
    tasks = {str(t.batch_id): t for t in tasks_result.scalars().all()}

    # 统计各状态数量
    status_counts = {
        BatchStatus.PENDING: 0,
        BatchStatus.QUEUED: 0,
        TaskStatus.RUNNING: 0,
        TaskStatus.RETRYING: 0,
        BatchStatus.COMPLETED: 0,
        BatchStatus.FAILED: 0
    }

    task_details = []
    for batch in batches:
        task = tasks.get(str(batch.id))
        batch_status = batch.breakdown_status or BatchStatus.PENDING
        status_counts[batch_status] = status_counts.get(batch_status, 0) + 1

        task_detail = {
            "batch_id": str(batch.id),
            "batch_number": batch.batch_number,
            "batch_status": batch_status,
            "chapter_count": batch.total_chapters or 0
        }

        if task:
            task_detail.update({
                "task_id": str(task.id),
                "task_status": _normalize_task_status(task.status),
                "progress": task.progress or 0,
                "current_step": task.current_step or "",
                "retry_count": task.retry_count or 0,
                "error_message": task.error_message
            })

            # 解析错误信息
            if task.error_message:
                try:
                    error_data = eval(task.error_message) if task.error_message.startswith('{') else None
                    if error_data and isinstance(error_data, dict):
                        task_detail["error_code"] = error_data.get("code")
                        task_detail["error_info"] = error_data
                except:
                    pass

        task_details.append(task_detail)

    # 计算整体进度
    total = len(batches)
    completed = status_counts.get(BatchStatus.COMPLETED, 0)
    overall_progress = round(completed / total * 100, 1) if total > 0 else 0

    return {
        "project_id": project_id,
        "total_batches": total,
        "completed": status_counts.get(BatchStatus.COMPLETED, 0),
        "in_progress": status_counts.get(TaskStatus.RUNNING, 0) + status_counts.get(TaskStatus.RETRYING, 0),
        "pending": status_counts.get(BatchStatus.PENDING, 0) + status_counts.get(BatchStatus.QUEUED, 0),
        "failed": status_counts.get(BatchStatus.FAILED, 0),
        "overall_progress": overall_progress,
        "status_summary": status_counts,
        "task_details": task_details,
        "last_updated": datetime.utcnow().isoformat()
    }


@router.post("/tasks/{task_id}/retry")
async def retry_failed_task(
    task_id: str,
    request: TaskRetryRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """重试失败的任务

    功能：
    - 支持修改配置重试
    - 限制重试次数（最多3次）
    - 自动检查配额
    - 校验上一批次是否已完成（防止跳集拆解）
    """
    # 验证任务归属
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

    if task.status != TaskStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只有失败的任务可以重试，当前状态: {task.status}"
        )

    if task.retry_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="任务已重试3次，无法继续重试"
        )

    # 获取批次信息
    batch_result = await db.execute(
        select(Batch).where(Batch.id == task.batch_id)
    )
    batch = batch_result.scalar_one_or_none()

    if batch:
        # 校验上一批次是否已完成（防止跳集拆解）
        prev_batch_result = await db.execute(
            select(Batch).where(
                Batch.project_id == batch.project_id,
                Batch.batch_number < batch.batch_number
            ).order_by(Batch.batch_number.desc()).limit(1)
        )
        prev_batch = prev_batch_result.scalar_one_or_none()

        if prev_batch and prev_batch.breakdown_status != BatchStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"上一批次（第{prev_batch.batch_number}集）尚未完成拆解，无法重新拆解"
            )

    # 检查积分（纯积分制，重试半价）
    quota_service = QuotaService(db)
    credits_check = await quota_service.check_credits(current_user, "retry")
    if not credits_check["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"积分不足: 需要 {credits_check['cost']}，余额 {credits_check['balance']}"
        )

    # 确定配置（使用新配置或原配置）
    if request and request.new_config:
        new_config = {**task.config, **request.new_config}
    else:
        new_config = task.config

    try:
        # 使用事务保证原子性
        async with db.begin_nested():
            # 先消耗积分（预扣，重试半价）
            await quota_service.consume_credits(current_user, "retry", "任务重试")

            # 创建新任务记录
            new_task = AITask(
                project_id=task.project_id,
                batch_id=task.batch_id,
                task_type="breakdown",
                status=TaskStatus.QUEUED,
                retry_count=task.retry_count + 1,
                depends_on=[],
                config=new_config
            )
            db.add(new_task)
            await db.flush()  # 获取 new_task.id

            # 启动Celery任务
            celery_task = run_breakdown_task.delay(
                str(new_task.id),
                str(task.batch_id),
                str(task.project_id),
                str(current_user.id)
            )

            new_task.celery_task_id = celery_task.id

            # 更新批次状态
            batch_result = await db.execute(
                select(Batch).where(Batch.id == task.batch_id)
            )
            batch = batch_result.scalar_one_or_none()
            if batch:
                batch.breakdown_status = BatchStatus.QUEUED

        # 提交事务
        await db.commit()
        await db.refresh(new_task)

        return {
            "task_id": str(new_task.id),
            "status": TaskStatus.QUEUED,
            "retry_count": new_task.retry_count,
            "batch_id": str(task.batch_id),
            "config": new_config,
            "message": f"任务已重新加入队列（第 {new_task.retry_count} 次尝试）"
        }

    except Exception as e:
        # 如果任务启动失败，回滚事务（配额会被回滚）
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"任务重试失败: {str(e)}"
        )


@router.get("/results/{batch_id}/detail")
async def get_breakdown_detail(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取拆解详情（包括模型、资源、质检信息等）

    返回：
    - breakdown_id: 拆解记录 ID
    - created_at: 创建时间
    - model_info: 使用的模型信息
    - resource_info: 使用的资源信息（改编方法论等）
    - qa_status: 质检状态
    - qa_score: 质检分数
    - qa_report: 质检报告
    - qa_retry_count: 质检重试次数
    - task_info: 任务执行信息
    """
    from app.models.plot_breakdown import PlotBreakdown
    from app.models.llm_call_log import LLMCallLog
    from app.models.model_config import ModelConfig

    # 验证批次属于当前用户，并获取最新的拆解结果
    result = await db.execute(
        select(PlotBreakdown).join(Batch).join(Project).where(
            PlotBreakdown.batch_id == batch_id,
            Project.user_id == current_user.id
        ).order_by(PlotBreakdown.created_at.desc())
    )
    breakdown = result.scalars().first()

    if not breakdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="拆解结果不存在"
        )

    # 获取关联的任务信息
    task_result = await db.execute(
        select(AITask).where(
            AITask.batch_id == batch_id,
            AITask.task_type == "breakdown"
        ).order_by(AITask.created_at.desc())
    )
    task = task_result.scalars().first()

    # 构建任务信息
    task_info = None
    model_info = None
    if task:
        # 计算执行时长
        duration_seconds = None
        if task.started_at and task.completed_at:
            duration_seconds = int((task.completed_at - task.started_at).total_seconds())

        task_info = {
            "task_id": str(task.id),
            "status": _normalize_task_status(task.status),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "duration_seconds": duration_seconds,
            "retry_count": task.retry_count or 0
        }

        # 从任务配置中获取模型信息
        if task.config and task.config.get("model_config_id"):
            model_config_id = task.config.get("model_config_id")
            model_result = await db.execute(
                select(ModelConfig).where(ModelConfig.id == model_config_id)
            )
            model_config = model_result.scalar_one_or_none()
            if model_config:
                model_info = {
                    "provider": model_config.provider,
                    "model_name": model_config.model_name,
                    "display_name": model_config.display_name
                }

    # 如果没有从任务配置获取到模型信息，尝试从 LLM 调用日志获取
    if not model_info and task:
        llm_log_result = await db.execute(
            select(LLMCallLog).where(
                LLMCallLog.task_id == task.id
            ).order_by(LLMCallLog.created_at.desc()).limit(1)
        )
        llm_log = llm_log_result.scalar_one_or_none()
        if llm_log:
            model_info = {
                "provider": llm_log.provider,
                "model_name": llm_log.model_name,
                "display_name": f"{llm_log.provider}/{llm_log.model_name}"
            }

    # 获取资源信息（改编方法论，used_adapt_method_id 存储的是 AIResource.name）
    resource_info = {}
    if breakdown.used_adapt_method_id:
        adapt_method_result = await db.execute(
            select(AIResource).where(AIResource.name == breakdown.used_adapt_method_id)
        )
        adapt_method = adapt_method_result.scalar_one_or_none()
        if adapt_method:
            resource_info["adapt_method"] = {
                "id": str(adapt_method.id),
                "name": adapt_method.name,
                "display_name": adapt_method.display_name
            }

    return {
        "breakdown_id": str(breakdown.id),
        "batch_id": str(breakdown.batch_id),
        "created_at": breakdown.created_at.isoformat() if breakdown.created_at else None,
        "format_version": breakdown.format_version,
        "model_info": model_info,
        "resource_info": resource_info,
        "qa_status": breakdown.qa_status,
        "qa_score": breakdown.qa_score,
        "qa_report": breakdown.qa_report,
        "qa_retry_count": breakdown.qa_retry_count or 0,
        "task_info": task_info
    }


@router.get("/results/{batch_id}/history")
async def get_breakdown_history(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取批次的拆解历史列表（同一批次的多次拆解记录）

    返回按创建时间倒序排列的拆解记录列表。
    """
    from app.models.plot_breakdown import PlotBreakdown
    from app.models.model_config import ModelConfig

    # 验证批次属于当前用户，并获取所有拆解记录
    result = await db.execute(
        select(PlotBreakdown).join(Batch).join(Project).where(
            PlotBreakdown.batch_id == batch_id,
            Project.user_id == current_user.id
        ).order_by(PlotBreakdown.created_at.desc())
    )
    breakdowns = result.scalars().all()

    if not breakdowns:
        return {"items": []}

    items = []
    for breakdown in breakdowns:
        task_info = None
        model_info = None

        # 直接通过 task_id 获取任务信息（新字段）
        if breakdown.task_id:
            task_result = await db.execute(
                select(AITask).where(AITask.id == breakdown.task_id)
            )
            task = task_result.scalar_one_or_none()
            if task:
                duration_seconds = None
                if task.started_at and task.completed_at:
                    duration_seconds = int((task.completed_at - task.started_at).total_seconds())

                task_info = {
                    "task_id": str(task.id),
                    "status": _normalize_task_status(task.status),
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "duration_seconds": duration_seconds,
                    "retry_count": task.retry_count or 0
                }

        # 直接通过 model_config_id 获取模型信息（新字段）
        if breakdown.model_config_id:
            model_result = await db.execute(
                select(ModelConfig).where(ModelConfig.id == breakdown.model_config_id)
            )
            model_config = model_result.scalar_one_or_none()
            if model_config:
                model_info = {
                    "provider": model_config.provider,
                    "model_name": model_config.model_name,
                    "display_name": model_config.display_name
                }

        # 获取资源信息（used_adapt_method_id 存储的是 AIResource.name，不是 id）
        resource_info = {}
        if breakdown.used_adapt_method_id:
            adapt_method_result = await db.execute(
                select(AIResource).where(AIResource.name == breakdown.used_adapt_method_id)
            )
            adapt_method = adapt_method_result.scalar_one_or_none()
            if adapt_method:
                resource_info["adapt_method"] = {
                    "id": str(adapt_method.id),
                    "name": adapt_method.name,
                    "display_name": adapt_method.display_name
                }

        # 计算剧情点数量
        plot_points_count = len(breakdown.plot_points) if breakdown.plot_points else 0

        items.append({
            "breakdown_id": str(breakdown.id),
            "batch_id": str(breakdown.batch_id),
            "created_at": breakdown.created_at.isoformat() if breakdown.created_at else None,
            "format_version": breakdown.format_version,
            "model_info": model_info,
            "resource_info": resource_info,
            "qa_status": breakdown.qa_status,
            "qa_score": breakdown.qa_score,
            "qa_report": breakdown.qa_report,
            "qa_retry_count": breakdown.qa_retry_count or 0,
            "plot_points_count": plot_points_count,
            "task_info": task_info
        })

    return {"items": items}


@router.post("/tasks/{task_id}/stop")
async def stop_breakdown_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """停止正在执行的拆解任务

    功能：
    - 使用 Celery revoke 停止正在执行的任务
    - 更新任务状态为 canceled
    - 返还已扣除的配额
    - 更新批次状态为 pending（允许重新提交）
    - 取消后续排队中的批次任务
    """
    # 验证任务归属
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

    # 只有正在执行的任务可以停止
    if task.status not in [TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.RETRYING, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只有正在执行的任务可以停止，当前状态: {task.status}"
        )

    cancelled_count = 0  # 取消的任务数量

    try:
        # 1. 使用 Celery revoke 停止任务（如果任务已在队列中）
        if task.celery_task_id:
            celery_app.control.revoke(task.celery_task_id, terminate=True)
            print(f"已撤销 Celery 任务: {task.celery_task_id}")

        # 2. 标记任务正在取消
        task.status = TaskStatus.CANCELLING
        task.current_step = "正在停止"
        task.error_message = None  # 清除错误信息
        cancelled_count += 1

        # 3. 获取批次信息
        batch_result = await db.execute(
            select(Batch).where(Batch.id == task.batch_id)
        )
        batch = batch_result.scalar_one_or_none()

        if batch:
            # 关键修复：立即更新当前批次状态为 PENDING，让前端可以重新提交
            batch.breakdown_status = BatchStatus.PENDING

            # 4. 取消该批次之后所有进行中的任务
            subsequent_tasks_result = await db.execute(
                select(AITask).join(Batch).where(
                    Batch.project_id == batch.project_id,
                    Batch.batch_number > batch.batch_number,
                    AITask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.RETRYING, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLING])
                )
            )
            subsequent_tasks = subsequent_tasks_result.scalars().all()

            for subsequent_task in subsequent_tasks:
                # 撤销 Celery 任务
                if subsequent_task.celery_task_id:
                    celery_app.control.revoke(subsequent_task.celery_task_id, terminate=True)
                    print(f"已撤销后续排队任务: {subsequent_task.celery_task_id}")

                # 更新任务状态
                subsequent_task.status = TaskStatus.CANCELED
                subsequent_task.current_step = "因前置任务停止而被取消"
                subsequent_task.error_message = None

                # 更新对应批次状态为 pending
                subsequent_batch_result = await db.execute(
                    select(Batch).where(Batch.id == subsequent_task.batch_id)
                )
                subsequent_batch = subsequent_batch_result.scalar_one_or_none()
                if subsequent_batch:
                    subsequent_batch.breakdown_status = BatchStatus.PENDING

                cancelled_count += 1

            if subsequent_tasks:
                print(f"已取消 {len(subsequent_tasks)} 个后续排队任务")

        # 5. 返还配额（使用同步方法，避免 greenlet 问题）
        try:
            from app.core.database import SyncSessionLocal
            sync_db = SyncSessionLocal()
            try:
                refund_episode_quota_sync(sync_db, task.project_id, 1)
                sync_db.commit()
                print(f"已返还配额: project_id={task.project_id}")
            finally:
                sync_db.close()
        except Exception as refund_error:
            print(f"返还配额失败: {refund_error}")

        # 6. 扣除已消耗的 Token 费用（即使任务被停止，也需要扣费）
        token_deducted = 0
        try:
            from app.core.credits import consume_token_credits_sync
            sync_db = SyncSessionLocal()
            try:
                token_result = consume_token_credits_sync(
                    db=sync_db,
                    user_id=str(current_user.id),
                    task_id=task_id,
                    task_type="breakdown"
                )
                if token_result.get("token_credits", 0) > 0:
                    sync_db.commit()
                    token_deducted = token_result.get("token_credits", 0)
                    print(f"已扣除 Token 费用: {token_deducted} 积分")
            finally:
                sync_db.close()
        except Exception as token_error:
            print(f"扣除 Token 费用失败: {token_error}")

        # 7. 提交事务
        await db.commit()

        # 构建返回消息
        message_parts = [f"已停止任务"]
        if cancelled_count > 1:
            message_parts.append(f"（含 {cancelled_count - 1} 个后续排队任务）")
        if token_deducted > 0:
            message_parts.append(f"，已扣除 Token 费用 {token_deducted} 积分")
        message = "".join(message_parts)

        return {
            "task_id": str(task.id),
            "status": TaskStatus.CANCELLING,
            "cancelled_count": cancelled_count,
            "message": message,
            "token_deducted": token_deducted
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止任务失败: {str(e)}"
        )

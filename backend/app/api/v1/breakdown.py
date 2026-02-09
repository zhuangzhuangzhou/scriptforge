from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
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
    # 配置选择
    adapt_method_key: Optional[str] = "adapt_method_default"
    quality_rule_key: Optional[str] = "qa_breakdown_default"
    output_style_key: Optional[str] = "output_style_default"


class BatchStartRequest(BaseModel):
    """批量启动拆解请求"""
    project_id: str
    # 可选配置参数
    adapt_method_key: Optional[str] = "adapt_method_default"
    quality_rule_key: Optional[str] = "qa_breakdown_default"
    output_style_key: Optional[str] = "output_style_default"
    # 并发控制
    concurrent_limit: Optional[int] = Field(default=3, ge=1, le=10)


class TaskRetryRequest(BaseModel):
    """任务重试请求"""
    new_config: Optional[dict] = None


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

    try:
        # 使用事务保证原子性
        async with db.begin_nested():
            # 先消耗剧集配额（预扣）
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
                    "pipeline_id": request.pipeline_id,
                    "adapt_method_key": request.adapt_method_key,
                    "quality_rule_key": request.quality_rule_key,
                    "output_style_key": request.output_style_key
                }
            )
            db.add(task)
            await db.flush()  # 获取 task.id

            # 启动Celery异步任务
            celery_task = run_breakdown_task.delay(
                str(task.id),
                str(batch.id),
                str(batch.project_id),
                str(current_user.id)
            )

            # 更新任务的celery_task_id
            task.celery_task_id = celery_task.id

            # 更新批次状态
            batch.breakdown_status = "queued"

        # 提交事务
        await db.commit()
        await db.refresh(task)

        return {"task_id": str(task.id), "status": "queued"}

    except Exception as e:
        # 如果任务启动失败，回滚事务（配额会被回滚）
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"任务创建失败: {str(e)}"
        )


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
    - 更新批次状态
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

    try:
        task_ids = []
        # 使用事务保证原子性
        async with db.begin_nested():
            for batch in batches:
                # 先消耗剧集配额（预扣）
                await quota_service.consume_episode_quota(current_user)

                # 创建AI任务
                task = AITask(
                    project_id=batch.project_id,
                    batch_id=batch.id,
                    task_type="breakdown",
                    status="queued",
                    depends_on=[],
                    config={
                        "adapt_method_key": "adapt_method_default",
                        "quality_rule_key": "qa_breakdown_default",
                        "output_style_key": "output_style_default"
                    }
                )
                db.add(task)
                await db.flush()  # 获取 task.id

                # 启动Celery异步任务
                celery_task = run_breakdown_task.delay(
                    str(task.id),
                    str(batch.id),
                    str(batch.project_id),
                    str(current_user.id)
                )

                task.celery_task_id = celery_task.id

                # 更新批次状态
                batch.breakdown_status = "queued"

                task_ids.append(str(task.id))

        # 提交事务
        await db.commit()

        return {"task_ids": task_ids, "total": len(task_ids)}

    except Exception as e:
        # 如果任务启动失败，回滚事务（配额会被回滚）
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量任务创建失败: {str(e)}"
        )


@router.post("/start-continue")
async def start_continue_breakdown(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """继续拆解：从第一个 pending 批次开始

    优化：
    - 配额在任务成功启动后才消耗
    - 使用事务保证数据一致性
    - 更新批次状态
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

    try:
        # 使用事务保证原子性
        async with db.begin_nested():
            # 先消耗剧集配额（预扣）
            await quota_service.consume_episode_quota(current_user)

            # 创建AI任务
            task = AITask(
                project_id=batch.project_id,
                batch_id=batch.id,
                task_type="breakdown",
                status="queued",
                depends_on=[],
                config={
                    "adapt_method_key": "adapt_method_default",
                    "quality_rule_key": "qa_breakdown_default",
                    "output_style_key": "output_style_default"
                }
            )
            db.add(task)
            await db.flush()  # 获取 task.id

            # 启动Celery异步任务
            celery_task = run_breakdown_task.delay(
                str(task.id),
                str(batch.id),
                str(batch.project_id),
                str(current_user.id)
            )

            task.celery_task_id = celery_task.id

            # 更新批次状态
            batch.breakdown_status = "queued"

        # 提交事务
        await db.commit()
        await db.refresh(task)

        return {"task_id": str(task.id), "batch_id": str(batch.id), "status": "queued"}

    except Exception as e:
        # 如果任务启动失败，回滚事务（配额会被回滚）
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"任务创建失败: {str(e)}"
        )


@router.get("/available-configs")
async def get_available_configs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取拆解可用的配置列表"""
    from app.models.ai_configuration import AIConfiguration

    # 获取所有配置（用户自定义 + 系统默认）
    result = await db.execute(
        select(AIConfiguration).where(
            (AIConfiguration.user_id == current_user.id) | (AIConfiguration.user_id.is_(None)),
            AIConfiguration.is_active == True,
            AIConfiguration.category.in_(['adapt_method', 'quality_rule', 'prompt_template'])
        ).order_by(AIConfiguration.category, AIConfiguration.user_id.desc().nulls_last())
    )
    all_configs = result.scalars().all()

    # 按分类分组（用户配置优先）
    adapt_methods = []
    quality_rules = []
    output_styles = []

    seen_keys = {
        'adapt_method': set(),
        'quality_rule': set(),
        'prompt_template': set()
    }

    for config in all_configs:
        # 跳过已见过的 key（用户配置优先于系统默认）
        if config.key in seen_keys[config.category]:
            continue
        seen_keys[config.category].add(config.key)

        config_info = {
            "key": config.key,
            "description": config.description,
            "is_custom": config.user_id is not None
        }

        if config.category == "adapt_method":
            adapt_methods.append(config_info)
        elif config.category == "quality_rule":
            quality_rules.append(config_info)
        elif config.category == "prompt_template" and "output_style" in config.key:
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


@router.post("/start-batch")
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
            detail="项目不存在"
        )

    # 获取所有未完成的批次（pending 或 failed）
    result = await db.execute(
        select(Batch).where(
            Batch.project_id == request.project_id,
            Batch.breakdown_status.in_(['pending', 'failed'])
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

    # 配额预检查
    required_quota = len(batches)
    quota_service = QuotaService(db)
    quota = await quota_service.check_episode_quota(current_user)

    if quota["remaining"] != -1 and quota["remaining"] < required_quota:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"配额不足：需要 {required_quota} 集，剩余 {quota['remaining']} 集"
        )

    # 构建任务配置
    task_config = {
        "adapt_method_key": request.adapt_method_key,
        "quality_rule_key": request.quality_rule_key,
        "output_style_key": request.output_style_key
    }

    try:
        task_ids = []
        # 使用事务保证原子性
        async with db.begin_nested():
            for batch in batches:
                # 先消耗剧集配额（预扣）
                await quota_service.consume_episode_quota(current_user)

                # 创建AI任务
                task = AITask(
                    project_id=batch.project_id,
                    batch_id=batch.id,
                    task_type="breakdown",
                    status="queued",
                    depends_on=[],
                    config=task_config
                )
                db.add(task)
                await db.flush()  # 获取 task.id

                # 启动Celery任务
                celery_task = run_breakdown_task.delay(
                    str(task.id),
                    str(batch.id),
                    str(batch.project_id),
                    str(current_user.id)
                )

                task.celery_task_id = celery_task.id

                # 更新批次状态
                batch.breakdown_status = "queued"

                task_ids.append(str(task.id))

        # 提交事务
        await db.commit()

        return {
            "task_ids": task_ids,
            "total": len(task_ids),
            "project_id": request.project_id,
            "config": task_config,
            "message": f"已启动 {len(task_ids)} 个拆解任务"
        }

    except Exception as e:
        # 如果任务启动失败，回滚事务（配额会被回滚）
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量任务创建失败: {str(e)}"
        )


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
        "pending": 0,
        "queued": 0,
        "running": 0,
        "retrying": 0,
        "completed": 0,
        "failed": 0
    }

    task_details = []
    for batch in batches:
        task = tasks.get(str(batch.id))
        batch_status = batch.breakdown_status or "pending"
        status_counts[batch_status] = status_counts.get(batch_status, 0) + 1

        task_detail = {
            "batch_id": str(batch.id),
            "batch_number": batch.batch_number,
            "batch_status": batch_status,
            "chapter_count": batch.chapter_count or 0
        }

        if task:
            task_detail.update({
                "task_id": str(task.id),
                "task_status": task.status,
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
    completed = status_counts.get("completed", 0)
    overall_progress = round(completed / total * 100, 1) if total > 0 else 0

    return {
        "project_id": project_id,
        "total_batches": total,
        "completed": status_counts.get("completed", 0),
        "in_progress": status_counts.get("running", 0) + status_counts.get("retrying", 0),
        "pending": status_counts.get("pending", 0) + status_counts.get("queued", 0),
        "failed": status_counts.get("failed", 0),
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

    if task.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只有失败的任务可以重试，当前状态: {task.status}"
        )

    if task.retry_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="任务已重试3次，无法继续重试"
        )

    # 检查配额
    quota_service = QuotaService(db)
    quota = await quota_service.check_episode_quota(current_user)
    if not quota["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="剧集配额已用尽，无法重试"
        )

    # 确定配置（使用新配置或原配置）
    if request and request.new_config:
        new_config = {**task.config, **request.new_config}
    else:
        new_config = task.config

    try:
        # 使用事务保证原子性
        async with db.begin_nested():
            # 先消耗剧集配额（预扣）
            await quota_service.consume_episode_quota(current_user)

            # 创建新任务记录
            new_task = AITask(
                project_id=task.project_id,
                batch_id=task.batch_id,
                task_type="breakdown",
                status="queued",
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
                batch.breakdown_status = "queued"

        # 提交事务
        await db.commit()
        await db.refresh(new_task)

        return {
            "task_id": str(new_task.id),
            "status": "queued",
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

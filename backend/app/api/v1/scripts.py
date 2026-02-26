from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field, field_serializer, model_validator
from typing import Optional, List, Any
from datetime import datetime, timezone
from uuid import UUID
from app.core.database import get_db
from app.models.user import User
from app.models.batch import Batch
from app.models.project import Project
from app.models.ai_task import AITask
from app.models.plot_breakdown import PlotBreakdown
from app.models.script import Script
from app.api.v1.auth import get_current_user
from app.api.v1.breakdown import _humanize_error_message
from app.core.quota import QuotaService
from app.core.status import TaskStatus, TaskType

router = APIRouter()


# ==================== 剧集摘要聚合接口 ====================

class EpisodeScriptInfo(BaseModel):
    """剧集中的剧本信息（轻量版，不含大字段）"""
    id: str
    title: Optional[str] = None
    word_count: int = 0
    qa_status: Optional[str] = None
    qa_score: Optional[int] = None
    # 移除大字段: structure, full_script, qa_report


class EpisodeSummaryItem(BaseModel):
    """单个剧集摘要"""
    episode_number: int
    status: str  # pending | in_progress | completed | failed
    breakdown_id: Optional[str] = None
    batch_id: Optional[str] = None
    script: Optional[EpisodeScriptInfo] = None


class RunningTaskInfo(BaseModel):
    """正在运行的任务信息"""
    task_id: str
    episode_number: int
    progress: int = 0
    current_step: Optional[str] = None


class ProgressSummary(BaseModel):
    """进度统计"""
    total: int = 0
    completed: int = 0
    in_progress: int = 0
    pending: int = 0
    failed: int = 0


class PaginationInfo(BaseModel):
    """分页信息"""
    page: int
    page_size: int
    total_pages: int


class EpisodesSummaryResponse(BaseModel):
    """剧集摘要响应"""
    episodes: List[EpisodeSummaryItem]
    running_task: Optional[RunningTaskInfo] = None
    progress: ProgressSummary
    pagination: PaginationInfo


@router.get("/episodes/summary", response_model=EpisodesSummaryResponse)
async def get_episodes_summary(
    project_id: str,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目的剧集摘要（Script Tab 专用聚合接口）

    支持分页，返回轻量级数据（不含 structure、full_script 等大字段）。
    进度统计基于全量数据计算，不受分页影响。
    """
    # 验证项目归属
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 1. 获取拆解结果（只查必要字段，不加载整个对象）
    breakdowns_result = await db.execute(
        select(
            PlotBreakdown.id,
            PlotBreakdown.batch_id,
            PlotBreakdown.plot_points
        ).join(Batch).where(
            Batch.project_id == project_id
        )
    )
    breakdowns = breakdowns_result.all()

    # 建立 episode -> breakdown 映射
    episode_map: dict[int, dict[str, Any]] = {}
    for breakdown_id, batch_id, plot_points in breakdowns:
        if plot_points:
            for pp in plot_points:
                ep = pp.get("episode")
                if ep and ep > 0 and ep not in episode_map:
                    episode_map[ep] = {
                        "episode_number": ep,
                        "status": "pending",
                        "breakdown_id": str(breakdown_id),
                        "batch_id": str(batch_id),
                        "script": None
                    }

    # 2. 获取已生成的剧本（只查必要字段，排除 content 大字段）
    scripts_result = await db.execute(
        select(
            Script.id,
            Script.episode_number,
            Script.title,
            Script.word_count,
            Script.qa_status,
            Script.qa_score,
            Script.plot_breakdown_id,
            Script.batch_id
        ).where(
            Script.project_id == project_id,
            Script.is_current.is_(True)
        )
    )
    scripts = scripts_result.all()

    for script_id, ep, title, word_count, qa_status, qa_score, plot_breakdown_id, batch_id in scripts:
        script_info = EpisodeScriptInfo(
            id=str(script_id),
            title=title,
            word_count=word_count or 0,
            qa_status=qa_status,
            qa_score=qa_score
        )

        if ep in episode_map:
            episode_map[ep]["status"] = "completed"
            episode_map[ep]["script"] = script_info
        else:
            episode_map[ep] = {
                "episode_number": ep,
                "status": "completed",
                "breakdown_id": str(plot_breakdown_id) if plot_breakdown_id else None,
                "batch_id": str(batch_id) if batch_id else None,
                "script": script_info
            }

    # 3. 获取正在运行的任务（只查必要字段）
    running_task_result = await db.execute(
        select(
            AITask.id,
            AITask.config,
            AITask.result,
            AITask.progress,
            AITask.current_step
        ).where(
            AITask.project_id == project_id,
            AITask.task_type == TaskType.EPISODE_SCRIPT,
            AITask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.IN_PROGRESS, TaskStatus.RETRYING])
        ).order_by(AITask.created_at.desc()).limit(1)
    )
    running_task = running_task_result.first()

    running_task_info = None
    if running_task:
        task_id, config, task_result, task_progress, current_step = running_task
        ep_num = (config.get("episode_number") if config else None) or \
                 (task_result.get("episode_number") if task_result else None)
        running_task_info = RunningTaskInfo(
            task_id=str(task_id),
            episode_number=ep_num or 0,
            progress=task_progress or 0,
            current_step=current_step
        )
        if ep_num and ep_num in episode_map:
            episode_map[ep_num]["status"] = "in_progress"

    # 4. 检查失败的任务（只查必要字段）
    failed_tasks_result = await db.execute(
        select(AITask.config).where(
            AITask.project_id == project_id,
            AITask.task_type == TaskType.EPISODE_SCRIPT,
            AITask.status == TaskStatus.FAILED
        ).order_by(AITask.created_at.desc())
    )
    failed_tasks = failed_tasks_result.all()

    for (config,) in failed_tasks:
        ep_num = config.get("episode_number") if config else None
        if ep_num and ep_num in episode_map:
            if episode_map[ep_num]["status"] == "pending":
                episode_map[ep_num]["status"] = "failed"

    # 构建响应
    all_episodes = sorted(
        [EpisodeSummaryItem(**ep) for ep in episode_map.values()],
        key=lambda x: x.episode_number
    )

    # 统计进度（基于全量数据）
    progress = ProgressSummary(
        total=len(all_episodes),
        completed=sum(1 for ep in all_episodes if ep.status == "completed"),
        in_progress=sum(1 for ep in all_episodes if ep.status == "in_progress"),
        pending=sum(1 for ep in all_episodes if ep.status == "pending"),
        failed=sum(1 for ep in all_episodes if ep.status == "failed")
    )

    # 分页
    total_items = len(all_episodes)
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_episodes = all_episodes[start_idx:end_idx]

    return EpisodesSummaryResponse(
        episodes=paged_episodes,
        running_task=running_task_info,
        progress=progress,
        pagination=PaginationInfo(
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


class EpisodeScriptStartRequest(BaseModel):
    """启动单集剧本生成请求"""
    breakdown_id: str
    episode_number: int = Field(..., ge=1)
    model_config_id: Optional[str] = None
    novel_type: Optional[str] = None


class BatchScriptStartRequest(BaseModel):
    """批量生成剧本请求"""
    breakdown_id: str
    episode_numbers: List[int] = Field(..., min_length=1)
    model_config_id: Optional[str] = None
    novel_type: Optional[str] = None


class ScriptUpdateRequest(BaseModel):
    """更新剧本请求"""
    title: Optional[str] = None
    content: Optional[dict] = None
    full_script: Optional[str] = None


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
    status: Optional[str] = None
    qa_status: Optional[str] = None
    qa_score: Optional[int] = None
    qa_report: Optional[dict] = None
    created_at: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def convert_orm_fields(cls, data):
        """将 ORM 对象转换为字典，处理 UUID 和 datetime 字段"""
        if hasattr(data, '__dict__'):
            # 这是一个 ORM 对象
            return {
                'id': str(data.id),
                'project_id': str(data.project_id),
                'batch_id': str(data.batch_id),
                'plot_breakdown_id': str(data.plot_breakdown_id) if data.plot_breakdown_id else None,
                'episode_number': data.episode_number,
                'title': data.title,
                'content': data.content,
                'word_count': data.word_count,
                'scene_count': data.scene_count,
                'status': data.status,
                'qa_status': data.qa_status,
                'qa_score': data.qa_score,
                'qa_report': data.qa_report,
                'created_at': data.created_at.isoformat() if data.created_at else None,
            }
        return data

    @field_serializer('id')
    def serialize_uuid(self, value: str) -> str:
        return value

    @field_serializer('project_id')
    def serialize_project_id(self, value: str) -> str:
        return value

    @field_serializer('batch_id')
    def serialize_batch_id(self, value: str) -> str:
        return value

    @field_serializer('plot_breakdown_id')
    def serialize_plot_breakdown_id(self, value: Optional[str]) -> Optional[str]:
        return value

    @field_serializer('created_at')
    def serialize_datetime(self, value: Optional[str]) -> Optional[str]:
        return value

    class Config:
        from_attributes = True


@router.get("", response_model=List[ScriptResponse])
async def list_scripts(
    project_id: Optional[str] = None,
    batch_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取剧本列表（只返回当前版本）"""
    query = select(Script).join(Project).where(
        Project.user_id == current_user.id,
        Script.is_current  # 只返回当前版本
    )

    if project_id:
        query = query.where(Script.project_id == project_id)
    if batch_id:
        query = query.where(Script.batch_id == batch_id)

    query = query.order_by(Script.created_at.desc())
    result = await db.execute(query)
    scripts = result.scalars().all()
    return scripts


# ==================== 剧本历史 API ====================

class ScriptHistoryItem(BaseModel):
    """剧本历史项"""
    script_id: str
    episode_number: int
    title: str
    word_count: int
    scene_count: int
    qa_status: Optional[str] = None
    qa_score: Optional[int] = None
    is_current: bool
    created_at: str


@router.get("/episode/{project_id}/{episode_number}/history", response_model=List[ScriptHistoryItem])
async def get_script_history(
    project_id: str,
    episode_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取某集的所有剧本历史版本"""
    # 验证项目属于当前用户
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 查询该集的所有历史版本
    result = await db.execute(
        select(Script).where(
            Script.project_id == project_id,
            Script.episode_number == episode_number
        ).order_by(Script.created_at.desc())
    )
    scripts = result.scalars().all()

    return [
        ScriptHistoryItem(
            script_id=str(s.id),
            episode_number=s.episode_number,
            title=s.title or f"第{s.episode_number}集",
            word_count=s.word_count or 0,
            scene_count=s.scene_count or 0,
            qa_status=s.qa_status,
            qa_score=s.qa_score,
            is_current=s.is_current,
            created_at=s.created_at.isoformat() if s.created_at else ""
        )
        for s in scripts
    ]


@router.get("/{script_id}/detail")
async def get_script_detail(
    script_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取指定剧本的完整数据"""
    result = await db.execute(
        select(Script).join(Project).where(
            Script.id == script_id,
            Project.user_id == current_user.id
        )
    )
    script = result.scalar_one_or_none()

    if not script:
        raise HTTPException(status_code=404, detail="剧本不存在")

    return {
        "script_id": str(script.id),
        "project_id": str(script.project_id),
        "batch_id": str(script.batch_id) if script.batch_id else None,
        "plot_breakdown_id": str(script.plot_breakdown_id) if script.plot_breakdown_id else None,
        "episode_number": script.episode_number,
        "title": script.title,
        "content": script.content,
        "word_count": script.word_count,
        "scene_count": script.scene_count,
        "status": script.status,
        "qa_status": script.qa_status,
        "qa_score": script.qa_score,
        "qa_report": script.qa_report,
        "is_current": script.is_current,
        "created_at": script.created_at.isoformat() if script.created_at else None
    }


# ==================== 单集剧本 API ====================

@router.post("/episode/start")
async def start_episode_script(
    request: EpisodeScriptStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """启动单集剧本生成"""
    # 验证拆解结果存在且属于当前用户
    result = await db.execute(
        select(PlotBreakdown).join(Batch).join(Project).where(
            PlotBreakdown.id == request.breakdown_id,
            Project.user_id == current_user.id
        )
    )
    breakdown = result.scalar_one_or_none()

    if not breakdown:
        raise HTTPException(status_code=404, detail="拆解结果不存在")

    # 验证集数存在于 plot_points 中
    if breakdown.plot_points:
        episode_exists = any(
            pp.get("episode") == request.episode_number
            for pp in breakdown.plot_points
        )
        if not episode_exists:
            raise HTTPException(status_code=400, detail=f"第 {request.episode_number} 集不存在")

    # 获取项目信息
    project_result = await db.execute(select(Project).where(Project.id == breakdown.project_id))
    project = project_result.scalar_one_or_none()

    # 检查积分（纯积分制）
    quota_service = QuotaService(db)
    credits_check = await quota_service.check_credits(current_user, "script")
    if not credits_check["allowed"]:
        raise HTTPException(status_code=403, detail=f"积分不足: 需要 {credits_check['cost']}，余额 {credits_check['balance']}")

    # 预扣积分（与剧集拆解一致）
    consume_result = await quota_service.consume_credits(current_user, "script", "剧本生成")
    if not consume_result:
        raise HTTPException(status_code=403, detail="积分预扣失败，请重试")

    # 创建任务
    task_config = {
        "model_config_id": request.model_config_id or (str(project.script_model_id) if project.script_model_id else None),
        "breakdown_id": str(breakdown.id),
        "episode_number": request.episode_number,
        "novel_type": request.novel_type or project.novel_type
    }

    task = AITask(
        project_id=breakdown.project_id,
        batch_id=breakdown.batch_id,
        task_type=TaskType.EPISODE_SCRIPT,
        status=TaskStatus.QUEUED,
        depends_on=[],
        config=task_config
    )
    db.add(task)
    await db.flush()

    # 启动 Celery 任务
    from app.tasks.script_tasks import run_episode_script_task
    celery_task = run_episode_script_task.delay(
        str(task.id),
        str(breakdown.id),
        request.episode_number,
        str(breakdown.project_id),
        str(current_user.id)
    )
    task.celery_task_id = celery_task.id
    await db.commit()

    return {"task_id": str(task.id), "status": TaskStatus.QUEUED, "episode_number": request.episode_number}


@router.get("/tasks")
async def get_project_script_tasks(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目的所有剧本任务（包括正在运行的）

    用于页面重新加载时恢复任务状态
    """
    # 验证项目归属
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 查询项目的所有剧本生成任务
    result = await db.execute(
        select(AITask).where(
            AITask.project_id == project_id,
            AITask.task_type == TaskType.EPISODE_SCRIPT  # 与创建任务时的 task_type 一致
        ).order_by(AITask.created_at.desc())
    )
    tasks = result.scalars().all()

    # 返回任务列表
    return [
        {
            "id": str(task.id),
            "status": task.status,
            # 优先从 config 获取（任务运行中），其次从 result 获取（任务完成后）
            "episode_number": (task.config.get("episode_number") if task.config else None) or (task.result.get("episode_number") if task.result else None),
            "progress": task.progress or 0,
            "current_step": task.current_step,
            "created_at": task.created_at.isoformat() if task.created_at else None
        }
        for task in tasks
    ]


@router.get("/tasks/{task_id}")
async def get_script_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取剧本任务状态"""
    result = await db.execute(
        select(AITask).join(Project).where(
            AITask.id == task_id,
            Project.user_id == current_user.id
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 动态生成人性化错误信息（参考 breakdown.py）
    error_display = None
    if task.error_message:
        error_display = _humanize_error_message(task.error_message)

    return {
        "task_id": str(task.id),
        "status": task.status,
        "progress": task.progress or 0,
        "current_step": task.current_step,
        "error_message": task.error_message,
        "error_display": error_display,
        "result": task.result
    }


@router.post("/tasks/{task_id}/stop")
async def stop_script_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """停止剧本生成任务

    功能：
    - 使用 Celery revoke 停止正在执行的任务
    - 更新任务状态为 canceled
    - 返还已扣除的积分
    """
    from app.core.celery_app import celery_app
    from app.models.billing import BillingRecord
    from app.core.quota import DEFAULT_CREDITS_PRICING

    # 验证任务归属
    result = await db.execute(
        select(AITask).join(Project).where(
            AITask.id == task_id,
            Project.user_id == current_user.id
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 只有正在执行的任务可以停止
    if task.status not in [TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.RETRYING, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只有正在执行的任务可以停止，当前状态: {task.status}"
        )

    try:
        # 1. 使用 Celery revoke 停止任务
        if task.celery_task_id:
            celery_app.control.revoke(task.celery_task_id, terminate=True)

        # 2. 更新任务状态
        task.status = TaskStatus.CANCELED
        task.current_step = "已停止"
        task.result = {"api_handled_credits": True}

        # 3. 返还积分
        refund_amount = DEFAULT_CREDITS_PRICING.get("script", 50)
        current_user.credits += refund_amount

        # 记录账单
        record = BillingRecord(
            user_id=current_user.id,
            type="refund",
            credits=refund_amount,
            balance_after=current_user.credits,
            description="剧本生成任务取消返还",
            created_at=datetime.now(timezone.utc)
        )
        db.add(record)

        await db.commit()

        return {
            "task_id": str(task.id),
            "status": TaskStatus.CANCELED,
            "message": "任务已停止",
            "refunded_credits": refund_amount
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止任务失败: {str(e)}"
        )


@router.get("/episode/{breakdown_id}/{episode_number}")
async def get_episode_script(
    breakdown_id: str,
    episode_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取单集剧本"""
    result = await db.execute(
        select(Script).join(Project).where(
            Script.plot_breakdown_id == breakdown_id,
            Script.episode_number == episode_number,
            Script.is_current.is_(True),  # 只获取当前版本
            Project.user_id == current_user.id
        )
    )
    script = result.scalar_one_or_none()

    if not script:
        raise HTTPException(status_code=404, detail="剧本不存在")

    return {
        "id": str(script.id),
        "episode_number": script.episode_number,
        "title": script.title,
        "word_count": script.word_count,
        "structure": script.content.get("structure") if script.content else None,
        "full_script": script.content.get("full_script") if script.content else None,
        "scenes": script.content.get("scenes", []) if script.content else [],
        "characters": script.content.get("characters", []) if script.content else [],
        "hook_type": script.content.get("hook_type") if script.content else None,
        "status": script.status,
        "qa_status": script.qa_status,
        "qa_score": script.qa_score,
        "qa_report": script.qa_report,
        "created_at": script.created_at.isoformat() if script.created_at else None
    }


@router.get("/episodes/{breakdown_id}")
async def list_episode_scripts(
    breakdown_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取拆解下所有剧本列表"""
    result = await db.execute(
        select(Script).join(Project).where(
            Script.plot_breakdown_id == breakdown_id,
            Project.user_id == current_user.id
        ).order_by(Script.episode_number)
    )
    scripts = result.scalars().all()

    return {
        "items": [
            {
                "id": str(s.id),
                "episode_number": s.episode_number,
                "title": s.title,
                "word_count": s.word_count,
                "status": s.status,
                "qa_status": s.qa_status,
                "qa_score": s.qa_score,
                "created_at": s.created_at.isoformat() if s.created_at else None
            }
            for s in scripts
        ],
        "total": len(scripts)
    }


@router.post("/batch/start")
async def start_batch_scripts(
    request: BatchScriptStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量生成剧本"""
    # 验证拆解结果
    result = await db.execute(
        select(PlotBreakdown).join(Batch).join(Project).where(
            PlotBreakdown.id == request.breakdown_id,
            Project.user_id == current_user.id
        )
    )
    breakdown = result.scalar_one_or_none()

    if not breakdown:
        raise HTTPException(status_code=404, detail="拆解结果不存在")

    project_result = await db.execute(select(Project).where(Project.id == breakdown.project_id))
    project = project_result.scalar_one_or_none()

    # 检查积分（纯积分制）
    quota_service = QuotaService(db)
    credits_check = await quota_service.check_credits(current_user, "script")
    required = len(request.episode_numbers)
    required_credits = required * credits_check["cost"]  # 使用统一定价

    if credits_check["balance"] < required_credits:
        raise HTTPException(status_code=403, detail=f"积分不足: 需要 {required_credits}，余额 {credits_check['balance']}")

    # 预扣积分（与剧集拆解一致）
    for _ in range(required):
        consume_result = await quota_service.consume_credits(current_user, "script", "剧本生成")
        if not consume_result:
            raise HTTPException(status_code=403, detail="积分预扣失败，请重试")

    task_ids = []
    from app.tasks.script_tasks import run_episode_script_task

    for ep_num in request.episode_numbers:
        task = AITask(
            project_id=breakdown.project_id,
            batch_id=breakdown.batch_id,
            task_type=TaskType.EPISODE_SCRIPT,
            status=TaskStatus.QUEUED,
            config={
                "model_config_id": request.model_config_id or (str(project.script_model_id) if project.script_model_id else None),
                "breakdown_id": str(breakdown.id),
                "episode_number": ep_num,
                "novel_type": request.novel_type or project.novel_type
            }
        )
        db.add(task)
        await db.flush()

        celery_task = run_episode_script_task.delay(
            str(task.id), str(breakdown.id), ep_num, str(breakdown.project_id), str(current_user.id)
        )
        task.celery_task_id = celery_task.id
        task_ids.append(str(task.id))

    await db.commit()
    return {"task_ids": task_ids, "total": len(task_ids)}


# ==================== 剧本编辑和审核 API ====================

@router.put("/{script_id}")
async def update_script(
    script_id: str,
    request: ScriptUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新剧本"""
    result = await db.execute(
        select(Script).join(Project).where(
            Script.id == script_id,
            Project.user_id == current_user.id
        )
    )
    script = result.scalar_one_or_none()

    if not script:
        raise HTTPException(status_code=404, detail="剧本不存在")

    if request.title is not None:
        script.title = request.title
    if request.content is not None:
        script.content = request.content
        script.word_count = len(request.content.get("full_script", ""))
    if request.full_script is not None:
        if script.content is None:
            script.content = {}
        script.content["full_script"] = request.full_script
        script.word_count = len(request.full_script)

    # 显式标记 JSONB 字段已修改
    if request.content is not None or request.full_script is not None:
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(script, 'content')

    script.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "更新成功", "script_id": script_id}


@router.post("/{script_id}/approve")
async def approve_script(
    script_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """审核通过剧本"""
    result = await db.execute(
        select(Script).join(Project).where(
            Script.id == script_id,
            Project.user_id == current_user.id
        )
    )
    script = result.scalar_one_or_none()

    if not script:
        raise HTTPException(status_code=404, detail="剧本不存在")

    script.status = "approved"
    script.approved_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "审核通过", "script_id": script_id, "status": "approved"}


# ==================== 通用剧本查询 API ====================
# 注意：此路由必须放在最后，因为 {script_id} 是通配符，会匹配所有路径

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

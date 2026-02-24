from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field, field_serializer, model_validator
from typing import Optional, List
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
from app.core.quota import QuotaService
from app.core.status import TaskStatus

router = APIRouter()


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
        task_type="episode_script",
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

    return {
        "task_id": str(task.id),
        "status": task.status,
        "progress": task.progress or 0,
        "current_step": task.current_step,
        "error_message": task.error_message,
        "result": task.result
    }


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
            task_type="episode_script",
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

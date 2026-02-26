"""用户反馈 API"""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.api.v1.admin import check_admin
from app.models.user import User
from app.models.feedback import Feedback

router = APIRouter()


# ==================== Pydantic 模型 ====================

class FeedbackCreate(BaseModel):
    """创建反馈请求"""
    type: str = Field(..., pattern="^(suggestion|bug|other)$")
    content: str = Field(..., min_length=1, max_length=5000)
    contact: Optional[str] = Field(None, max_length=255)


class FeedbackUpdate(BaseModel):
    """更新反馈请求（管理端）"""
    status: Optional[str] = Field(None, pattern="^(pending|processing|resolved|closed)$")
    admin_note: Optional[str] = Field(None, max_length=2000)


class FeedbackResponse(BaseModel):
    """反馈响应"""
    id: str
    user_id: str
    username: Optional[str] = None
    type: str
    content: str
    contact: Optional[str]
    status: str
    admin_note: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedFeedbacksResponse(BaseModel):
    """分页反馈列表响应"""
    items: List[FeedbackResponse]
    total: int
    page: int
    page_size: int


# ==================== 用户端 API ====================

@router.post("/feedback", response_model=FeedbackResponse)
async def create_feedback(
    data: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交反馈（用户端）"""
    feedback = Feedback(
        user_id=current_user.id,
        type=data.type,
        content=data.content,
        contact=data.contact,
    )

    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    return FeedbackResponse(
        id=str(feedback.id),
        user_id=str(feedback.user_id),
        username=current_user.username,
        type=feedback.type,
        content=feedback.content,
        contact=feedback.contact,
        status=feedback.status,
        admin_note=feedback.admin_note,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )


# ==================== 管理端 API ====================

@router.get("/admin/feedbacks", response_model=PaginatedFeedbacksResponse)
async def get_admin_feedbacks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None, pattern="^(suggestion|bug|other)$"),
    status: Optional[str] = Query(None, pattern="^(pending|processing|resolved|closed)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    """获取反馈列表（管理端）"""
    conditions = []

    if type:
        conditions.append(Feedback.type == type)
    if status:
        conditions.append(Feedback.status == status)

    # 查询总数
    count_stmt = select(func.count(Feedback.id))
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total = await db.scalar(count_stmt)

    # 查询列表并关联用户名
    stmt = (
        select(Feedback, User.username)
        .outerjoin(User, Feedback.user_id == User.id)
        .order_by(Feedback.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if conditions:
        stmt = stmt.where(and_(*conditions))

    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for feedback, username in rows:
        items.append(FeedbackResponse(
            id=str(feedback.id),
            user_id=str(feedback.user_id),
            username=username,
            type=feedback.type,
            content=feedback.content,
            contact=feedback.contact,
            status=feedback.status,
            admin_note=feedback.admin_note,
            created_at=feedback.created_at,
            updated_at=feedback.updated_at,
        ))

    return PaginatedFeedbacksResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/feedbacks/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback_detail(
    feedback_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    """获取反馈详情（管理端）"""
    stmt = (
        select(Feedback, User.username)
        .outerjoin(User, Feedback.user_id == User.id)
        .where(Feedback.id == feedback_id)
    )
    result = await db.execute(stmt)
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="反馈不存在")

    feedback, username = row

    return FeedbackResponse(
        id=str(feedback.id),
        user_id=str(feedback.user_id),
        username=username,
        type=feedback.type,
        content=feedback.content,
        contact=feedback.contact,
        status=feedback.status,
        admin_note=feedback.admin_note,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )


@router.patch("/admin/feedbacks/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: UUID,
    data: FeedbackUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    """更新反馈状态/备注（管理端）"""
    stmt = select(Feedback).where(Feedback.id == feedback_id)
    result = await db.execute(stmt)
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")

    if data.status is not None:
        feedback.status = data.status
    if data.admin_note is not None:
        feedback.admin_note = data.admin_note

    feedback.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(feedback)

    # 获取用户名
    user_stmt = select(User.username).where(User.id == feedback.user_id)
    username = await db.scalar(user_stmt)

    return FeedbackResponse(
        id=str(feedback.id),
        user_id=str(feedback.user_id),
        username=username,
        type=feedback.type,
        content=feedback.content,
        contact=feedback.contact,
        status=feedback.status,
        admin_note=feedback.admin_note,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )

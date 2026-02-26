"""通知公告 API"""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.api.v1.admin import check_admin
from app.models.user import User
from app.models.announcement import Announcement, AnnouncementRead

router = APIRouter()


# ==================== Pydantic 模型 ====================

class AnnouncementCreate(BaseModel):
    """创建通知请求"""
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    priority: str = Field(default="info", pattern="^(info|warning|urgent)$")
    type: str = Field(default="system", pattern="^(system|maintenance|feature|event)$")
    expires_at: Optional[datetime] = None


class AnnouncementUpdate(BaseModel):
    """更新通知请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)
    priority: Optional[str] = Field(None, pattern="^(info|warning|urgent)$")
    type: Optional[str] = Field(None, pattern="^(system|maintenance|feature|event)$")
    expires_at: Optional[datetime] = None


class AnnouncementResponse(BaseModel):
    """通知响应"""
    id: str
    title: str
    content: str
    priority: str
    type: str
    is_published: bool
    published_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_by: str
    target_user_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    read_count: Optional[int] = None
    total_users: Optional[int] = None

    class Config:
        from_attributes = True


class UserAnnouncementResponse(BaseModel):
    """用户端通知响应"""
    id: str
    title: str
    content: str
    priority: str
    type: str
    published_at: datetime
    is_read: bool
    read_at: Optional[datetime]

    class Config:
        from_attributes = True


class UnreadCountResponse(BaseModel):
    """未读数量响应"""
    unread_count: int


class PaginatedAnnouncementsResponse(BaseModel):
    """分页通知列表响应"""
    items: List[AnnouncementResponse]
    total: int
    page: int
    page_size: int


class PaginatedUserAnnouncementsResponse(BaseModel):
    """用户端分页通知列表响应"""
    items: List[UserAnnouncementResponse]
    total: int
    page: int
    page_size: int


# ==================== 管理端 API ====================

@router.get("/admin/announcements", response_model=PaginatedAnnouncementsResponse)
async def get_admin_announcements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    priority: Optional[str] = Query(None, pattern="^(info|warning|urgent)$"),
    type: Optional[str] = Query(None, pattern="^(system|maintenance|feature|event)$"),
    is_published: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    """获取通知列表（管理端）"""
    # 构建查询条件
    conditions = [Announcement.is_deleted.is_(False)]

    if priority:
        conditions.append(Announcement.priority == priority)
    if type:
        conditions.append(Announcement.type == type)
    if is_published is not None:
        conditions.append(Announcement.is_published == is_published)
    if search:
        conditions.append(Announcement.title.ilike(f"%{search}%"))

    # 查询总数
    count_stmt = select(func.count(Announcement.id)).where(and_(*conditions))
    total = await db.scalar(count_stmt)

    # 查询列表
    stmt = (
        select(Announcement)
        .where(and_(*conditions))
        .order_by(Announcement.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    announcements = result.scalars().all()

    # 转换为响应模型
    items = []
    for announcement in announcements:
        item_dict = {
            "id": str(announcement.id),
            "title": announcement.title,
            "content": announcement.content,
            "priority": announcement.priority,
            "type": announcement.type,
            "is_published": announcement.is_published,
            "published_at": announcement.published_at,
            "expires_at": announcement.expires_at,
            "created_by": str(announcement.created_by),
            "target_user_id": str(announcement.target_user_id) if announcement.target_user_id else None,
            "created_at": announcement.created_at,
            "updated_at": announcement.updated_at,
        }
        items.append(AnnouncementResponse(**item_dict))

    return PaginatedAnnouncementsResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("/admin/announcements", response_model=AnnouncementResponse)
async def create_announcement(
    data: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    """创建通知（管理端）"""
    announcement = Announcement(
        title=data.title,
        content=data.content,
        priority=data.priority,
        type=data.type,
        expires_at=data.expires_at,
        created_by=current_user.id,
    )

    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)

    return AnnouncementResponse(
        id=str(announcement.id),
        title=announcement.title,
        content=announcement.content,
        priority=announcement.priority,
        type=announcement.type,
        is_published=announcement.is_published,
        published_at=announcement.published_at,
        expires_at=announcement.expires_at,
        created_by=str(announcement.created_by),
        target_user_id=str(announcement.target_user_id) if announcement.target_user_id else None,
        created_at=announcement.created_at,
        updated_at=announcement.updated_at,
    )


@router.get("/admin/announcements/{announcement_id}", response_model=AnnouncementResponse)
async def get_announcement_detail(
    announcement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    """获取通知详情（管理端）"""
    stmt = select(Announcement).where(
        Announcement.id == announcement_id,
        Announcement.is_deleted .is_(False),
    )
    result = await db.execute(stmt)
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(status_code=404, detail="通知不存在")

    return AnnouncementResponse(
        id=str(announcement.id),
        title=announcement.title,
        content=announcement.content,
        priority=announcement.priority,
        type=announcement.type,
        is_published=announcement.is_published,
        published_at=announcement.published_at,
        expires_at=announcement.expires_at,
        created_by=str(announcement.created_by),
        target_user_id=str(announcement.target_user_id) if announcement.target_user_id else None,
        created_at=announcement.created_at,
        updated_at=announcement.updated_at,
    )


@router.put("/admin/announcements/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: UUID,
    data: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    """更新通知（管理端）"""
    stmt = select(Announcement).where(
        Announcement.id == announcement_id,
        Announcement.is_deleted .is_(False),
    )
    result = await db.execute(stmt)
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(status_code=404, detail="通知不存在")

    # 更新字段
    if data.title is not None:
        announcement.title = data.title
    if data.content is not None:
        announcement.content = data.content
    if data.priority is not None:
        announcement.priority = data.priority
    if data.type is not None:
        announcement.type = data.type
    if data.expires_at is not None:
        announcement.expires_at = data.expires_at

    announcement.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(announcement)

    return AnnouncementResponse(
        id=str(announcement.id),
        title=announcement.title,
        content=announcement.content,
        priority=announcement.priority,
        type=announcement.type,
        is_published=announcement.is_published,
        published_at=announcement.published_at,
        expires_at=announcement.expires_at,
        created_by=str(announcement.created_by),
        target_user_id=str(announcement.target_user_id) if announcement.target_user_id else None,
        created_at=announcement.created_at,
        updated_at=announcement.updated_at,
    )


@router.delete("/admin/announcements/{announcement_id}")
async def delete_announcement(
    announcement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    """删除通知（软删除）（管理端）"""
    stmt = select(Announcement).where(
        Announcement.id == announcement_id,
        Announcement.is_deleted .is_(False),
    )
    result = await db.execute(stmt)
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(status_code=404, detail="通知不存在")

    announcement.is_deleted = True
    announcement.updated_at = datetime.now(timezone.utc)

    await db.commit()

    return {"message": "删除成功"}


@router.post("/admin/announcements/{announcement_id}/publish")
async def publish_announcement(
    announcement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    """发布通知（管理端）"""
    stmt = select(Announcement).where(
        Announcement.id == announcement_id,
        Announcement.is_deleted .is_(False),
    )
    result = await db.execute(stmt)
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(status_code=404, detail="通知不存在")

    announcement.is_published = True
    announcement.published_at = datetime.now(timezone.utc)
    announcement.updated_at = datetime.now(timezone.utc)

    await db.commit()

    return {"message": "发布成功"}


@router.post("/admin/announcements/{announcement_id}/unpublish")
async def unpublish_announcement(
    announcement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    """取消发布通知（管理端）"""
    stmt = select(Announcement).where(
        Announcement.id == announcement_id,
        Announcement.is_deleted .is_(False),
    )
    result = await db.execute(stmt)
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(status_code=404, detail="通知不存在")

    announcement.is_published = False
    announcement.updated_at = datetime.now(timezone.utc)

    await db.commit()

    return {"message": "取消发布成功"}


@router.get("/admin/announcements/{announcement_id}/stats")
async def get_announcement_stats(
    announcement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    """获取通知统计（已读人数）（管理端）"""
    # 检查通知是否存在
    stmt = select(Announcement).where(
        Announcement.id == announcement_id,
        Announcement.is_deleted .is_(False),
    )
    result = await db.execute(stmt)
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(status_code=404, detail="通知不存在")

    # 统计已读人数
    read_count_stmt = select(func.count(AnnouncementRead.id)).where(
        AnnouncementRead.announcement_id == announcement_id
    )
    read_count = await db.scalar(read_count_stmt)

    # 统计总用户数
    total_users_stmt = select(func.count(User.id)).where(User.is_active .is_(True))
    total_users = await db.scalar(total_users_stmt)

    return {
        "announcement_id": str(announcement_id),
        "read_count": read_count or 0,
        "total_users": total_users or 0,
        "read_rate": round((read_count or 0) / (total_users or 1) * 100, 2),
    }


# ==================== 用户端 API ====================

@router.get("/announcements/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取未读数量（用户端）"""
    now = datetime.now(timezone.utc)

    # 统计未读通知数量
    stmt = (
        select(func.count(Announcement.id))
        .outerjoin(
            AnnouncementRead,
            and_(
                AnnouncementRead.announcement_id == Announcement.id,
                AnnouncementRead.user_id == current_user.id,
            ),
        )
        .where(
            Announcement.is_published .is_(True),
            Announcement.is_deleted .is_(False),
            or_(
                Announcement.expires_at.is_(None),
                Announcement.expires_at > now,
            ),
            or_(
                Announcement.target_user_id.is_(None),
                Announcement.target_user_id == current_user.id,
            ),
            AnnouncementRead.id.is_(None),  # 未读
        )
    )

    unread_count = await db.scalar(stmt)

    return UnreadCountResponse(unread_count=unread_count or 0)


@router.get("/announcements", response_model=PaginatedUserAnnouncementsResponse)
async def get_user_announcements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取已发布的通知列表（用户端）"""
    now = datetime.now(timezone.utc)

    # 构建查询条件：已发布、未删除、未过期、全局通知或个人通知
    conditions = [
        Announcement.is_published .is_(True),
        Announcement.is_deleted .is_(False),
        or_(
            Announcement.expires_at.is_(None),
            Announcement.expires_at > now,
        ),
        or_(
            Announcement.target_user_id.is_(None),
            Announcement.target_user_id == current_user.id,
        ),
    ]

    # 查询总数
    count_stmt = select(func.count(Announcement.id)).where(and_(*conditions))
    total = await db.scalar(count_stmt)

    # 查询列表并关联已读状态
    stmt = (
        select(
            Announcement,
            AnnouncementRead.read_at,
        )
        .outerjoin(
            AnnouncementRead,
            and_(
                AnnouncementRead.announcement_id == Announcement.id,
                AnnouncementRead.user_id == current_user.id,
            ),
        )
        .where(and_(*conditions))
        .order_by(Announcement.published_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # 转换为响应模型
    items = []
    for announcement, read_at in rows:
        items.append(UserAnnouncementResponse(
            id=str(announcement.id),
            title=announcement.title,
            content=announcement.content,
            priority=announcement.priority,
            type=announcement.type,
            published_at=announcement.published_at,
            is_read=read_at is not None,
            read_at=read_at,
        ))

    return PaginatedUserAnnouncementsResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/announcements/{announcement_id}", response_model=UserAnnouncementResponse)
async def get_user_announcement_detail(
    announcement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取通知详情（用户端）"""
    now = datetime.now(timezone.utc)

    # 查询通知并关联已读状态
    stmt = (
        select(
            Announcement,
            AnnouncementRead.read_at,
        )
        .outerjoin(
            AnnouncementRead,
            and_(
                AnnouncementRead.announcement_id == Announcement.id,
                AnnouncementRead.user_id == current_user.id,
            ),
        )
        .where(
            Announcement.id == announcement_id,
            Announcement.is_published .is_(True),
            Announcement.is_deleted .is_(False),
            or_(
                Announcement.expires_at.is_(None),
                Announcement.expires_at > now,
            ),
            or_(
                Announcement.target_user_id.is_(None),
                Announcement.target_user_id == current_user.id,
            ),
        )
    )
    result = await db.execute(stmt)
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="通知不存在")

    announcement, read_at = row

    return UserAnnouncementResponse(
        id=str(announcement.id),
        title=announcement.title,
        content=announcement.content,
        priority=announcement.priority,
        type=announcement.type,
        published_at=announcement.published_at,
        is_read=read_at is not None,
        read_at=read_at,
    )


@router.post("/announcements/{announcement_id}/read")
async def mark_announcement_as_read(
    announcement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记通知为已读（用户端）"""
    # 检查通知是否存在且可访问
    now = datetime.now(timezone.utc)
    stmt = select(Announcement).where(
        Announcement.id == announcement_id,
        Announcement.is_published .is_(True),
        Announcement.is_deleted .is_(False),
        or_(
            Announcement.expires_at.is_(None),
            Announcement.expires_at > now,
        ),
        or_(
            Announcement.target_user_id.is_(None),
            Announcement.target_user_id == current_user.id,
        ),
    )
    result = await db.execute(stmt)
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(status_code=404, detail="通知不存在")

    # 使用 INSERT ... ON CONFLICT DO NOTHING 防止重复标记
    insert_stmt = insert(AnnouncementRead).values(
        announcement_id=announcement_id,
        user_id=current_user.id,
        read_at=datetime.now(timezone.utc),
    ).on_conflict_do_nothing(
        index_elements=['announcement_id', 'user_id']
    )

    await db.execute(insert_stmt)
    await db.commit()

    return {"message": "标记成功"}

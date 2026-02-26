"""通知公告模型"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Announcement(Base):
    """通知公告表"""

    __tablename__ = "announcements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 基本信息
    title = Column(String(255), nullable=False, comment="通知标题")
    content = Column(Text, nullable=False, comment="通知内容（支持 Markdown）")

    # 优先级：info(普通), warning(警告), urgent(紧急)
    priority = Column(String(20), nullable=False, default="info", index=True, comment="优先级")

    # 类型：system(系统通知), maintenance(维护公告), feature(新功能), event(活动)
    type = Column(String(50), nullable=False, default="system", index=True, comment="通知类型")

    # 发布状态
    is_published = Column(Boolean, nullable=False, default=False, index=True, comment="是否已发布")
    published_at = Column(TIMESTAMP(timezone=True), nullable=True, comment="发布时间")

    # 过期时间（可选，过期后不再显示）
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True, index=True, comment="过期时间")

    # 软删除
    is_deleted = Column(Boolean, nullable=False, default=False, index=True, comment="是否已删除")

    # 创建者
    created_by = Column(UUID(as_uuid=True), nullable=False, comment="创建者用户ID")

    # 目标用户（系统自动通知专用）
    target_user_id = Column(UUID(as_uuid=True), nullable=True, index=True, comment="目标用户ID（NULL表示全局通知）")

    # 时间戳
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AnnouncementRead(Base):
    """通知已读记录表"""

    __tablename__ = "announcement_reads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 关联字段
    announcement_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="通知ID")
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="用户ID")

    # 已读时间
    read_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), comment="已读时间")

    # 联合唯一索引，防止重复标记
    __table_args__ = (
        Index('idx_announcement_user', 'announcement_id', 'user_id', unique=True),
    )

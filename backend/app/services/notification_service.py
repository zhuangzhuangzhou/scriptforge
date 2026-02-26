"""通知服务模块"""
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.models.announcement import Announcement


class NotificationService:
    """系统通知服务"""

    @staticmethod
    async def create_system_notification(
        db: AsyncSession,
        user_id: str,
        title: str,
        content: str,
        priority: str = "info",
        notification_type: str = "system"
    ):
        """创建系统自动通知（异步版本）

        Args:
            db: 异步数据库会话
            user_id: 目标用户ID
            title: 通知标题
            content: 通知内容
            priority: 优先级 (info/warning/urgent)
            notification_type: 通知类型 (system/maintenance/feature/event)

        Returns:
            Announcement: 创建的通知对象
        """
        notification = Announcement(
            id=uuid.uuid4(),
            title=title,
            content=content,
            priority=priority,
            type=notification_type,
            is_published=True,
            published_at=datetime.now(timezone.utc),
            created_by=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            target_user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification

    @staticmethod
    def create_system_notification_sync(
        db: Session,
        user_id: str,
        title: str,
        content: str,
        priority: str = "info",
        notification_type: str = "system"
    ):
        """创建系统自动通知（同步版本，用于 Celery 任务）

        Args:
            db: 同步数据库会话
            user_id: 目标用户ID
            title: 通知标题
            content: 通知内容
            priority: 优先级 (info/warning/urgent)
            notification_type: 通知类型 (system/maintenance/feature/event)

        Returns:
            Announcement: 创建的通知对象
        """
        notification = Announcement(
            id=uuid.uuid4(),
            title=title,
            content=content,
            priority=priority,
            type=notification_type,
            is_published=True,
            published_at=datetime.now(timezone.utc),
            created_by=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            target_user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    async def create_global_notification(
        db: AsyncSession,
        admin_user_id: str,
        title: str,
        content: str,
        priority: str = "info",
        notification_type: str = "system"
    ):
        """创建全局通知（异步版本）

        Args:
            db: 异步数据库会话
            admin_user_id: 管理员用户ID
            title: 通知标题
            content: 通知内容
            priority: 优先级 (info/warning/urgent)
            notification_type: 通知类型 (system/maintenance/feature/event)

        Returns:
            Announcement: 创建的通知对象
        """
        notification = Announcement(
            id=uuid.uuid4(),
            title=title,
            content=content,
            priority=priority,
            type=notification_type,
            is_published=True,
            published_at=datetime.now(timezone.utc),
            created_by=uuid.UUID(admin_user_id) if isinstance(admin_user_id, str) else admin_user_id,
            target_user_id=None,  # 全局通知
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification

"""用户反馈模型"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Feedback(Base):
    """用户反馈表"""

    __tablename__ = "feedbacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 提交用户
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="提交用户ID")

    # 反馈类型：suggestion(需求建议), bug(问题报告), other(其他)
    type = Column(String(20), nullable=False, default="other", index=True, comment="反馈类型")

    # 反馈内容
    content = Column(Text, nullable=False, comment="反馈内容")

    # 联系方式（选填）
    contact = Column(String(255), nullable=True, comment="联系方式")

    # 处理状态：pending(待处理), processing(处理中), resolved(已完成), closed(已关闭)
    status = Column(String(20), nullable=False, default="pending", index=True, comment="处理状态")

    # 管理员备注
    admin_note = Column(Text, nullable=True, comment="管理员备注")

    # 时间戳
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_feedback_user_created', 'user_id', 'created_at'),
    )

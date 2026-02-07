import uuid
from datetime import datetime
from sqlalchemy import Column, String, TIMESTAMP, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

class AIConfiguration(Base):
    """AI 配置表，用于存储动态 Prompt、适配方法等配置"""

    __tablename__ = "ai_configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    key = Column(String(100), index=True, nullable=False)
    value = Column(JSONB, nullable=False)
    category = Column(String(50), index=True)  # adapt_method, prompt_template, quality_rule
    is_active = Column(Boolean, default=True)
    description = Column(Text)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    user = relationship("User", backref="ai_configurations")

    __table_args__ = (
        UniqueConstraint('user_id', 'key', name='_user_key_uc'),
    )

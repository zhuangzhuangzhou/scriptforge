import uuid
from datetime import datetime
from sqlalchemy import Column, String, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base

class AIConfiguration(Base):
    """AI 配置表，用于存储动态 Prompt、适配方法等配置"""

    __tablename__ = "ai_configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(JSONB, nullable=False)
    description = Column(Text)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

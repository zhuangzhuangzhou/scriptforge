"""AI 模型提供商数据模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class AIModelProvider(Base):
    """AI 模型提供商表

    管理不同的 AI 模型提供商（OpenAI, Anthropic, 阿里云等）
    """
    __tablename__ = "ai_model_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_key = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    provider_type = Column(String(50), nullable=False)
    api_endpoint = Column(Text)
    is_enabled = Column(Boolean, default=True, index=True)
    is_system_default = Column(Boolean, default=False)
    icon_url = Column(Text)
    description = Column(Text)
    config_schema = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    models = relationship("AIModel", back_populates="provider", cascade="all, delete-orphan")
    credentials = relationship("AIModelCredential", back_populates="provider", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AIModelProvider(id={self.id}, provider_key={self.provider_key}, display_name={self.display_name})>"

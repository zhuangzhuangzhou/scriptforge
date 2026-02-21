"""AI 模型数据模型"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, Text, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from decimal import Decimal
from sqlalchemy import DECIMAL
from app.core.database import Base


class AIModel(Base):
    """AI 模型表

    管理具体的 AI 模型（gpt-4, claude-3-opus 等）
    """
    __tablename__ = "ai_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("ai_model_providers.id", ondelete="CASCADE"), nullable=False, index=True)
    model_key = Column(String(100), nullable=False)
    display_name = Column(String(100), nullable=False)
    model_type = Column(String(50))
    is_enabled = Column(Boolean, default=True, index=True)
    is_default = Column(Boolean, default=False, index=True)
    max_tokens = Column(Integer)
    max_input_tokens = Column(Integer)
    max_output_tokens = Column(Integer)
    timeout_seconds = Column(Integer, default=120)
    temperature_default = Column(DECIMAL(3, 2), default=Decimal('0.7'))
    supports_streaming = Column(Boolean, default=True)
    supports_function_calling = Column(Boolean, default=False)
    description = Column(Text)
    config = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关联关系
    provider = relationship("AIModelProvider", back_populates="models")
    pricing_rules = relationship("AIModelPricing", back_populates="model", cascade="all, delete-orphan")

    # 唯一约束：同一提供商下模型标识唯一
    __table_args__ = (
        UniqueConstraint('provider_id', 'model_key', name='_provider_model_uc'),
    )

    def __repr__(self):
        return f"<AIModel(id={self.id}, model_key={self.model_key}, display_name={self.display_name})>"

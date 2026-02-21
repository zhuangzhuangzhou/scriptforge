"""AI 模型计费规则数据模型"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from decimal import Decimal
from sqlalchemy import DECIMAL
from app.core.database import Base


class AIModelPricing(Base):
    """AI 模型计费规则表

    管理不同模型的 Token 计费规则和积分换算
    """
    __tablename__ = "ai_model_pricing"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False, index=True)
    input_credits_per_1k_tokens = Column(DECIMAL(10, 4), nullable=False, default=Decimal('1.0'))
    output_credits_per_1k_tokens = Column(DECIMAL(10, 4), nullable=False, default=Decimal('1.0'))
    min_credits_per_request = Column(DECIMAL(10, 2), default=Decimal('0'))
    effective_from = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    effective_until = Column(TIMESTAMP(timezone=True))
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关联关系
    model = relationship("AIModel", back_populates="pricing_rules")

    def __repr__(self):
        return f"<AIModelPricing(id={self.id}, model_id={self.model_id}, input={self.input_credits_per_1k_tokens}, output={self.output_credits_per_1k_tokens})>"

"""AI 模型凭证数据模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class AIModelCredential(Base):
    """AI 模型凭证表

    安全存储 API Key 等敏感凭证信息
    """
    __tablename__ = "ai_model_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("ai_model_providers.id", ondelete="CASCADE"), nullable=False, index=True)
    credential_name = Column(String(100), nullable=False)
    api_key = Column(Text, nullable=False)  # 明文存储（已移除加密）
    api_secret = Column(Text)  # 明文存储（已移除加密）
    is_active = Column(Boolean, default=True, index=True)
    is_system_default = Column(Boolean, default=False)
    quota_limit = Column(Integer)
    quota_used = Column(Integer, default=0)
    expires_at = Column(TIMESTAMP(timezone=True))
    last_used_at = Column(TIMESTAMP(timezone=True))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    provider = relationship("AIModelProvider", back_populates="credentials")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<AIModelCredential(id={self.id}, credential_name={self.credential_name}, provider_id={self.provider_id})>"

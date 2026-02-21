import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class ModelConfig(Base):
    """模型配置表"""

    __tablename__ = "model_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True)

    config_type = Column(String(50), nullable=False, index=True)  # 'breakdown', 'script'
    model_provider = Column(String(50), nullable=False)  # 'openai', 'anthropic', 'custom'
    model_name = Column(String(100), nullable=False)
    api_key_encrypted = Column(Text)

    parameters = Column(JSONB)  # 模型参数

    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

"""系统模型配置数据模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class SystemModelConfig(Base):
    """系统模型配置表

    存储全局的模型配置参数
    """
    __tablename__ = "system_model_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(JSONB, nullable=False)
    value_type = Column(String(50), nullable=False)
    description = Column(Text)
    is_editable = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SystemModelConfig(id={self.id}, config_key={self.config_key}, value_type={self.value_type})>"

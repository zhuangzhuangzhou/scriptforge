import uuid
from datetime import datetime
from sqlalchemy import Column, String, TIMESTAMP, Text, Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class AIResource(Base):
    """AI 资源文档表 - 存储方法论、输出风格、模板、示例等 Markdown 文档"""

    __tablename__ = "ai_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 基本信息
    name = Column(String(100), nullable=False, index=True)  # 唯一标识
    display_name = Column(String(255), nullable=False)  # 显示名称
    description = Column(Text)  # 描述
    category = Column(String(50), nullable=False, index=True)  # 分类：adapt_method / output_style / template / example

    # 内容（Markdown 格式）
    content = Column(Text, nullable=False)  # Markdown 文档内容

    # 权限
    is_builtin = Column(Boolean, default=False)  # 是否为系统内置
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)  # 创建者（内置为 null）
    visibility = Column(String(20), default='public')  # public / private

    # 状态
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)  # 版本号
    parent_id = Column(UUID(as_uuid=True), ForeignKey("ai_resources.id"), nullable=True)  # 复制来源

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

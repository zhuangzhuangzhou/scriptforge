from sqlalchemy import Column, String, Boolean, JSON, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base


class Skill(Base):
    """Skill模型"""
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(50))  # breakdown, script, analysis等

    # Skill配置
    module_path = Column(String(500), nullable=False)  # Python模块路径
    class_name = Column(String(100), nullable=False)  # 类名
    parameters = Column(JSON)  # Skill参数配置

    # 状态
    is_active = Column(Boolean, default=True)
    is_builtin = Column(Boolean, default=False)  # 是否为内置Skill

    # 权限控制
    visibility = Column(String(20), default='public')  # public(公共), private(私有), shared(协作)
    owner_id = Column(UUID(as_uuid=True), nullable=False)  # 创建者ID
    allowed_users = Column(JSON)  # 允许访问的用户ID列表 ["uuid1", "uuid2"]

    # 元数据
    version = Column(String(20), default="1.0.0")
    author = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

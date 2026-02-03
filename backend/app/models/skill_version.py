from sqlalchemy import Column, String, Boolean, JSON, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base


class SkillVersion(Base):
    """Skill版本模型 - 管理Skills的版本历史"""
    __tablename__ = "skill_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id = Column(UUID(as_uuid=True), nullable=False)  # 对应已有的Skill表
    user_id = Column(UUID(as_uuid=True), nullable=False)  # 版本创建者

    # 权限控制（继承自Skill）
    visibility = Column(String(20), default='public')  # public, private, shared
    owner_id = Column(UUID(as_uuid=True), nullable=False)  # Skill所有者
    allowed_users = Column(JSON)  # 允许访问的用户ID列表

    # 版本信息
    version = Column(String(20), nullable=False)  # 版本号：v1, v2, ...
    version_number = Column(Integer, default=1)  # 数字版本号

    # 代码内容
    code = Column(Text, nullable=False)  # Python代码
    parameters_schema = Column(JSON)  # 参数Schema

    # 元数据
    description = Column(Text)  # 版本描述
    changelog = Column(Text)  # 变更日志

    # 状态
    is_published = Column(Boolean, default=False)  # 是否发布
    is_active = Column(Boolean, default=True)  # 是否当前活跃版本

    # 来源
    source_version_id = Column(UUID(as_uuid=True))  # 来源版本（复制时）

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SkillExecutionLog(Base):
    """Skill执行日志"""
    __tablename__ = "skill_execution_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_version_id = Column(UUID(as_uuid=True), nullable=False)
    execution_id = Column(UUID(as_uuid=True), nullable=False)

    # 执行信息
    input_data = Column(JSON)  # 输入数据
    output_data = Column(JSON)  # 输出数据
    execution_time = Column(Integer)  # 执行时间（毫秒）

    # 状态
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DECIMAL, TIMESTAMP, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    avatar_url = Column(String(500))
    role = Column(String(20), nullable=False, default="user")

    # 用户等级: free(免费版), creator(创作者版), studio(工作室版), enterprise(企业版)
    tier = Column(String(20), nullable=False, default="free", index=True)

    # 算力积分余额
    credits = Column(Integer, default=0)

    # 每月产出配额（根据等级自动设置）
    monthly_episodes_used = Column(Integer, default=0)  # 本月已使用的剧集数
    monthly_reset_at = Column(TIMESTAMP(timezone=True))  # 配额重置时间

    # 用户自定义 API Key 配置（企业版）
    api_keys = Column(JSON)  # {"openai": "sk-xxx", "claude": "sk-xxx"}

    balance = Column(DECIMAL(10, 2), default=0.00)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(TIMESTAMP(timezone=True))

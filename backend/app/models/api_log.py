import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, ForeignKey, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class APILog(Base):
    """API 请求日志表"""

    __tablename__ = "api_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 请求信息
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE
    path = Column(String(500), nullable=False)   # 请求路径
    query_params = Column(Text)                  # 查询参数
    request_body = Column(Text)                  # 请求体

    # 用户信息
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_ip = Column(String(50))                 # 客户端 IP
    user_agent = Column(String(500))             # User-Agent

    # 响应信息
    status_code = Column(Integer, nullable=False)
    response_body = Column(Text)                 # 响应体
    response_time = Column(Integer)              # 响应时间（毫秒）
    error_message = Column(Text)                 # 错误信息（如果有）

    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index('ix_api_logs_path', 'path'),
        Index('ix_api_logs_user_id', 'user_id'),
        Index('ix_api_logs_status_code', 'status_code'),
    )

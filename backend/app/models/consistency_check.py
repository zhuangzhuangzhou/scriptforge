import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from app.core.database import Base


class ConsistencyCheck(Base):
    """一致性检查记录表"""

    __tablename__ = "consistency_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=True, index=True)

    # 检查类型: character(角色一致性), plot(剧情一致性), timeline(时间线), setting(场景设定)
    check_type = Column(String(50), nullable=False, index=True)

    # 状态: pending, running, completed, failed
    status = Column(String(20), nullable=False, default="pending", index=True)

    # 检查结果 (JSON格式)
    results = Column(JSON)

    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

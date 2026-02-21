import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class AITask(Base):
    """AI任务表"""

    __tablename__ = "ai_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"), index=True)

    task_type = Column(String(50), nullable=False)  # 'breakdown', 'script', 'consistency_check'
    status = Column(String(50), nullable=False, default="queued", index=True)
    progress = Column(Integer, default=0)  # 0-100
    current_step = Column(String(100))
    retry_count = Column(Integer, default=0)
    depends_on = Column(JSONB, default=list)

    config = Column(JSONB, nullable=False)
    result = Column(JSONB)
    error_message = Column(Text)

    celery_task_id = Column(String(255), index=True)

    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

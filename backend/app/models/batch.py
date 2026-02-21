import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Batch(Base):
    """批次表"""

    __tablename__ = "batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_number = Column(Integer, nullable=False)
    start_chapter = Column(Integer, nullable=False)
    end_chapter = Column(Integer, nullable=False)
    total_chapters = Column(Integer, nullable=False)
    total_words = Column(Integer, default=0)

    # 处理状态
    breakdown_status = Column(String(50), default="pending", index=True)
    script_status = Column(String(50), default="pending")
    
    # 新增 AI 处理字段
    ai_processed = Column(Boolean, default=False)
    context_size = Column(Integer, default=10)  # 该批次推荐的上下文大小
    
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

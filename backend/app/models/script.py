import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class Script(Base):
    """剧本表"""

    __tablename__ = "scripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    plot_breakdown_id = Column(UUID(as_uuid=True), ForeignKey("plot_breakdowns.id"), index=True)

    episode_number = Column(Integer, nullable=False)
    title = Column(String(255))
    content = Column(JSONB, nullable=False)
    format_version = Column(String(20), default="1.0")
    word_count = Column(Integer, default=0)
    scene_count = Column(Integer, default=0)

    # 状态字段
    status = Column(String(50), default="draft")  # draft, approved
    qa_status = Column(String(50))  # pass, fail
    qa_score = Column(Integer)  # 质检分数 0-100
    qa_report = Column(JSONB)  # 质检报告详情

    is_current = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    approved_at = Column(TIMESTAMP(timezone=True))  # 审核通过时间

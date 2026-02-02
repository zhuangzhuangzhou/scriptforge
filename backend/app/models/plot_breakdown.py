import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class PlotBreakdown(Base):
    """剧情拆解表"""

    __tablename__ = "plot_breakdowns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # 拆解结果
    conflicts = Column(JSONB)
    plot_hooks = Column(JSONB)
    characters = Column(JSONB)
    scenes = Column(JSONB)
    emotions = Column(JSONB)

    # 一致性检查
    consistency_status = Column(String(50), default="pending", index=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

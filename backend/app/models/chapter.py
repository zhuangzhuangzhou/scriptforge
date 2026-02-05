import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class Chapter(Base):
    """章节表"""

    __tablename__ = "chapters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"), index=True)
    chapter_number = Column(Integer, nullable=False)
    title = Column(String(255))
    content = Column(Text, nullable=False)
    word_count = Column(Integer, default=0)
    
    # 新增存储与处理字段
    txt_file_path = Column(String(500))  # MinIO 路径
    txt_file_size = Column(Integer)       # 文件大小
    skill_processed = Column(JSONB)       # Skill 处理后的结构化数据快照
    
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, BigInteger, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class Project(Base):
    """项目表"""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    novel_type = Column(String(50))
    description = Column(Text)

    # 文件信息
    original_file_path = Column(String(500))
    original_file_name = Column(String(255))
    original_file_size = Column(BigInteger)
    original_file_type = Column(String(50))

    # 批次配置
    batch_size = Column(Integer, nullable=False, default=5)
    chapter_split_rule = Column(JSONB)

    # 统计信息
    total_chapters = Column(Integer, default=0)
    total_words = Column(Integer, default=0)
    processed_chapters = Column(Integer, default=0)

    # 状态
    status = Column(String(50), nullable=False, default="draft", index=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

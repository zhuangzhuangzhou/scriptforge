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
    # draft: 草稿 (初始)
    # uploaded: 已上传 (文件已存储)
    # ready: 已就绪 (章节已拆分)
    # parsing: 拆解中 (剧情分析进行中)
    # scripting: 剧本生成中
    # completed: 已完成
    status = Column(String(50), nullable=False, default="draft", index=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectLog(Base):
    """项目日志表"""

    __tablename__ = "project_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    type = Column(String(50), nullable=False)  # 'info', 'success', 'warning', 'error', 'thinking'
    message = Column(Text, nullable=False)
    detail = Column(JSONB)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

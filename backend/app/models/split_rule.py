import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class SplitRule(Base):
    """小说章节拆分规则表"""

    __tablename__ = "split_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)  # 内部标识，如 standard_chinese
    display_name = Column(String(255), nullable=False)  # 显示名称，如 "中文 - 第N章"
    pattern = Column(Text, nullable=False)  # 正则表达式
    pattern_type = Column(String(50), default="regex")  # 模式类型
    example = Column(Text)  # 示例文字
    
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

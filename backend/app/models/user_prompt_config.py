"""用户提示词配置模型

存储用户对剧情拆解各步骤的提示词选择。
支持项目级配置（project_id 非空）和全局配置（project_id 为空）。
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserPromptConfig(Base):
    """用户提示词配置表"""

    __tablename__ = "user_prompt_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)

    # 各步骤的提示词资源 ID（null = 使用系统默认）
    conflict_prompt_id = Column(UUID(as_uuid=True), ForeignKey("ai_resources.id"), nullable=True)
    character_prompt_id = Column(UUID(as_uuid=True), ForeignKey("ai_resources.id"), nullable=True)
    scene_prompt_id = Column(UUID(as_uuid=True), ForeignKey("ai_resources.id"), nullable=True)
    emotion_prompt_id = Column(UUID(as_uuid=True), ForeignKey("ai_resources.id"), nullable=True)
    plot_hook_prompt_id = Column(UUID(as_uuid=True), ForeignKey("ai_resources.id"), nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关系
    user = relationship("User", backref="prompt_configs")
    project = relationship("Project", backref="prompt_config")
    conflict_prompt = relationship("AIResource", foreign_keys=[conflict_prompt_id])
    character_prompt = relationship("AIResource", foreign_keys=[character_prompt_id])
    scene_prompt = relationship("AIResource", foreign_keys=[scene_prompt_id])
    emotion_prompt = relationship("AIResource", foreign_keys=[emotion_prompt_id])
    plot_hook_prompt = relationship("AIResource", foreign_keys=[plot_hook_prompt_id])

    __table_args__ = (
        # 每个用户每个项目只能有一个配置（project_id 为 null 时表示全局配置）
        UniqueConstraint('user_id', 'project_id', name='uq_user_project_prompt_config'),
    )

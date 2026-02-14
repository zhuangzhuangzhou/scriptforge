import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class PlotBreakdown(Base):
    """剧情拆解表"""

    __tablename__ = "plot_breakdowns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # 数据分析关联字段
    task_id = Column(UUID(as_uuid=True), ForeignKey("ai_tasks.id", ondelete="SET NULL"), index=True)  # 关联的任务
    ai_model_id = Column(UUID(as_uuid=True), ForeignKey("ai_models.id", ondelete="SET NULL"), index=True)  # 使用的 AI 模型（来自 ai_models 表）
    model_config_id = Column(UUID(as_uuid=True), ForeignKey("model_configs.id", ondelete="SET NULL"), index=True)  # 模型配置 ID（来自 model_configs 表）

    # 拆解结果
    conflicts = Column(JSONB)
    plot_hooks = Column(JSONB)
    characters = Column(JSONB)
    scenes = Column(JSONB)
    emotions = Column(JSONB)
    episodes = Column(JSONB)  # 剧集规划结果

    # 统一剧情点格式
    plot_points = Column(JSONB)  # 统一格式的剧情点列表
    format_version = Column(Integer, default=1)  # 1=旧6字段格式, 2=新统一格式
    qa_score = Column(Integer)  # 质检分数
    qa_retry_count = Column(Integer, default=0)  # 质检重试次数

    # 一致性检查
    consistency_status = Column(String(50), default="pending", index=True)
    consistency_score = Column(Integer)
    consistency_results = Column(JSONB)

    # OWR 质检相关
    qa_status = Column(String(50), default="pending", index=True)
    qa_report = Column(JSONB)
    used_adapt_method_id = Column(String(100))

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

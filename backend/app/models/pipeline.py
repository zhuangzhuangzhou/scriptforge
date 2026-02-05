from sqlalchemy import Column, String, Boolean, JSON, DateTime, ForeignKey, Text, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
from app.core.database import Base


class Pipeline(Base):
    """Pipeline模型 - 定义剧本生成的流水线"""
    __tablename__ = "pipelines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    # Pipeline信息
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Pipeline配置
    config = Column(JSON)  # Pipeline整体配置
    stages_config = Column(JSON)  # 各阶段配置

    # 状态
    is_default = Column(Boolean, default=False)  # 是否为默认Pipeline
    is_active = Column(Boolean, default=True)

    # 版本管理
    version = Column(Integer, default=1)
    parent_pipeline_id = Column(UUID(as_uuid=True))  # 父Pipeline ID（用于分支）

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PipelineStage(Base):
    """PipelineStage模型 - Pipeline的阶段定义"""
    __tablename__ = "pipeline_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False)

    # Stage信息
    name = Column(String(100), nullable=False)  # 阶段名称：breakdown, script
    display_name = Column(String(255), nullable=False)  # 显示名称
    description = Column(Text)

    # Skills配置
    skills = Column(JSON)  # 该阶段执行的Skills列表
    skills_order = Column(JSON)  # Skills执行顺序

    # 执行配置
    config = Column(JSON)  # 执行参数配置
    input_mapping = Column(JSON)  # 输入映射
    output_mapping = Column(JSON)  # 输出映射

    # 执行顺序
    order = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PipelineExecution(Base):
    """Pipeline执行记录"""
    __tablename__ = "pipeline_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))

    # 执行状态
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    current_stage = Column(String(100))  # 当前执行的阶段

    # 执行进度
    progress = Column(Integer, default=0)  # 0-100
    current_step = Column(String(100))  # 当前步骤

    # 结果
    result = Column(JSON)  # 执行结果
    error_message = Column(Text)  # 错误信息

    # Celery任务ID
    celery_task_id = Column(String(255))

    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class PipelineExecutionLog(Base):
    """Pipeline执行日志"""
    __tablename__ = "pipeline_execution_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_executions.id", ondelete="CASCADE"), index=True, nullable=False)

    stage = Column(String(100))          # breakdown/script/...
    event = Column(String(100))          # stage_start/stage_completed/validator_result/error
    message = Column(Text)
    detail = Column(JSONB)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, ForeignKey, TIMESTAMP, Float, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class LLMCallLog(Base):
    """LLM 调用日志表"""

    __tablename__ = "llm_call_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 关联信息
    task_id = Column(UUID(as_uuid=True), ForeignKey("ai_tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)

    # 模型信息
    provider = Column(String(50), nullable=False)  # openai, anthropic, gemini
    model_name = Column(String(100), nullable=False)

    # 调用上下文
    skill_name = Column(String(100))  # 调用的 Skill 名称
    stage = Column(String(100))       # 执行阶段

    # 请求信息
    prompt = Column(Text, nullable=False)          # 完整 prompt
    prompt_tokens = Column(Integer)                # prompt token 数
    temperature = Column(Float)
    max_tokens = Column(Integer)

    # 响应信息
    response = Column(Text)                        # 完整响应内容
    response_tokens = Column(Integer)              # 响应 token 数
    total_tokens = Column(Integer)                 # 总 token 数

    # 执行信息
    status = Column(String(20), nullable=False, default="success")  # success, error
    error_message = Column(Text)
    latency_ms = Column(Integer)                   # 响应延迟（毫秒）

    # 额外元数据
    extra_metadata = Column(JSONB)                 # 其他信息（如 function_call 等）

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('ix_llm_call_logs_provider', 'provider'),
        Index('ix_llm_call_logs_model_name', 'model_name'),
        Index('ix_llm_call_logs_skill_name', 'skill_name'),
    )

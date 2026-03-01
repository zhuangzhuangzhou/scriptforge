import time
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from sqlalchemy.orm import Session
from app.models.llm_call_log import LLMCallLog
from uuid import UUID

logger = logging.getLogger(__name__)


def _safe_uuid(value: Optional[str]) -> Optional[UUID]:
    """安全地将字符串转换为 UUID，如果失败返回 None"""
    if not value:
        return None
    try:
        return UUID(value) if isinstance(value, str) else value
    except (ValueError, AttributeError):
        logger.warning(f"无效的 UUID 格式: {value}")
        return None

# 全局上下文存储（用于传递 task_id, user_id 等）
_call_context: Dict[str, Any] = {}


def set_llm_context(
    task_id: Optional[str] = None,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    skill_name: Optional[str] = None,
    stage: Optional[str] = None
):
    """设置 LLM 调用上下文"""
    global _call_context
    if task_id:
        _call_context["task_id"] = task_id
    if user_id:
        _call_context["user_id"] = user_id
    if project_id:
        _call_context["project_id"] = project_id
    if skill_name:
        _call_context["skill_name"] = skill_name
    if stage:
        _call_context["stage"] = stage


def clear_llm_context():
    """清除 LLM 调用上下文"""
    global _call_context
    _call_context = {}


def get_llm_context() -> Dict[str, Any]:
    """获取当前 LLM 调用上下文"""
    return _call_context.copy()


@contextmanager
def llm_context(
    task_id: Optional[str] = None,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    skill_name: Optional[str] = None,
    stage: Optional[str] = None
):
    """LLM 调用上下文管理器"""
    global _call_context
    old_context = _call_context.copy()
    set_llm_context(task_id, user_id, project_id, skill_name, stage)
    try:
        yield
    finally:
        _call_context = old_context


def log_llm_call(
    db: Session,
    provider: str,
    model_name: str,
    prompt: str,
    response: Optional[str] = None,
    prompt_tokens: Optional[int] = None,
    response_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    latency_ms: Optional[int] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    metadata: Optional[Dict] = None,
    # 上下文覆盖
    task_id: Optional[str] = None,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    ai_model_id: Optional[str] = None,
    skill_name: Optional[str] = None,
    stage: Optional[str] = None
):
    """记录 LLM 调用日志（同步版本）"""
    try:
        ctx = get_llm_context()

        # 将 prompt 存储到 metadata 中（prompt 字段已废弃）
        if metadata is None:
            metadata = {}
        if prompt and "prompt" not in metadata:
            metadata["prompt"] = prompt

        # 安全地转换 UUID
        final_task_id = _safe_uuid(task_id or ctx.get("task_id"))
        final_user_id = _safe_uuid(user_id or ctx.get("user_id"))
        final_project_id = _safe_uuid(project_id or ctx.get("project_id"))
        final_ai_model_id = _safe_uuid(ai_model_id)

        log = LLMCallLog(
            task_id=final_task_id,
            user_id=final_user_id,
            project_id=final_project_id,
            ai_model_id=final_ai_model_id,
            provider=provider,
            model_name=model_name,
            skill_name=skill_name or ctx.get("skill_name"),
            stage=stage or ctx.get("stage"),
            prompt_tokens=prompt_tokens,
            temperature=temperature,
            max_tokens=max_tokens,
            response=response,
            response_tokens=response_tokens,
            total_tokens=(prompt_tokens or 0) + (response_tokens or 0) if prompt_tokens or response_tokens else None,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
            extra_metadata=metadata
        )
        db.add(log)
        db.commit()
        logger.info(f"✅ LLM 日志记录成功: {provider}/{model_name}, status={status}")
        return log
    except Exception as e:
        logger.error(f"❌ 记录 LLM 调用日志失败: {e}", exc_info=True)
        # 注意：不要在这里 rollback，因为可能会影响主业务事务
        # 日志记录失败不应该影响主业务逻辑
        return None


async def log_llm_call_async(
    db,  # AsyncSession
    provider: str,
    model_name: str,
    prompt: str,
    response: Optional[str] = None,
    prompt_tokens: Optional[int] = None,
    response_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    latency_ms: Optional[int] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    metadata: Optional[Dict] = None,
    # 上下文覆盖
    task_id: Optional[str] = None,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    ai_model_id: Optional[str] = None,
    skill_name: Optional[str] = None,
    stage: Optional[str] = None
):
    """记录 LLM 调用日志（异步版本）"""
    try:
        ctx = get_llm_context()

        # 将 prompt 存储到 metadata 中（prompt 字段已废弃）
        if metadata is None:
            metadata = {}
        if prompt and "prompt" not in metadata:
            metadata["prompt"] = prompt

        # 安全地转换 UUID
        final_task_id = _safe_uuid(task_id or ctx.get("task_id"))
        final_user_id = _safe_uuid(user_id or ctx.get("user_id"))
        final_project_id = _safe_uuid(project_id or ctx.get("project_id"))
        final_ai_model_id = _safe_uuid(ai_model_id)

        log = LLMCallLog(
            task_id=final_task_id,
            user_id=final_user_id,
            project_id=final_project_id,
            ai_model_id=final_ai_model_id,
            provider=provider,
            model_name=model_name,
            skill_name=skill_name or ctx.get("skill_name"),
            stage=stage or ctx.get("stage"),
            prompt_tokens=prompt_tokens,
            temperature=temperature,
            max_tokens=max_tokens,
            response=response,
            response_tokens=response_tokens,
            total_tokens=(prompt_tokens or 0) + (response_tokens or 0) if prompt_tokens or response_tokens else None,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
            extra_metadata=metadata
        )
        db.add(log)
        await db.commit()
        logger.info(f"✅ LLM 日志记录成功（异步）: {provider}/{model_name}, status={status}")
        return log
    except Exception as e:
        logger.error(f"❌ 记录 LLM 调用日志失败（异步）: {e}", exc_info=True)
        # 注意：不要在这里 rollback，因为可能会影响主业务事务
        # 日志记录失败不应该影响主业务逻辑
        return None


class LLMCallTimer:
    """LLM 调用计时器"""

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = time.time()

    def stop(self):
        self.end_time = time.time()

    @property
    def latency_ms(self) -> int:
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return 0

import time
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from sqlalchemy.orm import Session
from app.models.llm_call_log import LLMCallLog

logger = logging.getLogger(__name__)

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
    skill_name: Optional[str] = None,
    stage: Optional[str] = None
):
    """记录 LLM 调用日志"""
    try:
        ctx = get_llm_context()

        log = LLMCallLog(
            task_id=task_id or ctx.get("task_id"),
            user_id=user_id or ctx.get("user_id"),
            project_id=project_id or ctx.get("project_id"),
            provider=provider,
            model_name=model_name,
            skill_name=skill_name or ctx.get("skill_name"),
            stage=stage or ctx.get("stage"),
            prompt=prompt,
            prompt_tokens=prompt_tokens,
            temperature=temperature,
            max_tokens=max_tokens,
            response=response,
            response_tokens=response_tokens,
            total_tokens=(prompt_tokens or 0) + (response_tokens or 0) if prompt_tokens or response_tokens else None,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
            metadata=metadata
        )
        db.add(log)
        db.commit()
        return log
    except Exception as e:
        logger.error(f"记录 LLM 调用日志失败: {e}")
        db.rollback()
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

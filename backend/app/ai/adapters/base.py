from abc import ABC, abstractmethod
from typing import Dict, Any, Iterator, Optional
from sqlalchemy.orm import Session


class BaseModelAdapter(ABC):
    """模型适配器基类"""

    # 提供商名称，子类需要覆盖
    provider_name: str = "unknown"

    def __init__(self, api_key: str, model_name: str, **kwargs):
        self.api_key = api_key
        self.model_name = model_name
        self.config = kwargs
        # 可选的数据库会话，用于记录日志
        self._db: Optional[Session] = kwargs.get("db")
        # 是否启用日志记录
        self._log_enabled: bool = kwargs.get("log_enabled", True)

    def set_db(self, db: Session):
        """设置数据库会话"""
        self._db = db

    def enable_logging(self, enabled: bool = True):
        """启用/禁用日志记录"""
        self._log_enabled = enabled

    def _log_call(
        self,
        prompt: str,
        response: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        response_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        latency_ms: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """记录 LLM 调用"""
        if not self._log_enabled or not self._db:
            return

        try:
            from app.ai.llm_logger import log_llm_call
            log_llm_call(
                db=self._db,
                provider=self.provider_name,
                model_name=self.model_name,
                prompt=prompt,
                response=response,
                prompt_tokens=prompt_tokens,
                response_tokens=response_tokens,
                temperature=temperature,
                max_tokens=max_tokens,
                latency_ms=latency_ms,
                status=status,
                error_message=error_message,
                metadata=metadata
            )
        except Exception:
            pass  # 日志记录失败不影响主流程

    @abstractmethod
    def generate(self, prompt: str, return_usage: bool = False, **kwargs) -> Any:
        """
        生成文本
        :param prompt: 提示词
        :param return_usage: 是否返回使用量信息
        :return: 字符串（默认）或包含内容和使用量的字典
        """
        pass

    @abstractmethod
    def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
        """流式生成文本"""
        pass

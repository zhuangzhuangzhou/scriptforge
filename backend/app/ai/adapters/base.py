from abc import ABC, abstractmethod
from typing import Dict, Any, Iterator, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession


class BaseModelAdapter(ABC):
    """模型适配器基类"""

    # 提供商名称，子类需要覆盖
    provider_name: str = "unknown"

    def __init__(self, api_key: str, model_name: str, **kwargs):
        self.api_key = api_key
        self.model_name = model_name
        self.config = kwargs
        # 模型默认配置（max_output_tokens, temperature_default 等）
        self.model_config = kwargs.get("model_config", {})
        # 可选的数据库会话，用于记录日志（支持同步和异步）
        self._db: Optional[Union[Session, AsyncSession]] = kwargs.get("db")
        # 是否启用日志记录
        self._log_enabled: bool = kwargs.get("log_enabled", True)
        # 判断是否为异步会话
        self._is_async_db = isinstance(self._db, AsyncSession) if self._db else False

    def set_db(self, db: Union[Session, AsyncSession]):
        """设置数据库会话"""
        self._db = db
        self._is_async_db = isinstance(db, AsyncSession)

    def enable_logging(self, enabled: bool = True):
        """启用/禁用日志记录"""
        self._log_enabled = enabled

    def _log_call_sync(
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
        """记录 LLM 调用（强制使用同步方式，即使传入的是 AsyncSession）"""
        if not self._log_enabled:
            return

        try:
            from app.ai.llm_logger import log_llm_call
            from app.core.database import SyncSessionLocal

            # 如果传入的是 AsyncSession，创建一个新的同步会话
            if self._is_async_db:
                with SyncSessionLocal() as sync_db:
                    log_llm_call(
                        db=sync_db,
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
            else:
                # 使用传入的同步会话
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
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ _log_call_sync 失败: {e}", exc_info=True)

    async def _log_call_async(
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
        """记录 LLM 调用（异步版本）"""
        if not self._log_enabled or not self._db:
            return

        try:
            from app.ai.llm_logger import log_llm_call_async
            await log_llm_call_async(
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
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ _log_call_async 失败: {e}", exc_info=True)

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

"""AI任务自定义异常类

用于区分不同类型的错误，支持自动重试和友好错误提示。

异常分类：
- RetryableError: 可重试错误（网络超时、API临时不可用等）
- QuotaExceededError: 配额不足错误（不可重试）
- ValidationError: 验证错误（参数校验失败等）
- ConfigurationError: 配置错误（AI配置不存在等）
- AITaskException: 所有AI任务异常的基类
"""

from typing import Optional


class AITaskException(Exception):
    """AI任务基础异常"""

    def __init__(self, message: str, code: str = "TASK_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

    def to_dict(self) -> dict:
        """转换为字典格式，便于JSON序列化"""
        return {
            "code": self.code,
            "message": self.message
        }


class RetryableError(AITaskException):
    """可重试错误（网络超时、API临时不可用等）

    此类错误会被Celery自动重试，支持指数退避策略。
    """

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message, code="RETRYABLE_ERROR")
        self.retry_after = retry_after


class QuotaExceededError(AITaskException):
    """配额不足错误（不可重试）

    用户API配额用尽或已达限额。
    """

    def __init__(self, message: str):
        super().__init__(message, code="QUOTA_EXCEEDED")


class ValidationError(AITaskException):
    """验证错误（参数校验失败等）

    输入参数不符合要求。
    """

    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")


class ConfigurationError(AITaskException):
    """配置错误（AI配置不存在等）

    系统配置问题，如AI配置不存在或格式错误。
    """

    def __init__(self, message: str):
        super().__init__(message, code="CONFIGURATION_ERROR")


class SkillExecutionError(AITaskException):
    """Skill执行错误

    Skill执行过程中发生的错误，如Skill不存在或执行失败。
    """

    def __init__(self, message: str, skill_name: Optional[str] = None):
        super().__init__(message, code="SKILL_EXECUTION_ERROR")
        self.skill_name = skill_name


class PipelineExecutionError(AITaskException):
    """Pipeline执行错误

    Pipeline执行过程中发生的错误。
    """

    def __init__(self, message: str, stage: Optional[str] = None):
        super().__init__(message, code="PIPELINE_EXECUTION_ERROR")
        self.stage = stage


class DatabaseError(AITaskException):
    """数据库错误

    数据库操作失败。
    """

    def __init__(self, message: str):
        super().__init__(message, code="DATABASE_ERROR")


class TokenLimitExceededError(AITaskException):
    """Token 超限错误

    输入或输出超过模型的 Token 限制。
    """

    def __init__(self, message: str, limit: int = None, actual: int = None):
        super().__init__(message, code="TOKEN_LIMIT_EXCEEDED")
        self.limit = limit
        self.actual = actual

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "limit": self.limit,
            "actual": self.actual
        }


# 异常分类辅助函数

def classify_exception(error: Exception) -> AITaskException:
    """根据异常类型分类并返回对应的AITaskException

    Args:
        error: 原始异常对象

    Returns:
        AITaskException: 分类后的异常对象
    """
    # 如果已经是AITaskException，直接返回
    if isinstance(error, AITaskException):
        return error

    # 根据异常类型进行分类
    error_type = type(error).__name__
    error_message = str(error).lower()

    # 网络相关错误 - 可重试
    if error_type in ("TimeoutError", "ConnectionError", "ConnectionRefusedError"):
        return RetryableError(f"网络连接失败: {str(error)}")

    # Token 超限错误 - 不可重试
    token_limit_keywords = [
        "context_length_exceeded",
        "context length",
        "maximum context length",
        "token limit",
        "max_tokens",
        "too many tokens",
        "input is too long",
        "prompt is too long",
        "exceeds the model's maximum",
    ]
    if any(keyword in error_message for keyword in token_limit_keywords):
        return TokenLimitExceededError(
            f"内容超过模型 Token 限制，请减少输入内容或分批处理: {str(error)}"
        )

    # OpenAI/API相关错误 - 可能是配额或可重试
    if "rate_limit" in error_message or "quota" in error_message:
        return QuotaExceededError(f"API配额不足: {str(error)}")

    if "timeout" in error_message:
        return RetryableError(f"API请求超时: {str(error)}")

    # JSON解析错误 - 可能是配置问题
    if isinstance(error, (ValueError, TypeError)):
        return ValidationError(f"数据验证失败: {str(error)}")

    # 数据库错误
    if "sqlalchemy" in error_message or "database" in error_message:
        return DatabaseError(f"数据库操作失败: {str(error)}")

    # 默认返回通用错误
    return AITaskException(f"任务执行失败: {str(error)}")


# 可重试错误的来源标识
RETRYABLE_ERROR_TYPES = (
    TimeoutError,
    ConnectionError,
    ConnectionRefusedError,
    RetryableError,
)

# 不可重试错误的来源标识
NON_RETRYABLE_ERROR_TYPES = (
    QuotaExceededError,
    ValidationError,
    ConfigurationError,
    TokenLimitExceededError,
)

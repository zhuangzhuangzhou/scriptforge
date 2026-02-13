from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "Novel-to-Script System"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    SECRET_KEY: str

    # 数据库配置
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis 配置
    REDIS_URL: str

    # Celery 配置
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # MinIO/S3 配置
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str = "novel-scripts"
    MINIO_SECURE: bool = False

    # JWT 配置
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OpenAI 配置
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4-turbo-preview"

    # Anthropic 配置
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-opus-20240229"

    # 默认模型提供商 (openai 或 anthropic)
    DEFAULT_MODEL_PROVIDER: str = "openai"

    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    ALLOWED_EXTENSIONS: List[str] = ["txt", "docx", "pdf"]

    # CORS 配置
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # API 日志配置
    API_LOG_ENABLED: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

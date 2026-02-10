from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# 创建异步引擎（用于 FastAPI）
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 创建同步引擎（用于 Celery 任务）
# 将 asyncpg 驱动替换为 psycopg2
SYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://",
    "postgresql+psycopg2://"
)

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# 创建同步会话工厂
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

# 创建基类
Base = declarative_base()


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

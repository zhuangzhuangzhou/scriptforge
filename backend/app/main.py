from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from app.core.database import AsyncSessionLocal
# 生产环境暂时禁用启动初始化（datetime 时区冲突问题）
# from app.core.init_skills import init_builtin_skills
# from app.core.init_pipeline import init_default_pipeline
# from app.core.init_simple_system import init_simple_system
# from app.core.init_ai_resources import init_builtin_resources
from app.middleware.api_logging import APILoggingMiddleware
from app.core.status import TaskStatus

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 请求日志中间件
app.add_middleware(APILoggingMiddleware, enabled=settings.API_LOG_ENABLED)

# 注册API路由
app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化（生产环境暂时禁用，避免 datetime 时区问题）"""
    print("应用启动完成（跳过初始化）")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": TaskStatus.RUNNING
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

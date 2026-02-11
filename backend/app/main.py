from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from app.core.database import AsyncSessionLocal
from app.core.init_skills import init_builtin_skills
from app.core.init_pipeline import init_default_pipeline
from app.core.init_simple_system import init_simple_system
from app.core.init_ai_resources import init_builtin_resources

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

# 注册API路由
app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    async with AsyncSessionLocal() as db:
        await init_builtin_skills(db)
        await init_default_pipeline(db)
        await init_simple_system(db)  # 初始化简化系统
        await init_builtin_resources(db)  # 初始化内置 AI 资源文档
        print("应用启动完成")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

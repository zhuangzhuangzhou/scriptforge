from fastapi import APIRouter
from app.api.v1 import auth, projects, breakdown

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(projects.router, prefix="/projects", tags=["项目管理"])
api_router.include_router(breakdown.router, prefix="/breakdown", tags=["剧情拆解"])

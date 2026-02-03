from fastapi import APIRouter
from app.api.v1 import auth, projects, breakdown, scripts, export, admin, websocket, skills_admin, skills_user, pipeline, skills_code, agent_definition

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(projects.router, prefix="/projects", tags=["项目管理"])
api_router.include_router(breakdown.router, prefix="/breakdown", tags=["剧情拆解"])
api_router.include_router(scripts.router, prefix="/scripts", tags=["剧本生成"])
api_router.include_router(export.router, prefix="/export", tags=["导出"])
api_router.include_router(admin.router, prefix="/admin", tags=["管理端"])
api_router.include_router(skills_admin.router, prefix="/admin/skills", tags=["Skills管理"])
api_router.include_router(skills_user.router, prefix="/skills", tags=["用户Skills"])
api_router.include_router(pipeline.router, prefix="/pipelines", tags=["Pipeline"])
api_router.include_router(skills_code.router, prefix="/skills/code", tags=["Skills代码"])
api_router.include_router(agent_definition.router, prefix="/agents", tags=["Agent管理"])
api_router.include_router(websocket.router, tags=["WebSocket"])

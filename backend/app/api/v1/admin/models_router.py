"""模型管理路由

统一管理所有模型相关的 API 路由
"""
from fastapi import APIRouter

# 使用绝对导入避免循环依赖
from app.api.v1.admin.model_providers import router as providers_router
from app.api.v1.admin.models import router as models_router
from app.api.v1.admin.credentials import router as credentials_router
from app.api.v1.admin.pricing import router as pricing_router
from app.api.v1.admin.system_config import router as system_config_router

router = APIRouter()

# 注册子路由
# 注意：路由注册顺序很重要！更具体的路由应该先注册
router.include_router(
    providers_router,
    prefix="/providers",
    tags=["模型提供商管理"]
)

router.include_router(
    credentials_router,
    prefix="/credentials",
    tags=["凭证管理"]
)

router.include_router(
    pricing_router,
    prefix="/pricing",
    tags=["计费规则管理"]
)

router.include_router(
    system_config_router,
    prefix="/system-config",
    tags=["系统配置管理"]
)

# 模型管理路由放在最后，因为它有 /{model_id} 这样的通配路由
router.include_router(
    models_router,
    prefix="/models",
    tags=["模型配置"]
)

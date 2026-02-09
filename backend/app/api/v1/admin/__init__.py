"""管理员 API 模块

提供管理员专用的 API 端点
"""
from fastapi import Depends, HTTPException, APIRouter
from app.models.user import User
from app.api.v1.auth import get_current_user


async def check_admin(current_user: User = Depends(get_current_user)) -> User:
    """验证管理员权限

    Args:
        current_user: 当前登录用户

    Returns:
        User: 管理员用户对象

    Raises:
        HTTPException: 如果用户不是管理员
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="需要管理员权限"
        )
    return current_user


# 创建主路由
router = APIRouter()

# 导入 admin_core.py 的路由（基础功能：用户管理、统计、Pipeline等）
from app.api.v1.admin_core import router as admin_base_router
router.include_router(admin_base_router, tags=["管理端基础功能"])

# 导入并注册模型管理路由
from app.api.v1.admin.models_router import router as models_router
router.include_router(models_router, prefix="/models", tags=["模型管理"])

__all__ = ["check_admin", "router"]

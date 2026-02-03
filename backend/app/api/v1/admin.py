from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user

router = APIRouter()


def check_admin(current_user: User = Depends(get_current_user)):
    """检查是否为管理员"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


class UserUpdateRequest(BaseModel):
    """更新用户请求"""
    is_active: Optional[bool] = None
    role: Optional[str] = None
    balance: Optional[float] = None


@router.get("/users")
async def get_users(
    skip: int = 0,
    limit: int = 20,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取用户列表"""
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()

    # 获取总数
    count_result = await db.execute(select(func.count(User.id)))
    total = count_result.scalar()

    return {
        "users": users,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """更新用户状态"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    if request.is_active is not None:
        user.is_active = request.is_active
    if request.role is not None:
        user.role = request.role
    if request.balance is not None:
        user.balance = request.balance

    await db.commit()
    await db.refresh(user)

    return user


@router.get("/stats")
async def get_system_stats(
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取系统统计信息"""
    from app.models.project import Project
    from app.models.ai_task import AITask

    # 统计用户数
    user_count = await db.execute(select(func.count(User.id)))
    total_users = user_count.scalar()

    # 统计活跃用户数
    active_user_count = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_user_count.scalar()

    # 统计项目数
    project_count = await db.execute(select(func.count(Project.id)))
    total_projects = project_count.scalar()

    # 统计AI任务数
    task_count = await db.execute(select(func.count(AITask.id)))
    total_tasks = task_count.scalar()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_projects": total_projects,
        "total_tasks": total_tasks
    }

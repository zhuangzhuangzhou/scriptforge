from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.models.user import User
from app.models.skill import Skill
from app.models.user_skill_config import UserSkillConfig
from app.api.v1.auth import get_current_user

router = APIRouter()


class UserSkillConfigRequest(BaseModel):
    """用户Skill配置请求"""
    skill_id: str
    project_id: Optional[str] = None
    custom_parameters: Optional[dict] = None
    execution_order: Optional[str] = None


@router.get("/available")
async def get_available_skills(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取可用的Skills列表"""
    query = select(Skill).where(Skill.is_active == True)

    if category:
        query = query.where(Skill.category == category)

    result = await db.execute(query)
    skills = result.scalars().all()

    return {"skills": skills}


@router.post("/config")
async def save_skill_config(
    request: UserSkillConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """保存用户Skill配置"""
    # 验证Skill存在
    result = await db.execute(select(Skill).where(Skill.id == request.skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill不存在"
        )

    config = UserSkillConfig(
        user_id=current_user.id,
        project_id=request.project_id,
        skill_id=request.skill_id,
        custom_parameters=request.custom_parameters,
        execution_order=request.execution_order
    )

    db.add(config)
    await db.commit()
    await db.refresh(config)

    return config


@router.get("/config")
async def get_user_skill_configs(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户的Skills配置"""
    query = select(UserSkillConfig).where(UserSkillConfig.user_id == current_user.id)

    if project_id:
        query = query.where(UserSkillConfig.project_id == project_id)

    result = await db.execute(query)
    configs = result.scalars().all()

    return {"configs": configs}

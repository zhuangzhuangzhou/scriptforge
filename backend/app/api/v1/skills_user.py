from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from app.core.database import get_db
from app.models.user import User
from app.models.skill import Skill
from app.models.user_skill_config import UserSkillConfig
from app.api.v1.auth import get_current_user

router = APIRouter()


def check_skill_visibility(skill: Skill, user_id: UUID) -> bool:
    """检查用户是否有权限访问Skill"""
    if skill.is_builtin:
        return True
    if skill.visibility == 'public':
        return True
    if skill.owner_id == user_id:
        return True
    if skill.visibility == 'shared':
        allowed_users = skill.allowed_users or []
        return str(user_id) in allowed_users
    return False


class UserSkillConfigRequest(BaseModel):
    """用户Skill配置请求"""
    skill_id: str
    project_id: Optional[str] = None
    custom_parameters: Optional[dict] = None
    execution_order: Optional[str] = None


class CreateSkillRequest(BaseModel):
    """创建Skill请求"""
    name: str
    display_name: str
    description: Optional[str] = None
    category: str
    module_path: str
    class_name: str
    visibility: str = 'public'  # public, private, shared
    allowed_users: Optional[List[str]] = None


@router.get("/available")
async def get_available_skills(
    category: Optional[str] = None,
    visibility: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取可用的Skills列表（根据权限过滤）"""
    # 获取公共Skills + 用户自己的Skills
    query = select(Skill).where(
        Skill.is_active == True,
        or_(
            Skill.visibility == 'public',  # 公共Skills
            Skill.owner_id == current_user.id,  # 用户自己的Skills
        )
    )

    if category:
        query = query.where(Skill.category == category)

    if visibility:
        query = query.where(Skill.visibility == visibility)

    result = await db.execute(query)
    skills = result.scalars().all()

    # 过滤用户可见的Skills
    visible_skills = [s for s in skills if check_skill_visibility(s, current_user.id)]

    return {"skills": visible_skills}


@router.get("/public")
async def get_public_skills(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """获取公共Skills（无需登录）"""
    query = select(Skill).where(
        Skill.is_active == True,
        Skill.visibility == 'public'
    )

    if category:
        query = query.where(Skill.category == category)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    skills = result.scalars().all()

    return {"skills": skills}


@router.get("/my")
async def get_my_skills(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户自己的Skills"""
    query = select(Skill).where(
        Skill.owner_id == current_user.id,
        Skill.is_active == True
    )

    if category:
        query = query.where(Skill.category == category)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    skills = result.scalars().all()

    return {"skills": skills}


@router.get("/shared")
async def get_shared_skills(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取分享给用户的Skills"""
    query = select(Skill).where(
        Skill.is_active == True,
        Skill.visibility == 'shared'
    )

    result = await db.execute(query)
    all_shared = result.scalars().all()

    # 过滤用户有权限访问的
    visible_skills = [s for s in all_shared if check_skill_visibility(s, current_user.id)]

    return {"skills": visible_skills}


@router.post("/create")
async def create_skill(
    request: CreateSkillRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新Skill（默认为私有）"""
    # 检查名称是否已存在
    result = await db.execute(
        select(Skill).where(Skill.name == request.name)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill名称已存在"
        )

    skill = Skill(
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        category=request.category,
        module_path=request.module_path,
        class_name=request.class_name,
        visibility=request.visibility,
        owner_id=current_user.id,
        allowed_users=request.allowed_users,
        is_builtin=False
    )

    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    return skill


@router.get("/{skill_id}")
async def get_skill_detail(
    skill_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取Skill详情（检查权限）"""
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill不存在"
        )

    # 检查权限
    if not check_skill_visibility(skill, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此Skill"
        )

    return skill


@router.post("/config")
async def save_skill_config(
    request: UserSkillConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """保存用户Skill配置"""
    # 验证Skill存在且有权限访问
    result = await db.execute(select(Skill).where(Skill.id == request.skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill不存在"
        )

    if not check_skill_visibility(skill, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此Skill"
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

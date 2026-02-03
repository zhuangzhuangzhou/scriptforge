from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.models.user import User
from app.models.skill import Skill
from app.api.v1.admin import check_admin

router = APIRouter()


class SkillCreateRequest(BaseModel):
    """创建Skill请求"""
    name: str
    display_name: str
    description: Optional[str] = None
    category: str
    module_path: str
    class_name: str
    parameters: Optional[dict] = None
    version: Optional[str] = "1.0.0"
    author: Optional[str] = None


class SkillUpdateRequest(BaseModel):
    """更新Skill请求"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    parameters: Optional[dict] = None
    is_active: Optional[bool] = None


@router.get("/skills")
async def get_skills(
    skip: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取Skills列表"""
    query = select(Skill)

    if category:
        query = query.where(Skill.category == category)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    skills = result.scalars().all()

    # 获取总数
    count_query = select(func.count(Skill.id))
    if category:
        count_query = count_query.where(Skill.category == category)
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return {
        "skills": skills,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/skills")
async def create_skill(
    request: SkillCreateRequest,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """创建Skill"""
    # 检查名称是否已存在
    result = await db.execute(select(Skill).where(Skill.name == request.name))
    existing_skill = result.scalar_one_or_none()

    if existing_skill:
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
        parameters=request.parameters,
        version=request.version,
        author=request.author
    )

    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    return skill


@router.put("/skills/{skill_id}")
async def update_skill(
    skill_id: str,
    request: SkillUpdateRequest,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """更新Skill"""
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill不存在"
        )

    if request.display_name is not None:
        skill.display_name = request.display_name
    if request.description is not None:
        skill.description = request.description
    if request.category is not None:
        skill.category = request.category
    if request.parameters is not None:
        skill.parameters = request.parameters
    if request.is_active is not None:
        skill.is_active = request.is_active

    await db.commit()
    await db.refresh(skill)

    return skill


@router.delete("/skills/{skill_id}")
async def delete_skill(
    skill_id: str,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """删除Skill"""
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill不存在"
        )

    if skill.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="内置Skill不能删除"
        )

    await db.delete(skill)
    await db.commit()

    return {"message": "Skill已删除"}

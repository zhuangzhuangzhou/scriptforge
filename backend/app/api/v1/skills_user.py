from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pydantic import BaseModel
from typing import Optional, List, Any
from uuid import UUID
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.skill import Skill
from app.models.user_skill_config import UserSkillConfig
from app.api.v1.auth import get_current_user
from app.ai.skills.template_skill_executor import TemplateSkillExecutor

logger = logging.getLogger(__name__)

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


class CreateTemplateSkillRequest(BaseModel):
    """创建模板Skill请求"""
    name: str
    display_name: str
    description: Optional[str] = None
    category: str  # breakdown, script
    prompt_template: str
    input_variables: List[str]
    output_schema: Optional[dict] = None
    visibility: str = "private"


class UpdateTemplateSkillRequest(BaseModel):
    """更新模板Skill请求"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    prompt_template: Optional[str] = None
    input_variables: Optional[List[str]] = None
    output_schema: Optional[dict] = None
    visibility: Optional[str] = None


class TestSkillRequest(BaseModel):
    """测试Skill请求"""
    variables: dict


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


@router.post("/template")
async def create_template_skill(
    request: CreateTemplateSkillRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建模板Skill"""
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

    # 验证 category
    valid_categories = ["breakdown", "script", "analysis"]
    if request.category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的category，必须是: {', '.join(valid_categories)}"
        )

    # 创建模板 Skill
    skill = Skill(
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        category=request.category,
        module_path="app.ai.skills.template_skill_executor",
        class_name="TemplateSkillExecutor",
        visibility=request.visibility,
        owner_id=current_user.id,
        is_builtin=False,
        is_template_based=True,
        prompt_template=request.prompt_template,
        input_variables=request.input_variables,
        output_schema=request.output_schema,
        author=current_user.username if hasattr(current_user, 'username') else None
    )

    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    logger.info(f"用户 {current_user.id} 创建了模板Skill: {skill.name}")

    return skill


@router.put("/template/{skill_id}")
async def update_template_skill(
    skill_id: str,
    request: UpdateTemplateSkillRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """编辑模板Skill"""
    # 查找 Skill
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill不存在"
        )

    # 检查是否为模板 Skill
    if not skill.is_template_based:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能编辑模板类型的Skill"
        )

    # 检查所有权
    if skill.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能编辑自己创建的Skill"
        )

    # 更新字段
    if request.display_name is not None:
        skill.display_name = request.display_name
    if request.description is not None:
        skill.description = request.description
    if request.category is not None:
        valid_categories = ["breakdown", "script", "analysis"]
        if request.category not in valid_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的category，必须是: {', '.join(valid_categories)}"
            )
        skill.category = request.category
    if request.prompt_template is not None:
        skill.prompt_template = request.prompt_template
    if request.input_variables is not None:
        skill.input_variables = request.input_variables
    if request.output_schema is not None:
        skill.output_schema = request.output_schema
    if request.visibility is not None:
        skill.visibility = request.visibility

    await db.commit()
    await db.refresh(skill)

    logger.info(f"用户 {current_user.id} 更新了模板Skill: {skill.name}")

    return skill


@router.post("/template/{skill_id}/test")
async def test_template_skill(
    skill_id: str,
    request: TestSkillRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """测试模板Skill"""
    # 查找 Skill
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill不存在"
        )

    # 检查是否为模板 Skill
    if not skill.is_template_based:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能测试模板类型的Skill"
        )

    # 检查权限
    if not check_skill_visibility(skill, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此Skill"
        )

    # 使用 TemplateSkillExecutor 执行测试
    executor = TemplateSkillExecutor(db)

    try:
        result = await executor.execute(
            skill_id=skill_id,
            variables=request.variables,
            user_id=str(current_user.id)
        )
        logger.info(f"用户 {current_user.id} 测试Skill {skill.name} 成功")
        return {
            "success": True,
            "result": result
        }
    except ValueError as e:
        logger.warning(f"测试Skill失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"测试Skill权限错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"测试Skill异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行测试时发生错误: {str(e)}"
        )

"""Skill 管理 API

提供 Skill 的 CRUD 操作和测试功能。
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, Field
import uuid

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.skill import Skill
from app.models.user import User

router = APIRouter(prefix="/skills", tags=["skills"])


# ==================== Pydantic Schemas ====================

class SkillBase(BaseModel):
    """Skill 基础信息"""
    name: str = Field(..., description="Skill 唯一标识")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="描述")
    category: Optional[str] = Field(None, description="分类：breakdown/qa/script")

    # 模板配置
    is_template_based: bool = Field(True, description="是否为模板驱动")
    prompt_template: Optional[str] = Field(None, description="Prompt 模板")
    input_schema: Optional[dict] = Field(None, description="输入 Schema")
    output_schema: Optional[dict] = Field(None, description="输出 Schema")
    model_config: Optional[dict] = Field(None, description="模型配置")

    # 示例数据
    example_input: Optional[dict] = Field(None, description="示例输入")
    example_output: Optional[dict] = Field(None, description="示例输出")

    # 权限
    visibility: str = Field("public", description="可见性：public/private/shared")


class SkillCreate(SkillBase):
    """创建 Skill"""
    pass


class SkillUpdate(BaseModel):
    """更新 Skill（所有字段可选）"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    prompt_template: Optional[str] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    model_config: Optional[dict] = None
    example_input: Optional[dict] = None
    example_output: Optional[dict] = None
    visibility: Optional[str] = None
    is_active: Optional[bool] = None


class SkillResponse(SkillBase):
    """Skill 响应"""
    id: str
    owner_id: str
    is_active: bool
    is_builtin: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SkillTestRequest(BaseModel):
    """测试 Skill 请求"""
    inputs: dict = Field(..., description="输入数据")
    model_config_id: Optional[str] = Field(None, description="模型配置 ID")


class SkillTestResponse(BaseModel):
    """测试 Skill 响应"""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


# ==================== API Endpoints ====================

@router.get("", response_model=List[SkillResponse])
async def list_skills(
    category: Optional[str] = Query(None, description="按分类筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    is_template_based: Optional[bool] = Query(None, description="是否为模板驱动"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取 Skill 列表"""

    # 构建查询条件
    conditions = [Skill.is_active == True]

    # 权限过滤：只显示公共的、自己创建的、或共享给自己的
    conditions.append(
        (Skill.visibility == "public") |
        (Skill.owner_id == current_user.id)
    )

    if category:
        conditions.append(Skill.category == category)

    if is_template_based is not None:
        conditions.append(Skill.is_template_based == is_template_based)

    if search:
        conditions.append(
            (Skill.name.ilike(f"%{search}%")) |
            (Skill.display_name.ilike(f"%{search}%")) |
            (Skill.description.ilike(f"%{search}%"))
        )

    # 执行查询
    result = await db.execute(
        select(Skill).where(and_(*conditions)).order_by(Skill.created_at.desc())
    )
    skills = result.scalars().all()

    return [
        SkillResponse(
            id=str(skill.id),
            name=skill.name,
            display_name=skill.display_name,
            description=skill.description,
            category=skill.category,
            is_template_based=skill.is_template_based,
            prompt_template=skill.prompt_template,
            input_schema=skill.input_schema,
            output_schema=skill.output_schema,
            model_config=skill.model_config,
            example_input=skill.example_input,
            example_output=skill.example_output,
            visibility=skill.visibility,
            owner_id=str(skill.owner_id),
            is_active=skill.is_active,
            is_builtin=skill.is_builtin,
            created_at=skill.created_at.isoformat(),
            updated_at=skill.updated_at.isoformat()
        )
        for skill in skills
    ]


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取 Skill 详情"""

    result = await db.execute(
        select(Skill).where(Skill.id == uuid.UUID(skill_id))
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill 不存在")

    # 权限检查
    if skill.visibility == "private" and skill.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此 Skill")

    return SkillResponse(
        id=str(skill.id),
        name=skill.name,
        display_name=skill.display_name,
        description=skill.description,
        category=skill.category,
        is_template_based=skill.is_template_based,
        prompt_template=skill.prompt_template,
        input_schema=skill.input_schema,
        output_schema=skill.output_schema,
        model_config=skill.model_config,
        example_input=skill.example_input,
        example_output=skill.example_output,
        visibility=skill.visibility,
        owner_id=str(skill.owner_id),
        is_active=skill.is_active,
        is_builtin=skill.is_builtin,
        created_at=skill.created_at.isoformat(),
        updated_at=skill.updated_at.isoformat()
    )


@router.post("", response_model=SkillResponse)
async def create_skill(
    skill_data: SkillCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新 Skill"""

    # 检查名称是否已存在
    result = await db.execute(
        select(Skill).where(Skill.name == skill_data.name)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Skill 名称已存在")

    # 创建 Skill
    skill = Skill(
        id=uuid.uuid4(),
        name=skill_data.name,
        display_name=skill_data.display_name,
        description=skill_data.description,
        category=skill_data.category,
        is_template_based=skill_data.is_template_based,
        prompt_template=skill_data.prompt_template,
        input_schema=skill_data.input_schema,
        output_schema=skill_data.output_schema,
        model_config=skill_data.model_config,
        example_input=skill_data.example_input,
        example_output=skill_data.example_output,
        visibility=skill_data.visibility,
        owner_id=current_user.id,
        is_active=True,
        is_builtin=False,
        # 兼容旧字段
        module_path="app.ai.simple_executor",
        class_name="SimpleSkillExecutor"
    )

    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    return SkillResponse(
        id=str(skill.id),
        name=skill.name,
        display_name=skill.display_name,
        description=skill.description,
        category=skill.category,
        is_template_based=skill.is_template_based,
        prompt_template=skill.prompt_template,
        input_schema=skill.input_schema,
        output_schema=skill.output_schema,
        model_config=skill.model_config,
        example_input=skill.example_input,
        example_output=skill.example_output,
        visibility=skill.visibility,
        owner_id=str(skill.owner_id),
        is_active=skill.is_active,
        is_builtin=skill.is_builtin,
        created_at=skill.created_at.isoformat(),
        updated_at=skill.updated_at.isoformat()
    )


@router.put("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: str,
    skill_data: SkillUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新 Skill"""

    result = await db.execute(
        select(Skill).where(Skill.id == uuid.UUID(skill_id))
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill 不存在")

    # 权限检查：只有创建者可以编辑
    if skill.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权编辑此 Skill")

    # 内置 Skill 不可编辑
    if skill.is_builtin:
        raise HTTPException(status_code=403, detail="内置 Skill 不可编辑")

    # 更新字段
    update_data = skill_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(skill, key, value)

    await db.commit()
    await db.refresh(skill)

    return SkillResponse(
        id=str(skill.id),
        name=skill.name,
        display_name=skill.display_name,
        description=skill.description,
        category=skill.category,
        is_template_based=skill.is_template_based,
        prompt_template=skill.prompt_template,
        input_schema=skill.input_schema,
        output_schema=skill.output_schema,
        model_config=skill.model_config,
        example_input=skill.example_input,
        example_output=skill.example_output,
        visibility=skill.visibility,
        owner_id=str(skill.owner_id),
        is_active=skill.is_active,
        is_builtin=skill.is_builtin,
        created_at=skill.created_at.isoformat(),
        updated_at=skill.updated_at.isoformat()
    )


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除 Skill（软删除）"""

    result = await db.execute(
        select(Skill).where(Skill.id == uuid.UUID(skill_id))
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill 不存在")

    # 权限检查
    if skill.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除此 Skill")

    # 内置 Skill 不可删除
    if skill.is_builtin:
        raise HTTPException(status_code=403, detail="内置 Skill 不可删除")

    # 软删除
    skill.is_active = False
    await db.commit()

    return {"message": "Skill 已删除"}


@router.post("/{skill_id}/test", response_model=SkillTestResponse)
async def test_skill(
    skill_id: str,
    test_data: SkillTestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """测试 Skill 执行"""
    import time
    from app.ai.simple_executor import SimpleSkillExecutor
    from app.ai.adapters import get_adapter
    from app.core.database import get_sync_db

    # 获取 Skill
    result = await db.execute(
        select(Skill).where(Skill.id == uuid.UUID(skill_id))
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill 不存在")

    # 权限检查
    if skill.visibility == "private" and skill.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权测试此 Skill")

    # 获取模型配置
    model_config_id = test_data.model_config_id
    if not model_config_id:
        # 使用默认模型
        from app.models.model_config import ModelConfig
        result = await db.execute(
            select(ModelConfig).where(
                ModelConfig.owner_id == current_user.id,
                ModelConfig.is_active == True
            ).limit(1)
        )
        model_config = result.scalar_one_or_none()
        if not model_config:
            raise HTTPException(status_code=400, detail="未找到可用的模型配置")
        model_config_id = str(model_config.id)

    try:
        # 获取模型适配器
        model_adapter = await get_adapter(
            db=db,
            model_id=model_config_id,
            user_id=str(current_user.id)
        )

        # 创建同步数据库会话（用于执行器）
        sync_db = next(get_sync_db())

        # 创建执行器
        executor = SimpleSkillExecutor(
            db=sync_db,
            model_adapter=model_adapter
        )

        # 执行测试
        start_time = time.time()
        result = executor.execute_skill(
            skill_name=skill.name,
            inputs=test_data.inputs
        )
        execution_time = time.time() - start_time

        return SkillTestResponse(
            success=True,
            result=result,
            execution_time=execution_time
        )

    except Exception as e:
        return SkillTestResponse(
            success=False,
            error=str(e)
        )

"""AI 资源文档管理 API

提供 AI 资源文档（方法论、输出风格、模板、示例）的 CRUD 操作。
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from pydantic import BaseModel, Field
import uuid

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.ai_resource import AIResource
from app.models.user import User

router = APIRouter(prefix="/ai-resources", tags=["AI资源文档"])


# ==================== Pydantic Schemas ====================

# TODO: 后期升级 - 将分类配置迁移到数据库表，支持动态管理
# 目前分类配置写死在代码中，通过 /categories 接口返回给前端
# 升级方案：新建 ai_resource_categories 表，存储 key/label/icon/color/description/order/default_select_all
# 分类枚举定义（包含图标和颜色信息供前端使用）
RESOURCE_CATEGORIES = {
    "methodology": {
        "label": "方法论",
        "icon": "BookOpen",
        "color": "blue",
        "description": "改编方法论，决定如何提取冲突、识别情绪钩子、应用压缩策略",
        "order": 1,
        "default_select_all": True,  # 默认全选
    },
    "type_guide": {
        "label": "类型指南",
        "icon": "Compass",
        "color": "emerald",
        "description": "不同小说类型的改编指南，针对悬疑、言情、玄幻等类型的专属策略",
        "order": 2,
        "default_select_all": False,
    },
    "output_style": {
        "label": "输出风格",
        "icon": "Palette",
        "color": "purple",
        "description": "剧本输出的风格规范（起承转钩、视觉化优先、快节奏无尿点）",
        "order": 3,
        "default_select_all": False,
    },
    "qa_rules": {
        "label": "质检规则",
        "icon": "Shield",
        "color": "orange",
        "description": "质量检查标准和维度，决定拆解结果的通过阈值",
        "order": 4,
        "default_select_all": False,
    },
    "template": {
        "label": "模板案例",
        "icon": "FileText",
        "color": "cyan",
        "description": "输出格式模板和参考示例",
        "order": 5,
        "default_select_all": False,
    },
    "hook_types": {
        "label": "钩子规则",
        "icon": "Anchor",
        "color": "rose",
        "description": "情绪钩子类型和规则定义（爽感、震撼、虐心、悬念、成长、情感、冲突等）",
        "order": 6,
        "default_select_all": True,
    },
    "breakdown_prompt": {
        "label": "拆解提示词",
        "icon": "MessageSquare",
        "color": "indigo",
        "description": "剧情拆解各步骤的提示词模板，控制 AI 如何分析小说内容",
        "order": 7,
        "default_select_all": False,
    },
}


class AIResourceCreate(BaseModel):
    """创建 AI 资源"""
    name: str = Field(..., description="唯一标识")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="描述")
    category: str = Field(..., description="分类：methodology/output_style/qa_rules/template")
    content: str = Field(..., description="Markdown 文档内容")
    visibility: str = Field("public", description="可见性：public/private")


class AIResourceUpdate(BaseModel):
    """更新 AI 资源（所有字段可选）"""
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    visibility: Optional[str] = None
    is_active: Optional[bool] = None


class AIResourceResponse(BaseModel):
    """AI 资源响应"""
    model_config = {"from_attributes": True}

    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    category: str
    content: str
    is_builtin: bool = False
    owner_id: Optional[str] = None
    visibility: str = "public"
    is_active: bool = True
    version: int = 1
    parent_id: Optional[str] = None
    created_at: str
    updated_at: str


class AIResourceListResponse(BaseModel):
    """AI 资源列表响应（带分页）"""
    items: List[AIResourceResponse]
    total: int
    page: int
    page_size: int


# ==================== 辅助函数 ====================

def _to_response(resource: AIResource) -> AIResourceResponse:
    """将 ORM 对象转换为响应模型"""
    return AIResourceResponse(
        id=str(resource.id),
        name=resource.name,
        display_name=resource.display_name,
        description=resource.description,
        category=resource.category,
        content=resource.content,
        is_builtin=resource.is_builtin,
        owner_id=str(resource.owner_id) if resource.owner_id else None,
        visibility=resource.visibility,
        is_active=resource.is_active,
        version=resource.version,
        parent_id=str(resource.parent_id) if resource.parent_id else None,
        created_at=resource.created_at.isoformat(),
        updated_at=resource.updated_at.isoformat()
    )


# ==================== API Endpoints ====================

@router.get("/categories")
async def get_resource_categories():
    """获取 AI 资源分类列表"""
    categories = []
    for key, config in RESOURCE_CATEGORIES.items():
        categories.append({
            "key": key,
            "label": config["label"],
            "icon": config["icon"],
            "color": config["color"],
            "description": config["description"],
            "order": config["order"],
            "default_select_all": config["default_select_all"],
        })
    # 按 order 排序
    categories.sort(key=lambda x: x["order"])
    return {"categories": categories}


@router.get("", response_model=AIResourceListResponse)
async def list_ai_resources(
    category: Optional[str] = Query(None, description="按分类筛选：adapt_method/output_style/template/example"),
    scope: Optional[str] = Query(None, description="范围筛选：all/builtin/mine"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取 AI 资源列表"""
    conditions = [AIResource.is_active == True]

    # 权限过滤：用户只能看到公共资源和自己的资源
    if current_user.role != "admin":
        conditions.append(
            or_(
                AIResource.visibility == "public",
                AIResource.owner_id == current_user.id
            )
        )

    # 分类筛选（qa_rules 包含 qa_dimensions，hook_types 包含 hook_rules）
    if category:
        if category == "qa_rules":
            # 质检规则包含 qa_rules 和 qa_dimensions
            conditions.append(
                or_(
                    AIResource.category == "qa_rules",
                    AIResource.category == "qa_dimensions"
                )
            )
        elif category == "hook_types":
            # 钩子规则包含 hook_types 和 hook_rules
            conditions.append(
                or_(
                    AIResource.category == "hook_types",
                    AIResource.category == "hook_rules"
                )
            )
        else:
            conditions.append(AIResource.category == category)

    # 范围筛选
    if scope == "builtin":
        conditions.append(AIResource.is_builtin == True)
    elif scope == "mine":
        conditions.append(AIResource.owner_id == current_user.id)

    # 搜索
    if search:
        conditions.append(
            or_(
                AIResource.name.ilike(f"%{search}%"),
                AIResource.display_name.ilike(f"%{search}%"),
                AIResource.description.ilike(f"%{search}%")
            )
        )

    # 查询总数
    count_query = select(func.count()).select_from(AIResource).where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页查询
    query = select(AIResource).where(and_(*conditions))
    query = query.order_by(AIResource.is_builtin.desc(), AIResource.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    resources = result.scalars().all()

    return AIResourceListResponse(
        items=[_to_response(r) for r in resources],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{resource_id}", response_model=AIResourceResponse)
async def get_ai_resource(
    resource_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取 AI 资源详情"""
    result = await db.execute(
        select(AIResource).where(AIResource.id == uuid.UUID(resource_id))
    )
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(status_code=404, detail="AI 资源不存在")

    # 权限检查
    if resource.visibility == "private" and resource.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权访问此资源")

    return _to_response(resource)


@router.post("", response_model=AIResourceResponse)
async def create_ai_resource(
    data: AIResourceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建 AI 资源"""
    # 检查名称是否已存在
    result = await db.execute(
        select(AIResource).where(AIResource.name == data.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="资源名称已存在")

    resource = AIResource(
        id=uuid.uuid4(),
        name=data.name,
        display_name=data.display_name,
        description=data.description,
        category=data.category,
        content=data.content,
        visibility=data.visibility,
        owner_id=current_user.id,
        is_builtin=False,
        is_active=True,
        version=1
    )

    db.add(resource)
    await db.commit()
    await db.refresh(resource)

    return _to_response(resource)


@router.put("/{resource_id}", response_model=AIResourceResponse)
async def update_ai_resource(
    resource_id: str,
    data: AIResourceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新 AI 资源

    - 普通用户只能编辑自己创建的资源
    - 管理员可以编辑内置资源（仅限 content、description、display_name、is_active）
    """
    result = await db.execute(
        select(AIResource).where(AIResource.id == uuid.UUID(resource_id))
    )
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(status_code=404, detail="AI 资源不存在")

    # 内置资源：只有管理员可以编辑，且只能修改部分字段
    if resource.is_builtin:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="只有管理员可以编辑内置资源")

        # 内置资源只允许修改这些字段
        allowed_fields = {"content", "description", "display_name", "is_active"}
        update_data = data.model_dump(exclude_unset=True)

        # 检查是否有不允许修改的字段
        disallowed = set(update_data.keys()) - allowed_fields
        if disallowed:
            raise HTTPException(
                status_code=400,
                detail=f"内置资源不允许修改以下字段: {', '.join(disallowed)}"
            )

        for key, value in update_data.items():
            setattr(resource, key, value)
    else:
        # 非内置资源：只能编辑自己创建的资源（管理员可以编辑所有）
        if resource.owner_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="无权编辑此资源")

        # 更新字段
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(resource, key, value)

    await db.commit()
    await db.refresh(resource)

    return _to_response(resource)


@router.patch("/{resource_id}/toggle")
async def toggle_ai_resource(
    resource_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """切换 AI 资源的启用/禁用状态

    - 管理员可以切换任何资源（包括内置资源）
    - 普通用户只能切换自己创建的资源
    """
    result = await db.execute(
        select(AIResource).where(AIResource.id == uuid.UUID(resource_id))
    )
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(status_code=404, detail="AI 资源不存在")

    # 权限检查
    if resource.is_builtin:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="只有管理员可以切换内置资源状态")
    else:
        if resource.owner_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="无权操作此资源")

    # 切换状态
    resource.is_active = not resource.is_active
    await db.commit()
    await db.refresh(resource)

    return {
        "id": str(resource.id),
        "is_active": resource.is_active,
        "message": f"资源已{'启用' if resource.is_active else '禁用'}"
    }


@router.delete("/{resource_id}")
async def delete_ai_resource(
    resource_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除 AI 资源（软删除）"""
    result = await db.execute(
        select(AIResource).where(AIResource.id == uuid.UUID(resource_id))
    )
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(status_code=404, detail="AI 资源不存在")

    # 内置资源不允许删除
    if resource.is_builtin:
        raise HTTPException(status_code=403, detail="内置资源不可删除")

    # 只能删除自己创建的资源
    if resource.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权删除此资源")

    resource.is_active = False
    await db.commit()

    return {"message": "AI 资源已删除"}


@router.post("/{resource_id}/clone", response_model=AIResourceResponse)
async def clone_ai_resource(
    resource_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """复制 AI 资源（基于系统内置创建用户私有版本）"""
    result = await db.execute(
        select(AIResource).where(AIResource.id == uuid.UUID(resource_id))
    )
    original = result.scalar_one_or_none()

    if not original:
        raise HTTPException(status_code=404, detail="AI 资源不存在")

    # 权限检查：只能复制公共的或自己的资源
    if original.visibility == "private" and original.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权复制此资源")

    # 生成新名称（避免冲突）
    base_name = original.name
    new_name = f"{base_name}_copy"
    counter = 1

    while True:
        result = await db.execute(
            select(AIResource).where(AIResource.name == new_name)
        )
        if not result.scalar_one_or_none():
            break
        counter += 1
        new_name = f"{base_name}_copy_{counter}"

    new_resource = AIResource(
        id=uuid.uuid4(),
        name=new_name,
        display_name=f"{original.display_name} (副本)",
        description=original.description,
        category=original.category,
        content=original.content,
        visibility="private",
        owner_id=current_user.id,
        is_builtin=False,
        is_active=True,
        version=1,
        parent_id=original.id
    )

    db.add(new_resource)
    await db.commit()
    await db.refresh(new_resource)

    return _to_response(new_resource)

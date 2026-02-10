"""简化的 Agent 管理 API

提供 Agent 的 CRUD 操作和执行功能。
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, Field
import uuid

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.agent import SimpleAgent
from app.models.user import User

router = APIRouter(prefix="/simple-agents", tags=["simple-agents"])


# ==================== Pydantic Schemas ====================

class AgentBase(BaseModel):
    """Agent 基础信息"""
    name: str = Field(..., description="Agent 唯一标识")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="描述")
    category: Optional[str] = Field(None, description="分类：breakdown/qa/script")
    workflow: dict = Field(..., description="工作流定义")
    visibility: str = Field("public", description="可见性：public/private")


class AgentCreate(AgentBase):
    """创建 Agent"""
    pass


class AgentUpdate(BaseModel):
    """更新 Agent（所有字段可选）"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    workflow: Optional[dict] = None
    visibility: Optional[str] = None
    is_active: Optional[bool] = None


class AgentResponse(AgentBase):
    """Agent 响应"""
    id: str
    owner_id: str
    is_active: bool
    is_builtin: bool
    version: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class AgentExecuteRequest(BaseModel):
    """执行 Agent 请求"""
    context: dict = Field(..., description="初始上下文数据")
    model_config_id: Optional[str] = Field(None, description="模型配置 ID")


class AgentExecuteResponse(BaseModel):
    """执行 Agent 响应"""
    success: bool
    results: Optional[dict] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


# ==================== API Endpoints ====================

@router.get("", response_model=List[AgentResponse])
async def list_agents(
    category: Optional[str] = Query(None, description="按分类筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取 Agent 列表"""

    # 构建查询条件
    conditions = [SimpleAgent.is_active == True]

    # 权限过滤
    conditions.append(
        (SimpleAgent.visibility == "public") |
        (SimpleAgent.owner_id == current_user.id)
    )

    if category:
        conditions.append(SimpleAgent.category == category)

    if search:
        conditions.append(
            (SimpleAgent.name.ilike(f"%{search}%")) |
            (SimpleAgent.display_name.ilike(f"%{search}%")) |
            (SimpleAgent.description.ilike(f"%{search}%"))
        )

    # 执行查询
    result = await db.execute(
        select(SimpleAgent).where(and_(*conditions)).order_by(SimpleAgent.created_at.desc())
    )
    agents = result.scalars().all()

    return [
        AgentResponse(
            id=str(agent.id),
            name=agent.name,
            display_name=agent.display_name,
            description=agent.description,
            category=agent.category,
            workflow=agent.workflow,
            visibility=agent.visibility,
            owner_id=str(agent.owner_id),
            is_active=agent.is_active,
            is_builtin=agent.is_builtin,
            version=agent.version,
            created_at=agent.created_at.isoformat(),
            updated_at=agent.updated_at.isoformat()
        )
        for agent in agents
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取 Agent 详情"""

    result = await db.execute(
        select(SimpleAgent).where(SimpleAgent.id == uuid.UUID(agent_id))
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    # 权限检查
    if agent.visibility == "private" and agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此 Agent")

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        display_name=agent.display_name,
        description=agent.description,
        category=agent.category,
        workflow=agent.workflow,
        visibility=agent.visibility,
        owner_id=str(agent.owner_id),
        is_active=agent.is_active,
        is_builtin=agent.is_builtin,
        version=agent.version,
        created_at=agent.created_at.isoformat(),
        updated_at=agent.updated_at.isoformat()
    )


@router.post("", response_model=AgentResponse)
async def create_agent(
    agent_data: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新 Agent"""

    # 检查名称是否已存在
    result = await db.execute(
        select(SimpleAgent).where(SimpleAgent.name == agent_data.name)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Agent 名称已存在")

    # 创建 Agent
    agent = SimpleAgent(
        id=uuid.uuid4(),
        name=agent_data.name,
        display_name=agent_data.display_name,
        description=agent_data.description,
        category=agent_data.category,
        workflow=agent_data.workflow,
        visibility=agent_data.visibility,
        owner_id=current_user.id,
        is_active=True,
        is_builtin=False
    )

    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        display_name=agent.display_name,
        description=agent.description,
        category=agent.category,
        workflow=agent.workflow,
        visibility=agent.visibility,
        owner_id=str(agent.owner_id),
        is_active=agent.is_active,
        is_builtin=agent.is_builtin,
        version=agent.version,
        created_at=agent.created_at.isoformat(),
        updated_at=agent.updated_at.isoformat()
    )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新 Agent"""

    result = await db.execute(
        select(SimpleAgent).where(SimpleAgent.id == uuid.UUID(agent_id))
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    # 权限检查
    if agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权编辑此 Agent")

    # 内置 Agent 不可编辑
    if agent.is_builtin:
        raise HTTPException(status_code=403, detail="内置 Agent 不可编辑")

    # 更新字段
    update_data = agent_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)

    await db.commit()
    await db.refresh(agent)

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        display_name=agent.display_name,
        description=agent.description,
        category=agent.category,
        workflow=agent.workflow,
        visibility=agent.visibility,
        owner_id=str(agent.owner_id),
        is_active=agent.is_active,
        is_builtin=agent.is_builtin,
        version=agent.version,
        created_at=agent.created_at.isoformat(),
        updated_at=agent.updated_at.isoformat()
    )


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除 Agent（软删除）"""

    result = await db.execute(
        select(SimpleAgent).where(SimpleAgent.id == uuid.UUID(agent_id))
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    # 权限检查
    if agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除此 Agent")

    # 内置 Agent 不可删除
    if agent.is_builtin:
        raise HTTPException(status_code=403, detail="内置 Agent 不可删除")

    # 软删除
    agent.is_active = False
    await db.commit()

    return {"message": "Agent 已删除"}


@router.post("/{agent_id}/execute", response_model=AgentExecuteResponse)
async def execute_agent(
    agent_id: str,
    execute_data: AgentExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """执行 Agent"""
    import time
    from app.ai.simple_executor import SimpleAgentExecutor
    from app.ai.adapters import get_adapter

    # 获取 Agent
    result = await db.execute(
        select(SimpleAgent).where(SimpleAgent.id == uuid.UUID(agent_id))
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    # 权限检查
    if agent.visibility == "private" and agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权执行此 Agent")

    # 获取模型配置
    model_config_id = execute_data.model_config_id
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

        # 创建同步数据库会话
        sync_db = next(get_sync_db())

        # 创建执行器
        executor = SimpleAgentExecutor(
            db=sync_db,
            model_adapter=model_adapter
        )

        # 执行 Agent
        start_time = time.time()
        results = executor.execute_agent(
            agent_name=agent.name,
            context=execute_data.context
        )
        execution_time = time.time() - start_time

        return AgentExecuteResponse(
            success=True,
            results=results,
            execution_time=execution_time
        )

    except Exception as e:
        return AgentExecuteResponse(
            success=False,
            error=str(e)
        )

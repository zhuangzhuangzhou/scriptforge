from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime
from app.core.database import get_db
from app.models.user import User
from app.models.agent import AgentDefinition, AgentExecution, PipelineNodeAgent
from app.api.v1.auth import get_current_user

router = APIRouter()


# ============ 请求模型 ============

class CreateAgentRequest(BaseModel):
    """创建 Agent 请求"""
    name: str = Field(..., min_length=1, max_length=100, description="内部标识")
    display_name: str = Field(..., min_length=1, max_length=255, description="显示名称")
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)

    # Agent 配置
    role: str = Field(..., min_length=1, description="角色设定")
    goal: str = Field(..., min_length=1, description="目标描述")
    system_prompt: Optional[str] = None
    prompt_template: str = Field(default="{{input}}", description="Prompt 模板")

    # 参数配置
    parameters_schema: Optional[dict] = None
    default_parameters: Optional[dict] = None

    # 触发配置
    trigger_type: str = Field(default="manual", description="触发类型")
    trigger_config: Optional[dict] = None

    # 输出配置
    output_format: str = Field(default="text", description="输出格式")

    # 权限
    is_public: bool = Field(default=False, description="是否公开")


class UpdateAgentRequest(BaseModel):
    """更新 Agent 请求"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    role: Optional[str] = None
    goal: Optional[str] = None
    system_prompt: Optional[str] = None
    prompt_template: Optional[str] = None
    parameters_schema: Optional[dict] = None
    default_parameters: Optional[dict] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[dict] = None
    output_format: Optional[str] = None
    is_public: Optional[bool] = None


class ExecuteAgentRequest(BaseModel):
    """执行 Agent 请求"""
    input_data: Any
    context: Optional[dict] = None
    parameters: Optional[dict] = None


class BindAgentRequest(BaseModel):
    """绑定 Agent 到节点请求"""
    agent_id: str
    node_id: str = Field(..., description="Pipeline 节点 ID")
    agent_order: int = Field(default=0, ge=0)
    input_mapping: Optional[dict] = None
    output_mapping: Optional[dict] = None
    trigger_condition: Optional[dict] = None
    is_optional: bool = Field(default=True)


class ExecuteFromNodeRequest(BaseModel):
    """从 Pipeline 节点触发执行"""
    node_id: str
    pipeline_id: Optional[str] = None
    input_data: Any
    context: Optional[dict] = None
    parameters: Optional[dict] = None


# ============ API 端点 ============

@router.get("/definitions")
async def get_agent_definitions(
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取 Agent 定义列表"""
    # 构建查询
    query = select(AgentDefinition).where(
        AgentDefinition.is_active == True,
        (
            (AgentDefinition.user_id == current_user.id) |
            (AgentDefinition.is_public == True)
        )
    )

    # 分类过滤
    if category:
        query = query.where(AgentDefinition.category == category)

    # 搜索过滤
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                AgentDefinition.display_name.ilike(search_pattern),
                AgentDefinition.description.ilike(search_pattern),
                AgentDefinition.name.ilike(search_pattern)
            )
        )

    # 统计总数
    count_query = select(AgentDefinition).where(
        and_(
            AgentDefinition.is_active == True,
            or_(
                AgentDefinition.user_id == current_user.id,
                AgentDefinition.is_public == True
            )
        )
    )
    if category:
        count_query = count_query.where(AgentDefinition.category == category)
    if search:
        count_query = count_query.where(
            or_(
                AgentDefinition.display_name.ilike(search_pattern),
                AgentDefinition.description.ilike(search_pattern)
            )
        )
    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(AgentDefinition.created_at.desc())

    result = await db.execute(query)
    agents = result.scalars().all()

    return {
        "agents": [
            {
                "id": str(a.id),
                "name": a.name,
                "display_name": a.display_name,
                "description": a.description,
                "category": a.category,
                "role": a.role[:100] + "..." if len(a.role) > 100 else a.role,
                "goal": a.goal,
                "output_format": a.output_format,
                "is_public": a.is_public,
                "usage_count": a.usage_count,
                "is_mine": str(a.user_id) == str(current_user.id),
                "created_at": a.created_at.isoformat()
            }
            for a in agents
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/definitions/{agent_id}")
async def get_agent_detail(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取 Agent 详情"""
    result = await db.execute(
        select(AgentDefinition).where(AgentDefinition.id == agent_id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent 不存在"
        )

    # 检查权限
    if not agent.is_public and str(agent.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此 Agent"
        )

    return {
        "id": str(agent.id),
        "name": agent.name,
        "display_name": agent.display_name,
        "description": agent.description,
        "category": agent.category,
        "role": agent.role,
        "goal": agent.goal,
        "system_prompt": agent.system_prompt,
        "prompt_template": agent.prompt_template,
        "parameters_schema": agent.parameters_schema,
        "default_parameters": agent.default_parameters,
        "trigger_type": agent.trigger_type,
        "trigger_config": agent.trigger_config,
        "output_format": agent.output_format,
        "is_public": agent.is_public,
        "usage_count": agent.usage_count,
        "is_mine": str(agent.user_id) == str(current_user.id),
        "created_at": agent.created_at.isoformat(),
        "updated_at": agent.updated_at.isoformat()
    }


@router.post("/definitions")
async def create_agent(
    request: CreateAgentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新 Agent"""
    # 检查名称是否已存在
    result = await db.execute(
        select(AgentDefinition).where(
            and_(
                AgentDefinition.name == request.name,
                AgentDefinition.user_id == current_user.id
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent 名称已存在"
        )

    agent = AgentDefinition(
        user_id=current_user.id,
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        category=request.category,
        role=request.role,
        goal=request.goal,
        system_prompt=request.system_prompt,
        prompt_template=request.prompt_template,
        parameters_schema=request.parameters_schema,
        default_parameters=request.default_parameters,
        trigger_type=request.trigger_type,
        trigger_config=request.trigger_config,
        output_format=request.output_format,
        is_public=request.is_public,
        is_template=False
    )

    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return {
        "id": str(agent.id),
        "message": "Agent 创建成功"
    }


@router.put("/definitions/{agent_id}")
async def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新 Agent"""
    result = await db.execute(
        select(AgentDefinition).where(AgentDefinition.id == agent_id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent 不存在"
        )

    # 检查权限
    if str(agent.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能修改自己创建的 Agent"
        )

    # 更新字段
    update_data = request.model_dump(exclude_unset=True)
    if update_data:
        await db.execute(
            update(AgentDefinition)
            .where(AgentDefinition.id == agent_id)
            .values(**update_data, updated_at=datetime.utcnow())
        )
        await db.commit()

    return {"message": "Agent 更新成功"}


@router.delete("/definitions/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除 Agent（软删除）"""
    result = await db.execute(
        select(AgentDefinition).where(AgentDefinition.id == agent_id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent 不存在"
        )

    # 检查权限
    if str(agent.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能删除自己创建的 Agent"
        )

    # 软删除
    await db.execute(
        update(AgentDefinition)
        .where(AgentDefinition.id == agent_id)
        .values(is_active=False, updated_at=datetime.utcnow())
    )
    await db.commit()

    return {"message": "Agent 已删除"}


@router.post("/execute/{agent_id}")
async def execute_agent(
    agent_id: str,
    request: ExecuteAgentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """执行 Agent"""
    # 1. 获取 Agent 定义
    result = await db.execute(
        select(AgentDefinition).where(AgentDefinition.id == agent_id)
    )
    agent_def = result.scalar_one_or_none()

    if not agent_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent 不存在"
        )

    # 2. 检查权限
    if not agent_def.is_public and str(agent_def.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此 Agent"
        )

    # 3. 更新使用计数
    await db.execute(
        update(AgentDefinition)
        .where(AgentDefinition.id == agent_id)
        .values(usage_count=AgentDefinition.usage_count + 1)
    )
    await db.commit()

    # 4. 执行 Agent
    from app.ai.agents.agent_executor import AgentExecutor
    from app.ai.adapters import get_adapter

    adapter = await get_adapter(
        user_id=str(current_user.id),
        db=db
    )
    executor = AgentExecutor(adapter)

    result = await executor.execute(
        agent_definition={
            "name": agent_def.name,
            "role": agent_def.role,
            "goal": agent_def.goal,
            "system_prompt": agent_def.system_prompt,
            "prompt_template": agent_def.prompt_template,
            "output_format": agent_def.output_format
        },
        input_data=request.input_data,
        context=request.context,
        parameters=request.parameters or agent_def.default_parameters
    )

    # 5. 记录执行历史
    execution = AgentExecution(
        agent_id=agent_def.id,
        input_data=request.input_data,
        output_data=result.get("output"),
        context_history=request.context,
        status="completed" if result.get("success") else "failed",
        error_message=result.get("error"),
        tokens_used=result.get("tokens_used", 0),
        execution_time=result.get("execution_time", 0)
    )
    db.add(execution)
    await db.commit()

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Agent 执行失败")
        )

    return {
        "output": result["output"],
        "tokens_used": result["tokens_used"],
        "execution_time": result["execution_time"]
    }


@router.get("/executions/{agent_id}")
async def get_agent_executions(
    agent_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取 Agent 执行历史"""
    # 检查权限
    result = await db.execute(
        select(AgentDefinition).where(AgentDefinition.id == agent_id)
    )
    agent_def = result.scalar_one_or_none()

    if not agent_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent 不存在"
        )

    if str(agent_def.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能查看自己创建的 Agent 执行历史"
        )

    # 获取执行记录
    query = select(AgentExecution).where(
        AgentExecution.agent_id == agent_id
    ).order_by(AgentExecution.created_at.desc())

    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    executions = result.scalars().all()

    return {
        "executions": [
            {
                "id": str(e.id),
                "status": e.status,
                "input_data": e.input_data,
                "output_data": e.output_data,
                "tokens_used": e.tokens_used,
                "execution_time": e.execution_time,
                "created_at": e.created_at.isoformat()
            }
            for e in executions
        ]
    }


@router.post("/node/trigger")
async def trigger_agent_from_node(
    request: ExecuteFromNodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """从 Pipeline 节点触发 Agent 执行"""
    # 查找绑定的 Agent
    result = await db.execute(
        select(PipelineNodeAgent)
        .where(
            and_(
                PipelineNodeAgent.node_id == request.node_id,
                PipelineNodeAgent.agent_id.in_(
                    select(AgentDefinition.id).where(
                        or_(
                            AgentDefinition.user_id == current_user.id,
                            AgentDefinition.is_public == True
                        )
                    )
                )
            )
        )
        .order_by(PipelineNodeAgent.agent_order)
    )
    bindings = result.scalars().all()

    if not bindings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该节点没有绑定任何 Agent"
        )

    results = []

    # 依次执行绑定的 Agent
    for binding in bindings:
        # 获取 Agent 定义
        agent_result = await db.execute(
            select(AgentDefinition).where(AgentDefinition.id == binding.agent_id)
        )
        agent_def = agent_result.scalar_one_or_none()

        if not agent_def or not agent_def.is_active:
            continue

        # 执行 Agent
        from app.ai.agents.agent_executor import AgentExecutor
        from app.ai.adapters import get_adapter

        adapter = await get_adapter(
            user_id=str(current_user.id),
            db=db
        )
        executor = AgentExecutor(adapter)

        # 应用输入映射
        input_data = _apply_mapping(
            request.input_data,
            binding.input_mapping
        )

        result = await executor.execute(
            agent_definition={
                "name": agent_def.name,
                "role": agent_def.role,
                "goal": agent_def.goal,
                "system_prompt": agent_def.system_prompt,
                "prompt_template": agent_def.prompt_template,
                "output_format": agent_def.output_format
            },
            input_data=input_data,
            context=request.context
        )

        # 记录执行
        execution = AgentExecution(
            agent_id=agent_def.id,
            pipeline_id=request.pipeline_id,
            node_id=request.node_id,
            input_data=input_data,
            output_data=result.get("output"),
            context_history=request.context,
            status="completed" if result.get("success") else "failed",
            error_message=result.get("error"),
            tokens_used=result.get("tokens_used", 0),
            execution_time=result.get("execution_time", 0)
        )
        db.add(execution)

        # 应用输出映射
        output_data = _apply_mapping(
            result.get("output"),
            binding.output_mapping
        )

        results.append({
            "agent_id": str(agent_def.id),
            "agent_name": agent_def.display_name,
            "success": result.get("success", False),
            "output": output_data
        })

    await db.commit()

    return {
        "node_id": request.node_id,
        "results": results
    }


def _apply_mapping(data: Any, mapping: Optional[dict]) -> Any:
    """应用数据映射"""
    if not mapping or not data:
        return data

    if isinstance(data, dict):
        result = {}
        for key, value in mapping.items():
            if key in data:
                result[value] = data[key]
            # 如果映射值是路径，支持嵌套
            elif "." in value:
                parts = value.split(".")
                current = data
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        current = None
                        break
                if current is not None:
                    result[key] = current
        return result if result else data

    return data

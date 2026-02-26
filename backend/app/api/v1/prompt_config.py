"""用户提示词配置 API

提供用户对剧情拆解各步骤提示词的配置管理。
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user_prompt_config import UserPromptConfig
from app.models.ai_resource import AIResource
from app.models.user import User

router = APIRouter(prefix="/prompt-config", tags=["提示词配置"])


# ==================== Pydantic Schemas ====================

class PromptConfigResponse(BaseModel):
    """提示词配置响应"""
    id: Optional[str] = None
    user_id: str
    project_id: Optional[str] = None
    conflict_prompt_id: Optional[str] = None
    character_prompt_id: Optional[str] = None
    scene_prompt_id: Optional[str] = None
    emotion_prompt_id: Optional[str] = None
    plot_hook_prompt_id: Optional[str] = None
    # 附带提示词名称，方便前端显示
    conflict_prompt_name: Optional[str] = None
    character_prompt_name: Optional[str] = None
    scene_prompt_name: Optional[str] = None
    emotion_prompt_name: Optional[str] = None
    plot_hook_prompt_name: Optional[str] = None


class PromptConfigUpdate(BaseModel):
    """更新提示词配置"""
    project_id: Optional[str] = None
    conflict_prompt_id: Optional[str] = None
    character_prompt_id: Optional[str] = None
    scene_prompt_id: Optional[str] = None
    emotion_prompt_id: Optional[str] = None
    plot_hook_prompt_id: Optional[str] = None


# ==================== 默认提示词名称映射 ====================

DEFAULT_PROMPT_NAMES = {
    "conflict": "breakdown_conflict_extraction",
    "character": "breakdown_character_analysis",
    "scene": "breakdown_scene_identification",
    "emotion": "breakdown_emotion_extraction",
    "plot_hook": "breakdown_plot_hooks",
}


# ==================== 辅助函数 ====================

async def _get_prompt_name(db: AsyncSession, prompt_id: Optional[str]) -> Optional[str]:
    """获取提示词显示名称"""
    if not prompt_id:
        return None
    result = await db.execute(
        select(AIResource.display_name).where(AIResource.id == uuid.UUID(prompt_id))
    )
    name = result.scalar_one_or_none()
    return name


async def _build_response(db: AsyncSession, config: Optional[UserPromptConfig], user_id: str, project_id: Optional[str] = None) -> PromptConfigResponse:
    """构建配置响应，包含提示词名称"""
    if config:
        return PromptConfigResponse(
            id=str(config.id),
            user_id=str(config.user_id),
            project_id=str(config.project_id) if config.project_id else None,
            conflict_prompt_id=str(config.conflict_prompt_id) if config.conflict_prompt_id else None,
            character_prompt_id=str(config.character_prompt_id) if config.character_prompt_id else None,
            scene_prompt_id=str(config.scene_prompt_id) if config.scene_prompt_id else None,
            emotion_prompt_id=str(config.emotion_prompt_id) if config.emotion_prompt_id else None,
            plot_hook_prompt_id=str(config.plot_hook_prompt_id) if config.plot_hook_prompt_id else None,
            conflict_prompt_name=await _get_prompt_name(db, str(config.conflict_prompt_id) if config.conflict_prompt_id else None),
            character_prompt_name=await _get_prompt_name(db, str(config.character_prompt_id) if config.character_prompt_id else None),
            scene_prompt_name=await _get_prompt_name(db, str(config.scene_prompt_id) if config.scene_prompt_id else None),
            emotion_prompt_name=await _get_prompt_name(db, str(config.emotion_prompt_id) if config.emotion_prompt_id else None),
            plot_hook_prompt_name=await _get_prompt_name(db, str(config.plot_hook_prompt_id) if config.plot_hook_prompt_id else None),
        )
    # 返回空配置（使用系统默认）
    return PromptConfigResponse(
        user_id=user_id,
        project_id=project_id,
    )


# ==================== API Endpoints ====================

@router.get("", response_model=PromptConfigResponse)
async def get_prompt_config(
    project_id: Optional[str] = Query(None, description="项目 ID，不传则获取全局配置"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户提示词配置

    优先返回项目级配置，如果没有则返回全局配置，都没有则返回空配置（使用系统默认）
    """
    config = None

    # 1. 尝试获取项目级配置
    if project_id:
        result = await db.execute(
            select(UserPromptConfig).where(
                and_(
                    UserPromptConfig.user_id == current_user.id,
                    UserPromptConfig.project_id == uuid.UUID(project_id)
                )
            )
        )
        config = result.scalar_one_or_none()

    # 2. 如果没有项目级配置，尝试获取全局配置
    if not config:
        result = await db.execute(
            select(UserPromptConfig).where(
                and_(
                    UserPromptConfig.user_id == current_user.id,
                    UserPromptConfig.project_id.is_(None)
                )
            )
        )
        config = result.scalar_one_or_none()

    return await _build_response(db, config, str(current_user.id), project_id)


@router.put("", response_model=PromptConfigResponse)
async def update_prompt_config(
    data: PromptConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """保存用户提示词配置

    如果配置不存在则创建，存在则更新
    """
    project_uuid = uuid.UUID(data.project_id) if data.project_id else None

    # 查找现有配置
    result = await db.execute(
        select(UserPromptConfig).where(
            and_(
                UserPromptConfig.user_id == current_user.id,
                UserPromptConfig.project_id == project_uuid if project_uuid else UserPromptConfig.project_id.is_(None)
            )
        )
    )
    config = result.scalar_one_or_none()

    if config:
        # 更新现有配置
        if data.conflict_prompt_id is not None:
            config.conflict_prompt_id = uuid.UUID(data.conflict_prompt_id) if data.conflict_prompt_id else None
        if data.character_prompt_id is not None:
            config.character_prompt_id = uuid.UUID(data.character_prompt_id) if data.character_prompt_id else None
        if data.scene_prompt_id is not None:
            config.scene_prompt_id = uuid.UUID(data.scene_prompt_id) if data.scene_prompt_id else None
        if data.emotion_prompt_id is not None:
            config.emotion_prompt_id = uuid.UUID(data.emotion_prompt_id) if data.emotion_prompt_id else None
        if data.plot_hook_prompt_id is not None:
            config.plot_hook_prompt_id = uuid.UUID(data.plot_hook_prompt_id) if data.plot_hook_prompt_id else None
    else:
        # 创建新配置
        config = UserPromptConfig(
            id=uuid.uuid4(),
            user_id=current_user.id,
            project_id=project_uuid,
            conflict_prompt_id=uuid.UUID(data.conflict_prompt_id) if data.conflict_prompt_id else None,
            character_prompt_id=uuid.UUID(data.character_prompt_id) if data.character_prompt_id else None,
            scene_prompt_id=uuid.UUID(data.scene_prompt_id) if data.scene_prompt_id else None,
            emotion_prompt_id=uuid.UUID(data.emotion_prompt_id) if data.emotion_prompt_id else None,
            plot_hook_prompt_id=uuid.UUID(data.plot_hook_prompt_id) if data.plot_hook_prompt_id else None,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)

    return await _build_response(db, config, str(current_user.id), data.project_id)


@router.post("/reset", response_model=PromptConfigResponse)
async def reset_prompt_config(
    project_id: Optional[str] = Query(None, description="项目 ID，不传则重置全局配置"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """重置提示词配置为系统默认

    删除用户的自定义配置，恢复使用系统默认提示词
    """
    project_uuid = uuid.UUID(project_id) if project_id else None

    result = await db.execute(
        select(UserPromptConfig).where(
            and_(
                UserPromptConfig.user_id == current_user.id,
                UserPromptConfig.project_id == project_uuid if project_uuid else UserPromptConfig.project_id.is_(None)
            )
        )
    )
    config = result.scalar_one_or_none()

    if config:
        await db.delete(config)
        await db.commit()

    return await _build_response(db, None, str(current_user.id), project_id)


@router.get("/defaults")
async def get_default_prompts(
    db: AsyncSession = Depends(get_db)
):
    """获取系统默认提示词列表

    返回各步骤的默认提示词 ID 和名称，供前端下拉选择
    """
    defaults = {}

    for step, name in DEFAULT_PROMPT_NAMES.items():
        result = await db.execute(
            select(AIResource).where(
                and_(
                    AIResource.name == name,
                    AIResource.is_builtin.is_(True),
                    AIResource.is_active.is_(True)
                )
            )
        )
        resource = result.scalar_one_or_none()
        if resource:
            defaults[step] = {
                "id": str(resource.id),
                "name": resource.name,
                "display_name": resource.display_name,
            }

    return {"defaults": defaults}


@router.get("/available")
async def get_available_prompts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户可用的拆解提示词列表

    包括系统内置和用户自己创建的提示词
    """
    from sqlalchemy import or_

    result = await db.execute(
        select(AIResource).where(
            and_(
                AIResource.category == "breakdown_prompt",
                AIResource.is_active.is_(True),
                or_(
                    AIResource.visibility == "public",
                    AIResource.owner_id == current_user.id
                )
            )
        ).order_by(AIResource.is_builtin.desc(), AIResource.created_at.desc())
    )
    resources = result.scalars().all()

    return {
        "prompts": [
            {
                "id": str(r.id),
                "name": r.name,
                "display_name": r.display_name,
                "description": r.description,
                "is_builtin": r.is_builtin,
            }
            for r in resources
        ]
    }

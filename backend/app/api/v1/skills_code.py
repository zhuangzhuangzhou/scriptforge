from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from app.core.database import get_db
from app.models.user import User
from app.models.skill_version import SkillVersion
from app.models.skill import Skill
from app.api.v1.auth import get_current_user

router = APIRouter()


def _can_access_skill(skill: Skill, user: User) -> bool:
    """检查用户是否有权限访问 Skill（用于代码版本管理）"""
    if skill.is_builtin:
        return True
    if skill.visibility == "public":
        return True
    if skill.owner_id == user.id:
        return True
    if skill.visibility == "shared":
        allowed_users = skill.allowed_users or []
        return str(user.id) in allowed_users
    return False


async def _get_skill_or_404(
    skill_id: str, current_user: User, db: AsyncSession
) -> Skill:
    """获取 Skill 并校验访问权限"""
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill不存在"
        )

    if not _can_access_skill(skill, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此Skill"
        )

    return skill


class SkillCodeCreateRequest(BaseModel):
    """创建Skill代码请求"""
    skill_id: str
    code: str
    description: Optional[str] = None
    parameters_schema: Optional[Dict[str, Any]] = None


class SkillCodeUpdateRequest(BaseModel):
    """更新Skill代码请求"""
    code: str
    description: Optional[str] = None
    changelog: Optional[str] = None
    parameters_schema: Optional[Dict[str, Any]] = None


@router.get("/skills/code")
async def get_skills_code(
    skill_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户的Skills代码列表"""
    if skill_id:
        # 校验 Skill 权限
        await _get_skill_or_404(skill_id, current_user, db)

        # 获取特定Skill的版本
        result = await db.execute(
            select(SkillVersion).where(
                SkillVersion.skill_id == skill_id,
                SkillVersion.user_id == current_user.id
            ).order_by(SkillVersion.version_number.desc())
        )
        versions = result.scalars().all()

        # 获取当前活跃版本
        active_result = await db.execute(
            select(SkillVersion).where(
                SkillVersion.skill_id == skill_id,
                SkillVersion.user_id == current_user.id,
                SkillVersion.is_active == True
            ).order_by(SkillVersion.version_number.desc())
        )
        active_version = active_result.scalar_one_or_none()

        return {
            "versions": versions,
            "active_version": active_version
        }

    # 获取用户所有Skills
    result = await db.execute(
        select(SkillVersion).where(
            SkillVersion.user_id == current_user.id
        ).distinct(SkillVersion.skill_id)
    )
    skills = result.scalars().all()

    return {"skills": skills}


@router.post("/skills/code")
async def create_skill_version(
    request: SkillCodeCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新版本的Skill代码"""
    skill = await _get_skill_or_404(request.skill_id, current_user, db)

    # 获取上一个版本号
    last_version_result = await db.execute(
        select(SkillVersion).where(
            SkillVersion.skill_id == request.skill_id,
            SkillVersion.user_id == current_user.id
        ).order_by(SkillVersion.version_number.desc())
    )
    last_version = last_version_result.scalar_one_or_none()

    version_number = 1
    version_str = "v1"
    if last_version:
        version_number = last_version.version_number + 1
        version_str = f"v{version_number}"

    # 创建新版本
    skill_version = SkillVersion(
        skill_id=request.skill_id,
        user_id=current_user.id,
        visibility=skill.visibility,
        owner_id=skill.owner_id or current_user.id,
        allowed_users=skill.allowed_users,
        version=version_str,
        version_number=version_number,
        code=request.code,
        description=request.description,
        parameters_schema=request.parameters_schema,
        is_active=True
    )

    # 将之前的活跃版本设为非活跃
    if last_version:
        last_version.is_active = False

    db.add(skill_version)
    await db.commit()
    await db.refresh(skill_version)

    return skill_version


@router.get("/skills/code/{version_id}")
async def get_skill_version(
    version_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取Skill版本详情"""
    result = await db.execute(
        select(SkillVersion).where(
            SkillVersion.id == version_id,
            SkillVersion.user_id == current_user.id
        )
    )
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill版本不存在"
        )

    return version


@router.put("/skills/code/{version_id}")
async def update_skill_version(
    version_id: str,
    request: SkillCodeUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新Skill代码（创建新版本）"""
    # 获取当前版本
    result = await db.execute(
        select(SkillVersion).where(
            SkillVersion.id == version_id,
            SkillVersion.user_id == current_user.id
        )
    )
    current_version = result.scalar_one_or_none()

    if not current_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill版本不存在"
        )

    # 创建新版本
    new_version = SkillVersion(
        skill_id=current_version.skill_id,
        user_id=current_user.id,
        visibility=current_version.visibility,
        owner_id=current_version.owner_id or current_user.id,
        allowed_users=current_version.allowed_users,
        version=f"v{current_version.version_number + 1}",
        version_number=current_version.version_number + 1,
        code=request.code,
        description=request.description or current_version.description,
        changelog=request.changelog,
        parameters_schema=request.parameters_schema or current_version.parameters_schema,
        source_version_id=current_version.id
    )

    # 设为活跃版本
    current_version.is_active = False
    new_version.is_active = True

    db.add(new_version)
    await db.commit()
    await db.refresh(new_version)

    return new_version


@router.get("/skills/code/{version_id}/history")
async def get_skill_version_history(
    version_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取Skill版本历史"""
    # 先定位目标版本，避免泄露其它Skill版本
    target_result = await db.execute(
        select(SkillVersion).where(
            SkillVersion.id == version_id,
            SkillVersion.user_id == current_user.id
        )
    )
    target_version = target_result.scalar_one_or_none()

    if not target_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill版本不存在"
        )

    result = await db.execute(
        select(SkillVersion).where(
            SkillVersion.skill_id == target_version.skill_id,
            SkillVersion.user_id == current_user.id
        ).order_by(SkillVersion.version_number.desc())
    )
    versions = result.scalars().all()

    return {"versions": versions}


@router.post("/skills/code/{version_id}/rollback")
async def rollback_skill_version(
    version_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """回滚到指定版本"""
    # 获取要回滚的版本
    result = await db.execute(
        select(SkillVersion).where(
            SkillVersion.id == version_id,
            SkillVersion.user_id == current_user.id
        )
    )
    target_version = result.scalar_one_or_none()

    if not target_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="版本不存在"
        )

    # 获取当前活跃版本
    active_result = await db.execute(
        select(SkillVersion).where(
            SkillVersion.skill_id == target_version.skill_id,
            SkillVersion.user_id == current_user.id,
            SkillVersion.is_active == True
        )
    )
    active_version = active_result.scalar_one_or_none()

    if active_version:
        active_version.is_active = False

    # 获取当前用户的最新版本号
    last_version_result = await db.execute(
        select(SkillVersion).where(
            SkillVersion.skill_id == target_version.skill_id,
            SkillVersion.user_id == current_user.id
        ).order_by(SkillVersion.version_number.desc())
    )
    last_version = last_version_result.scalar_one_or_none()
    next_version_number = (last_version.version_number + 1) if last_version else 1

    # 创建新版本，内容与目标版本相同
    rollback_version = SkillVersion(
        skill_id=target_version.skill_id,
        user_id=current_user.id,
        visibility=target_version.visibility,
        owner_id=target_version.owner_id or current_user.id,
        allowed_users=target_version.allowed_users,
        version=f"v{next_version_number}",
        version_number=next_version_number,
        code=target_version.code,
        description=f"回滚到 {target_version.version}",
        changelog=f"Rolled back to {target_version.version}",
        source_version_id=target_version.id,
        is_active=True
    )

    db.add(rollback_version)
    await db.commit()
    await db.refresh(rollback_version)

    return rollback_version


@router.post("/skills/code/{version_id}/test")
async def test_skill_code(
    version_id: str,
    test_input: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """测试Skill代码"""
    result = await db.execute(
        select(SkillVersion).where(
            SkillVersion.id == version_id,
            SkillVersion.user_id == current_user.id
        )
    )
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill版本不存在"
        )

    # TODO: 实现代码执行沙箱
    # 1. 动态导入代码
    # 2. 执行Skill的execute方法
    # 3. 返回执行结果

    return {
        "status": "testing",
        "message": "测试功能开发中",
        "input": test_input
    }

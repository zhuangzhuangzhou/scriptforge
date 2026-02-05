from typing import List, Optional, Dict, Any, Union
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID

from app.core.database import get_db
from app.core.storage import minio_access_key_client
from app.core.config import settings
from app.models.user import User
from app.models.project import Project
from app.models.chapter import Chapter
from app.models.batch import Batch
from app.models.split_rule import SplitRule
from app.api.v1.auth import get_current_user
from app.utils.file_parser import get_parser
from app.utils.chapter_splitter import ChapterSplitter
from app.utils.batch_divider import BatchDivider
from app.core.quota import QuotaService

router = APIRouter()

# 默认章节识别正则
DEFAULT_CHAPTER_PATTERN = r"第[一二三四五六七八九十百千\d]+章"


def normalize_chapter_split_rule(rule: Optional[Union[str, Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    """将前端传入的章节拆分规则标准化为字典"""
    if rule is None:
        return None

    if isinstance(rule, str):
        if rule == "auto":
            return {"type": "regex", "pattern": DEFAULT_CHAPTER_PATTERN}
        if rule == "blank_line":
            return {"type": "blank_line"}
        # 兜底：把字符串当成自定义正则
        return {"type": "regex", "pattern": rule}

    if isinstance(rule, dict):
        return rule

    return None


class ProjectCreate(BaseModel):
    name: str
    novel_type: Optional[str] = None
    description: Optional[str] = None
    batch_size: int = 5
    # 兼容两种方式：直接传规则 或 传规则ID
    chapter_split_rule: Optional[Union[str, Dict[str, Any]]] = None
    split_rule_id: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    novel_type: Optional[str] = None
    description: Optional[str] = None
    batch_size: Optional[int] = None
    chapter_split_rule: Optional[Union[str, Dict[str, Any]]] = None
    split_rule_id: Optional[str] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    novel_type: Optional[str] = None
    description: Optional[str] = None
    batch_size: int
    total_chapters: int = 0
    total_words: int = 0
    processed_chapters: int = 0
    status: str
    created_at: str
    updated_at: str

    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def validate_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

# ============ API 端点 ============

class BatchResponse(BaseModel):
    id: str
    project_id: str
    batch_number: int
    start_chapter: int
    end_chapter: int
    total_chapters: int
    total_words: int
    breakdown_status: str
    script_status: str

    class Config:
        from_attributes = True


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新项目"""
    quota_service = QuotaService(db)
    quota = await quota_service.check_project_quota(current_user)
    if not quota["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"项目配额已用尽，当前等级最多创建 {quota['limit']} 个项目"
        )

    new_project = Project(
        user_id=current_user.id,
        name=project_data.name,
        novel_type=project_data.novel_type,
        description=project_data.description,
        batch_size=project_data.batch_size,
        chapter_split_rule=normalize_chapter_split_rule(project_data.chapter_split_rule)
    )

    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    return new_project

@router.get("", response_model=List[ProjectResponse])
async def get_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """仅获取当前用户的项目"""
    result = await db.execute(
        select(Project).where(Project.user_id == current_user.id).order_by(Project.created_at.desc())
    )
    return result.scalars().all()

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """仅获取属于当前用户的指定项目"""
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == current_user.id)
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="未找到项目或无权访问")
    return project


@router.get("/{project_id}/batches", response_model=List[BatchResponse])
async def get_project_batches(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目批次列表"""
    # 验证项目归属
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    batches_result = await db.execute(
        select(Batch).where(Batch.project_id == project_id).order_by(Batch.batch_number)
    )
    batches = batches_result.scalars().all()
    return batches


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新项目信息"""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    # 更新字段
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.novel_type is not None:
        project.novel_type = project_data.novel_type
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.batch_size is not None:
        project.batch_size = project_data.batch_size
    if project_data.chapter_split_rule is not None:
        project.chapter_split_rule = normalize_chapter_split_rule(project_data.chapter_split_rule)
    # if project_data.split_rule_id is not None:
    #     project.split_rule_id = project_data.split_rule_id

    await db.commit()
    await db.refresh(project)

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """仅删除属于当前用户的项目"""
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == current_user.id)
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在或无权访问")

    await db.delete(project)
    await db.commit()
    return None

@router.post("/{project_id}/upload")
async def upload_novel_file(
    project_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """仅允许向自己的项目上传文件"""
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == current_user.id)
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在或无权访问")

    # 验证文件类型
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支持的文件类型")

    file_content = await file.read()
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    object_name = f"novels/{current_user.id}/{project_id}/{unique_filename}" # 路径增加 user_id 隔离

    import io
    minio_access_key_client.upload_file(io.BytesIO(file_content), object_name, file.content_type)

    project.original_file_path = object_name
    project.original_file_name = file.filename
    project.status = 'uploaded'
    await db.commit()

    return {"message": "上传成功", "project_id": str(project_id)}

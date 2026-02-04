from typing import List, Optional
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.core.storage import minio_access_key_client
from app.core.config import settings
from app.models.user import User
from app.models.project import Project
from app.models.chapter import Chapter
from app.models.batch import Batch
from app.api.v1.auth import get_current_user
from app.utils.file_parser import get_parser
from app.utils.chapter_splitter import ChapterSplitter
from app.utils.batch_divider import BatchDivider
from app.core.quota import QuotaService

router = APIRouter()


# Pydantic 模型
class ProjectCreate(BaseModel):
    name: str
    novel_type: Optional[str] = None
    description: Optional[str] = None
    batch_size: int = 5


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    novel_type: Optional[str] = None
    description: Optional[str] = None
    batch_size: Optional[int] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    novel_type: Optional[str]
    description: Optional[str]
    batch_size: int
    total_chapters: int
    total_words: int
    processed_chapters: int
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新项目"""
    # 检查项目配额
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
    """获取项目列表"""
    result = await db.execute(
        select(Project).where(Project.user_id == current_user.id).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目详情"""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    return project


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

    await db.commit()
    await db.refresh(project)

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除项目"""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    await db.delete(project)
    await db.commit()

    return None


@router.post("/{project_id}/upload")
async def upload_novel_file(
    project_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """上传小说文件"""
    # 验证项目存在且属于当前用户
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    # 验证文件类型
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型，仅支持: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # 读取文件内容
    file_content = await file.read()
    file_size = len(file_content)

    # 验证文件大小
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制（最大{settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB）"
        )

    # 生成唯一文件名
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    object_name = f"novels/{project_id}/{unique_filename}"

    # 上传文件到MinIO
    import io
    file_stream = io.BytesIO(file_content)
    minio_access_key_client.upload_file(file_stream, object_name, file.content_type)

    # 保存临时文件用于解析
    import tempfile
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        # 解析文件内容
        parser = get_parser(file_extension)
        text_content = parser.parse(temp_file_path)

        # 拆分章节
        splitter = ChapterSplitter(project.chapter_split_rule)
        chapters_data = splitter.split(text_content)
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    # 划分批次
    divider = BatchDivider(project.batch_size)
    batches_data = divider.divide(chapters_data)

    # 保存批次到数据库
    for batch_data in batches_data:
        new_batch = Batch(
            project_id=project.id,
            batch_number=batch_data['batch_number'],
            start_chapter=batch_data['start_chapter'],
            end_chapter=batch_data['end_chapter'],
            total_chapters=batch_data['total_chapters'],
            total_words=batch_data['total_words']
        )
        db.add(new_batch)
        await db.flush()

        # 保存该批次的章节
        for chapter_data in batch_data['chapters']:
            new_chapter = Chapter(
                project_id=project.id,
                batch_id=new_batch.id,
                chapter_number=chapter_data['chapter_number'],
                title=chapter_data['title'],
                content=chapter_data['content'],
                word_count=chapter_data['word_count']
            )
            db.add(new_chapter)

    # 更新项目信息
    project.original_file_path = object_name
    project.original_file_name = file.filename
    project.original_file_size = file_size
    project.original_file_type = file_extension
    project.total_chapters = len(chapters_data)
    project.total_words = sum(ch['word_count'] for ch in chapters_data)
    project.status = 'uploaded'

    await db.commit()

    return {
        "message": "文件上传成功",
        "total_chapters": len(chapters_data),
        "total_words": project.total_words,
        "total_batches": len(batches_data)
    }

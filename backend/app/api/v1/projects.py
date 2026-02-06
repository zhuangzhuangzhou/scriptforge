from typing import List, Optional, Dict, Any, Union
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, delete, update, cast, String
from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID

from app.core.database import get_db
from app.core.storage import minio_access_key_client
from app.core.config import settings
from app.models.user import User
from app.models.project import Project, ProjectLog
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
    chapter_split_rule: Optional[Union[str, Dict[str, Any]]] = None
    created_at: str
    updated_at: str

    # 文件信息
    original_file_name: Optional[str] = None
    original_file_size: Optional[int] = None
    original_file_type: Optional[str] = None
    original_file_path: Optional[str] = None

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

    @field_validator('id', 'project_id', mode='before')
    @classmethod
    def validate_id(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


class LogResponse(BaseModel):
    id: str
    type: str
    message: str
    detail: Optional[Dict[str, Any]] = None
    created_at: str

    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    @field_validator('created_at', mode='before')
    @classmethod
    def validate_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    class Config:
        from_attributes = True


class ChapterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chapter_number: int
    title: str
    content: Optional[str] = None
    word_count: int
    status: Optional[str] = "unprocessed"

    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v


class ChapterListResponse(BaseModel):
    items: List[ChapterResponse]
    total: int


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


@router.get("/{project_id}/logs", response_model=List[LogResponse])
async def get_project_logs(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目日志列表"""
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

    logs_result = await db.execute(
        select(ProjectLog).where(ProjectLog.project_id == project_id).order_by(ProjectLog.created_at.desc())
    )
    logs = logs_result.scalars().all()
    return logs


@router.get("/{project_id}/chapters", response_model=ChapterListResponse)
async def get_project_chapters(
    project_id: str,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目章节列表"""
    # 验证项目归属
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在或无权访问"
        )

    # 构建基础查询
    base_query = select(Chapter).where(Chapter.project_id == project_id)

    # 关键字搜索
    if keyword:
        base_query = base_query.where(
            or_(
                Chapter.title.ilike(f"%{keyword}%"),
                cast(Chapter.chapter_number, String).ilike(f"%{keyword}%")
            )
        )

    # 计算总数
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    chapters_result = await db.execute(
        base_query.order_by(Chapter.chapter_number)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = chapters_result.scalars().all()

    return {
        "items": items,
        "total": total
    }


@router.delete("/{project_id}/chapters/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chapter(
    project_id: UUID,
    chapter_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除指定章节"""
    # 验证项目归属
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在或无权访问")

    # 获取章节信息用于更新项目统计
    chapter = await db.get(Chapter, chapter_id)
    if not chapter or chapter.project_id != project_id:
        raise HTTPException(status_code=404, detail="章节不存在")

    word_count = chapter.word_count

    # 删除章节
    await db.execute(delete(Chapter).where(Chapter.id == chapter_id))

    # 更新项目统计
    project.total_chapters -= 1
    project.total_words -= word_count

    await db.commit()
    return None


@router.post("/{project_id}/chapters/upload")
async def upload_chapter(
    project_id: UUID,
    file: UploadFile = File(...),
    prev_chapter_id: Optional[UUID] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """上传并插入章节"""
    # 1. 验证项目
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在或无权访问")

    # 2. 读取内容
    try:
        content = (await file.read()).decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件读取失败: {str(e)}")

    word_count = len(content)

    # 3. 确定章节编号
    if prev_chapter_id:
        prev_chapter = await db.get(Chapter, prev_chapter_id)
        if not prev_chapter or prev_chapter.project_id != project_id:
            raise HTTPException(status_code=404, detail="前置章节不存在")

        new_chapter_number = prev_chapter.chapter_number + 1

        # 将后续章节编号后移
        await db.execute(
            update(Chapter)
            .where(Chapter.project_id == project_id, Chapter.chapter_number >= new_chapter_number)
            .values(chapter_number=Chapter.chapter_number + 1)
        )
    else:
        # 追加到末尾
        max_num_result = await db.execute(
            select(func.max(Chapter.chapter_number)).where(Chapter.project_id == project_id)
        )
        max_num = max_num_result.scalar() or 0
        new_chapter_number = max_num + 1

    # 4. 创建新章节
    new_chapter = Chapter(
        project_id=project_id,
        chapter_number=new_chapter_number,
        title=file.filename.rsplit('.', 1)[0],
        content=content,
        word_count=word_count
    )
    db.add(new_chapter)

    # 5. 更新项目统计
    project.total_chapters += 1
    project.total_words += word_count

    await db.commit()
    await db.refresh(new_chapter)

    return {
        "id": str(new_chapter.id),
        "chapter_number": new_chapter.chapter_number,
        "title": new_chapter.title
    }


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
    project.original_file_size = len(file_content)
    project.status = 'uploaded'
    await db.commit()

    return {"message": "上传成功", "project_id": str(project_id)}


@router.post("/{project_id}/split")
async def split_chapters(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    拆分小说章节
    状态流转: uploaded -> ready
    """
    # 1. 获取项目
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == current_user.id)
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 允许 ready 状态重试拆分
    if project.status not in ['uploaded', 'ready']:
        raise HTTPException(status_code=400, detail="项目状态不正确，请先上传文件")

    if not project.original_file_path:
        raise HTTPException(status_code=400, detail="源文件不存在")

    # 2. 从 MinIO 读取文件
    try:
        response = minio_access_key_client.get_object(project.original_file_path)
        content = response.read().decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")

    # 3. 执行拆分
    try:
        splitter = ChapterSplitter(project.chapter_split_rule)
        chapters_data = splitter.split(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"拆分失败: {str(e)}")

    if not chapters_data:
        raise HTTPException(status_code=400, detail="未识别到章节，请检查拆分规则")

    # 4. 清理旧数据并保存新章节
    # 清理该项目的所有旧章节和旧批次，确保状态重置
    await db.execute(delete(Batch).where(Batch.project_id == project_id))
    await db.execute(delete(Chapter).where(Chapter.project_id == project_id))

    # 批量插入新章节
    new_chapters = []
    total_words = 0
    for ch in chapters_data:
        new_chapters.append(Chapter(
            project_id=project_id,
            chapter_number=ch['chapter_number'],
            title=ch['title'],
            content=ch['content'],
            word_count=ch['word_count']
        ))
        total_words += ch['word_count']

    db.add_all(new_chapters)

    # 5. 更新项目状态和统计
    project.status = 'ready'
    project.total_chapters = len(new_chapters)
    project.total_words = total_words
    project.processed_chapters = 0  # 重置处理进度

    await db.commit()

    return {
        "message": f"成功拆分为 {len(new_chapters)} 章",
        "total_chapters": len(new_chapters),
        "total_words": total_words
    }


@router.post("/{project_id}/start")
async def start_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    启动项目（开始剧情分析）
    状态流转: ready -> parsing（仅允许一次）
    注意：分批逻辑移至 create-batches 接口
    """
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == current_user.id)
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 只允许 ready 状态启动，已启动的项目不能再次启动
    if project.status != 'ready':
        if project.status in ['parsing', 'scripting', 'completed']:
            raise HTTPException(status_code=400, detail="项目已启动")
        else:
            raise HTTPException(status_code=400, detail="项目尚未就绪（请先拆分章节）")

    # 验证有章节数据
    chapters_count = await db.execute(
        select(func.count()).select_from(Chapter).where(Chapter.project_id == project_id)
    )
    if chapters_count.scalar() == 0:
        raise HTTPException(status_code=400, detail="项目没有章节，请先拆分")

    # 仅更新状态，不进行分批（分批在进入 PLOT 页面时触发）
    project.status = 'parsing'

    await db.commit()
    await db.refresh(project)

    return {"status": "parsing", "message": "项目已启动"}


@router.post("/{project_id}/create-batches")
async def create_batches(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    按需创建批次（幂等接口，进入 PLOT 页面时调用）
    如果批次已存在则跳过创建
    """
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == current_user.id)
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 检查是否已有批次
    existing = await db.execute(
        select(func.count()).select_from(Batch).where(Batch.project_id == project_id)
    )
    if existing.scalar() > 0:
        return {"message": "批次已存在", "created": False}

    # 获取所有章节
    chapters_result = await db.execute(
        select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.chapter_number)
    )
    chapters = chapters_result.scalars().all()

    if not chapters:
        raise HTTPException(status_code=400, detail="项目没有章节，请先拆分")

    # 执行分批逻辑
    chapters_data = [
        {"chapter_number": c.chapter_number, "word_count": c.word_count, "id": c.id}
        for c in chapters
    ]

    divider = BatchDivider(batch_size=project.batch_size)
    batches_data = divider.divide(chapters_data)

    # 创建新批次并关联章节
    for b_data in batches_data:
        new_batch = Batch(
            project_id=project_id,
            batch_number=b_data['batch_number'],
            start_chapter=b_data['start_chapter'],
            end_chapter=b_data['end_chapter'],
            total_chapters=b_data['total_chapters'],
            total_words=b_data['total_words']
        )
        db.add(new_batch)
        await db.flush()

        # 更新章节的 batch_id
        chapter_ids = [c['id'] for c in b_data['chapters']]
        await db.execute(
            update(Chapter).where(Chapter.id.in_(chapter_ids)).values(batch_id=new_batch.id)
        )

    await db.commit()

    return {"message": "分批完成", "batch_count": len(batches_data), "created": True}


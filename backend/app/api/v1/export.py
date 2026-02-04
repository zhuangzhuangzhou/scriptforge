from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from io import BytesIO
import zipfile
import urllib.parse

from app.core.database import get_db
from app.models.user import User
from app.models.script import Script
from app.models.project import Project
from app.api.v1.auth import get_current_user
from app.utils.pdf_exporter import PDFExporter
from app.utils.word_exporter import WordExporter

router = APIRouter()


class ExportSingleRequest(BaseModel):
    """导出单集请求"""
    script_id: str
    format: str = "pdf"  # pdf, docx, txt


class ExportBatchRequest(BaseModel):
    """批量导出请求"""
    project_id: str
    format: str = "pdf"


@router.post("/single")
async def export_single(
    request: ExportSingleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """导出单集"""
    # 验证剧本存在
    result = await db.execute(select(Script).where(Script.id == request.script_id))
    script = result.scalar_one_or_none()

    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="剧本不存在"
        )

    # 权限检查：确保剧本所属项目属于当前用户
    project_result = await db.execute(select(Project).where(Project.id == script.project_id))
    project = project_result.scalar_one_or_none()

    if not project or project.user_id != current_user.id:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该剧本"
        )

    # 准备数据
    script_data = {
        "title": script.title,
        "content": script.content
    }

    # 根据格式导出
    if request.format == "pdf":
        exporter = PDFExporter()
        file_stream = exporter.export_script(script_data)
        media_type = "application/pdf"
        ext = "pdf"
    elif request.format == "docx":
        exporter = WordExporter()
        file_stream = exporter.export_script(script_data)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的导出格式: {request.format}"
        )

    # 设置文件名 (处理中文文件名)
    filename = f"{script.title}.{ext}"
    encoded_filename = urllib.parse.quote(filename)

    return StreamingResponse(
        file_stream,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )


@router.post("/batch")
async def export_batch(
    request: ExportBatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量导出（打包）"""
    # 检查项目权限
    project_result = await db.execute(select(Project).where(Project.id == request.project_id))
    project = project_result.scalar_one_or_none()

    if not project:
         raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    if project.user_id != current_user.id:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该项目"
        )

    # 获取项目的所有剧本
    result = await db.execute(
        select(Script).where(Script.project_id == request.project_id).order_by(Script.episode_number)
    )
    scripts = result.scalars().all()

    if not scripts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该项目没有剧本"
        )

    # 创建内存中的ZIP文件
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for script in scripts:
            script_data = {
                "title": script.title,
                "content": script.content
            }

            file_content = None
            ext = ""

            if request.format == "pdf":
                exporter = PDFExporter()
                file_stream = exporter.export_script(script_data)
                file_content = file_stream.getvalue()
                ext = "pdf"
            elif request.format == "docx":
                exporter = WordExporter()
                file_stream = exporter.export_script(script_data)
                file_content = file_stream.getvalue()
                ext = "docx"
            else:
                 # 暂时跳过不支持的格式，或者报错
                 continue

            # 添加到ZIP
            filename = f"第{script.episode_number}集_{script.title}.{ext}"
            zip_file.writestr(filename, file_content)

    zip_buffer.seek(0)

    # 设置ZIP文件名
    zip_filename = f"{project.name}_剧本导出.zip"
    encoded_filename = urllib.parse.quote(zip_filename)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )

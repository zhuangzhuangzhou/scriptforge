from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from io import BytesIO
import zipfile
from zipfile import ZipInfo
import urllib.parse
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.script import Script
from app.models.project import Project
from app.api.v1.auth import get_current_user
from app.utils.pdf_exporter import PDFExporter
from app.utils.word_exporter import WordExporter

logger = logging.getLogger(__name__)

router = APIRouter()


class ExportSingleRequest(BaseModel):
    """导出单集请求"""
    script_id: str
    format: str = "pdf"  # pdf, docx, txt


class ExportBatchRequest(BaseModel):
    """批量导出请求"""
    project_id: str
    format: str = "pdf"
    merged: bool = False  # 是否合并为一份文档


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

    # 设置文件名 (处理中文文件名)，格式：项目名称_x集
    filename = f"{project.name}_{script.episode_number}集.{ext}"
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
    """批量导出（打包或合并）"""
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

    # 获取项目的所有剧本（只获取当前版本）
    result = await db.execute(
        select(Script).where(
            Script.project_id == request.project_id,
            Script.is_current == True
        ).order_by(Script.episode_number)
    )
    scripts = result.scalars().all()

    if not scripts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该项目没有剧本"
        )

    logger.info(f"开始批量导出: 项目={project.name}, 剧本数={len(scripts)}, 格式={request.format}, 合并={request.merged}")

    # 合并导出为一份文档
    if request.merged:
        scripts_data = [
            {
                "episode_number": script.episode_number,
                "title": script.title,
                "content": script.content
            }
            for script in scripts
        ]

        if request.format == "docx":
            exporter = WordExporter()
            file_stream = exporter.export_merged(project.name, scripts_data)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = "docx"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="合并导出目前仅支持 docx 格式"
            )

        filename = f"{project.name}_全集剧本.{ext}"
        encoded_filename = urllib.parse.quote(filename)

        logger.info(f"合并导出完成: 项目={project.name}")

        return StreamingResponse(
            file_stream,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )

    # 分集导出为 ZIP
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for i, script in enumerate(scripts):
            logger.info(f"导出第 {i+1}/{len(scripts)} 集: {script.title}")

            script_data = {
                "title": script.title,
                "content": script.content
            }

            file_content = None
            ext = ""

            try:
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
                    continue
            except Exception as e:
                logger.error(f"导出第 {script.episode_number} 集失败: {e}")
                continue

            # 添加到ZIP，使用 项目名称_x集 格式
            filename = f"{project.name}_{script.episode_number}集.{ext}"
            # 使用 ZipInfo 并设置 UTF-8 标志位，避免中文文件名乱码
            zip_info = ZipInfo(filename)
            zip_info.flag_bits |= 0x800  # UTF-8 编码标志
            zip_file.writestr(zip_info, file_content)

    logger.info(f"批量导出完成: 项目={project.name}")
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

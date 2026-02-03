from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.models.script import Script
from app.api.v1.auth import get_current_user

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

    # TODO: 实现导出逻辑
    return {"message": "导出功能开发中"}


@router.post("/batch")
async def export_batch(
    request: ExportBatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量导出（打包）"""
    # 获取项目的所有剧本
    result = await db.execute(
        select(Script).where(Script.project_id == request.project_id)
    )
    scripts = result.scalars().all()

    if not scripts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该项目没有剧本"
        )

    # TODO: 实现批量导出逻辑
    return {"message": "批量导出功能开发中"}

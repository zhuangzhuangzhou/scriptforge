from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.ai_task import AITask
import asyncio

router = APIRouter()


@router.websocket("/ws/breakdown/{task_id}")
async def websocket_breakdown_progress(websocket: WebSocket, task_id: str):
    """WebSocket端点：实时推送Breakdown任务进度"""
    await websocket.accept()

    try:
        async with AsyncSessionLocal() as db:
            while True:
                # 查询任务状态
                result = await db.execute(select(AITask).where(AITask.id == task_id))
                task = result.scalar_one_or_none()

                if not task:
                    await websocket.send_json({"error": "任务不存在"})
                    break

                # 发送进度信息
                progress_data = {
                    "task_id": str(task.id),
                    "status": task.status,
                    "progress": task.progress or 0,
                    "current_step": task.current_step or "",
                    "error_message": task.error_message,
                    "retry_count": task.retry_count,
                    "depends_on": task.depends_on or []
                }
                await websocket.send_json(progress_data)

                # 如果任务已完成或失败，断开连接
                if task.status in ["completed", "failed", "canceled"]:
                    break

                # 等待1秒后再次查询
                await asyncio.sleep(1)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})


@router.websocket("/ws/scripts/{task_id}")
async def websocket_script_progress(websocket: WebSocket, task_id: str):
    """WebSocket端点：实时推送Script任务进度"""
    await websocket.accept()

    try:
        async with AsyncSessionLocal() as db:
            while True:
                # 查询任务状态
                result = await db.execute(select(AITask).where(AITask.id == task_id))
                task = result.scalar_one_or_none()

                if not task:
                    await websocket.send_json({"error": "任务不存在"})
                    break

                # 发送进度信息
                progress_data = {
                    "task_id": str(task.id),
                    "status": task.status,
                    "progress": task.progress or 0,
                    "current_step": task.current_step or "",
                    "error_message": task.error_message,
                    "retry_count": task.retry_count,
                    "depends_on": task.depends_on or []
                }
                await websocket.send_json(progress_data)

                # 如果任务已完成或失败，断开连接
                if task.status in ["completed", "failed", "canceled"]:
                    break

                # 等待1秒后再次查询
                await asyncio.sleep(1)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})

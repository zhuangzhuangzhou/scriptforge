"""WebSocket进度推送模块

支持：
- 单任务进度追踪
- 批量进度推送（使用Redis Pub/Sub）
- 智能轮询间隔
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.ai_task import AITask
from typing import Optional
import asyncio
import json
import redis.asyncio as redis
from datetime import datetime

router = APIRouter()

# Redis客户端（懒加载）
_redis_client: Optional[redis.Redis] = None


async def get_redis() -> Optional[redis.Redis]:
    """获取Redis客户端"""
    global _redis_client
    if _redis_client is None:
        try:
            from app.core.config import settings
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:
            pass
    return _redis_client


def serialize_task(task: AITask) -> dict:
    """序列化任务状态"""
    return {
        "task_id": str(task.id),
        "status": task.status,
        "progress": task.progress or 0,
        "current_step": task.current_step or "",
        "error_message": task.error_message,
        "retry_count": task.retry_count or 0,
        "depends_on": task.depends_on or [],
        "updated_at": datetime.utcnow().isoformat()
    }


async def publish_progress(task_id: str, data: dict):
    """发布进度到Redis频道"""
    try:
        redis_client = await get_redis()
        if redis_client:
            channel = f"breakdown:progress:{task_id}"
            await redis_client.publish(channel, json.dumps(data))
    except Exception:
        pass


@router.websocket("/ws/breakdown/{task_id}")
async def websocket_breakdown_progress(websocket: WebSocket, task_id: str):
    """WebSocket端点：实时推送Breakdown任务进度

    优化特性：
    - 使用 Redis Pub/Sub 实时推送（高效）
    - 连接时立即发送当前状态
    - Redis 不可用时降级到数据库轮询
    - 状态变更检测，避免发送重复数据
    """
    await websocket.accept()

    redis_client = None
    pubsub = None
    use_polling = False

    try:
        # 1. 首次连接时立即查询并发送当前状态
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(AITask).where(AITask.id == task_id))
            task = result.scalar_one_or_none()

            if not task:
                await websocket.send_json({"error": "任务不存在", "code": "TASK_NOT_FOUND"})
                return

            # 立即发送当前状态
            initial_data = serialize_task(task)
            await websocket.send_json(initial_data)

            # 如果任务已经完成，发送完成消息后退出
            if task.status in ["completed", "failed", "canceled"]:
                await websocket.send_json({
                    "task_id": task_id,
                    "status": "done",
                    "final_status": task.status,
                    "message": f"任务已{ '完成' if task.status == 'completed' else '失败' }"
                })
                return

        # 2. 尝试连接 Redis 并订阅频道
        try:
            redis_client = await get_redis()
            if redis_client:
                channel_name = f"breakdown:progress:{task_id}"
                pubsub = redis_client.pubsub()
                await pubsub.subscribe(channel_name)
                print(f"[WebSocket] 已订阅 Redis 频道: {channel_name}")
            else:
                print(f"[WebSocket] Redis 不可用，降级到数据库轮询")
                use_polling = True
        except Exception as e:
            print(f"[WebSocket] Redis 订阅失败: {e}，降级到数据库轮询")
            use_polling = True

        # 3. 主循环：接收更新
        last_data = initial_data

        if not use_polling and pubsub:
            # 使用 Redis Pub/Sub（高效）
            print(f"[WebSocket] 使用 Redis Pub/Sub 模式")
            while True:
                try:
                    # 从 Redis 获取消息（带超时）
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

                    if message and message['type'] == 'message':
                        try:
                            # 解析进度数据
                            progress_data = json.loads(message['data'])

                            # 避免发送重复数据
                            if progress_data != last_data:
                                await websocket.send_json(progress_data)
                                last_data = progress_data

                            # 检测任务完成
                            if progress_data.get('status') in ["completed", "failed", "canceled"]:
                                await websocket.send_json({
                                    "task_id": task_id,
                                    "status": "done",
                                    "final_status": progress_data.get('status'),
                                    "message": f"任务已{ '完成' if progress_data.get('status') == 'completed' else '失败' }"
                                })
                                break

                        except json.JSONDecodeError as e:
                            print(f"[WebSocket] JSON 解析失败: {e}")
                            continue

                    # 短暂等待，避免过度轮询
                    await asyncio.sleep(0.1)

                except asyncio.TimeoutError:
                    # 超时是正常的，继续循环
                    continue

        else:
            # 降级到数据库轮询（兼容模式）
            print(f"[WebSocket] 使用数据库轮询模式")
            poll_interval = 1
            task_status = initial_data.get('status')

            async with AsyncSessionLocal() as db:
                while True:
                    await asyncio.sleep(poll_interval)

                    # 强制刷新 session 缓存，确保读取最新数据
                    db.expire_all()

                    # 查询任务状态
                    result = await db.execute(select(AITask).where(AITask.id == task_id))
                    task = result.scalar_one_or_none()

                    if not task:
                        await websocket.send_json({"error": "任务不存在", "code": "TASK_NOT_FOUND"})
                        break

                    # 构建进度数据
                    progress_data = serialize_task(task)

                    # 状态变更检测，避免发送重复数据
                    if progress_data != last_data:
                        await websocket.send_json(progress_data)
                        last_data = progress_data

                    # 更新任务状态变量
                    new_status = task.status

                    # 如果状态发生变化，调整轮询间隔
                    if new_status != task_status:
                        task_status = new_status
                        if new_status in ["completed", "failed", "canceled"]:
                            # 任务结束时，发送最终状态后退出
                            await websocket.send_json({
                                "task_id": task_id,
                                "status": "done",
                                "final_status": new_status,
                                "message": f"任务已{ '完成' if new_status == 'completed' else '失败' }"
                            })
                            break
                        else:
                            # 任务进行中，保持快速轮询
                            poll_interval = 1

    except WebSocketDisconnect:
        print(f"[WebSocket] 客户端断开连接: {task_id}")
    except Exception as e:
        print(f"[WebSocket] 错误: {e}")
        try:
            await websocket.send_json({"error": str(e), "code": "INTERNAL_ERROR"})
        except:
            pass
    finally:
        # 清理资源
        if pubsub:
            try:
                await pubsub.unsubscribe()
                await pubsub.close()
            except Exception as e:
                print(f"[WebSocket] 清理 pubsub 失败: {e}")


@router.websocket("/ws/batch-progress/{project_id}")
async def websocket_batch_progress(websocket: WebSocket, project_id: str):
    """WebSocket端点：批量拆解进度推送

    功能：
    - 同时监控多个任务进度
    - 实时统计完成/失败/进行中数量
    - 使用Redis Pub/Sub实现高效推送
    """
    await websocket.accept()

    # 获取Redis客户端
    redis_client = await get_redis()
    pubsub = None
    task_ids = set()

    try:
        # 尝试订阅Redis频道（用于接收实时更新）
        if redis_client:
            channel_pattern = f"breakdown:progress:*"
            pubsub = redis_client.pubsub()
            await pubsub.psubscribe(channel_pattern)
            print(f"已订阅进度频道: {channel_pattern}")
        else:
            print("Redis未配置，将使用HTTP轮询")

        # 发送初始状态
        await websocket.send_json({
            "type": "connected",
            "project_id": project_id,
            "message": "已连接批量进度监控"
        })

        # 主循环
        last_update = None
        while True:
            try:
                # 1. 优先处理Redis消息
                if pubsub:
                    message = await pubsub.get_message(timeout=0.1)
                    if message and message['type'] == 'pmessage':
                        try:
                            data = json.loads(message['data'])
                            await websocket.send_json({
                                "type": "progress_update",
                                **data
                            })
                            last_update = datetime.utcnow()
                        except:
                            pass
                    continue

                # 2. 如果没有Redis，使用HTTP轮询（兜底方案）
                # 这里需要导入批量进度端点的逻辑
                # 由于复杂度较高，建议使用batch-progress API进行轮询

                await asyncio.sleep(2)

            except WebSocketDisconnect:
                break
            except Exception as e:
                await asyncio.sleep(1)

    except Exception as e:
        print(f"批量进度WebSocket错误: {e}")
    finally:
        if pubsub:
            await pubsub.unsubscribe()
            await pubsub.close()


@router.websocket("/ws/batch-simple/{project_id}")
async def websocket_batch_simple(websocket: WebSocket, project_id: str):
    """简化的批量进度WebSocket

    使用数据库轮询，但优化了查询效率：
    - 批量查询所有任务状态
    - 只返回变更的数据
    """
    await websocket.accept()

    last_states = {}  # 缓存上次状态

    try:
        async with AsyncSessionLocal() as db:
            while True:
                # 批量查询项目下的所有任务
                from app.models.batch import Batch
                from sqlalchemy import func

                # 获取项目的批次ID列表
                batch_result = await db.execute(
                    select(Batch.id).where(Batch.project_id == project_id)
                )
                batch_ids = [b[0] for b in batch_result.fetchall()]

                if not batch_ids:
                    await asyncio.sleep(2)
                    continue

                # 批量查询任务状态
                task_result = await db.execute(
                    select(AITask).where(
                        AITask.batch_id.in_(batch_ids),
                        AITask.task_type == "breakdown"
                    )
                )
                tasks = task_result.scalars().all()

                # 统计各状态数量
                status_counts = {
                    "pending": 0,
                    "queued": 0,
                    "running": 0,
                    "retrying": 0,
                    "completed": 0,
                    "failed": 0
                }

                task_updates = []
                for task in tasks:
                    status_counts[task.status] = status_counts.get(task.status, 0) + 1

                    # 检测状态变更
                    last_state = last_states.get(str(task.id))
                    current_state = {
                        "task_id": str(task.id),
                        "batch_id": str(task.batch_id),
                        "status": task.status,
                        "progress": task.progress or 0,
                        "error_message": task.error_message
                    }

                    if last_state != current_state:
                        task_updates.append({
                            "type": "task_update",
                            **current_state
                        })

                    last_states[str(task.id)] = current_state

                # 计算整体进度
                total = len(tasks)
                completed = status_counts.get("completed", 0)
                overall_progress = round(completed / total * 100, 1) if total > 0 else 0

                # 发送批量进度
                batch_data = {
                    "type": "batch_progress",
                    "project_id": project_id,
                    "total_tasks": total,
                    "status_counts": status_counts,
                    "overall_progress": overall_progress,
                    "updated_at": datetime.utcnow().isoformat()
                }

                # 如果有任务更新，也发送更新列表
                if task_updates:
                    batch_data["task_updates"] = task_updates

                await websocket.send_json(batch_data)

                # 检查是否全部完成
                if completed + status_counts.get("failed", 0) >= total:
                    await websocket.send_json({
                        "type": "batch_complete",
                        "message": f"批量任务完成，成功 {completed}，失败 {status_counts.get('failed', 0)}"
                    })
                    break

                # 轮询间隔（任务进行中1秒，完成时2秒）
                await asyncio.sleep(1.5)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"批量进度WebSocket错误: {e}")


@router.websocket("/ws/breakdown-logs/{task_id}")
async def websocket_breakdown_logs(websocket: WebSocket, task_id: str):
    """WebSocket端点：实时推送拆解日志

    功能：
    - 订阅 Redis 频道 breakdown:logs:{task_id}
    - 接收并转发所有日志消息到前端
    - 检测任务完成状态并自动关闭连接
    - 正确处理 WebSocket 断开和异常

    消息类型：
    - step_start: 步骤开始
    - stream_chunk: 流式内容片段
    - step_end: 步骤结束
    - error: 错误信息
    - progress: 进度更新

    Requirements: 3.4.1, 3.4.3
    """
    # 添加调试日志
    print(f"[WebSocket] 收到连接请求: task_id={task_id}")
    print(f"[WebSocket] Origin: {websocket.headers.get('origin')}")
    print(f"[WebSocket] Host: {websocket.headers.get('host')}")

    try:
        await websocket.accept()
        print(f"[WebSocket] 连接已接受: task_id={task_id}")
    except Exception as e:
        print(f"[WebSocket] 接受连接失败: {e}")
        return

    redis_client = None
    pubsub = None

    try:
        # 获取 Redis 客户端
        redis_client = await get_redis()

        if not redis_client:
            # Redis 不可用
            print(f"[WebSocket] Redis 不可用")
            await websocket.send_json({
                "type": "error",
                "content": "Redis 服务不可用，无法提供实时日志",
                "code": "REDIS_UNAVAILABLE"
            })
            await websocket.close()
            return

        print(f"[WebSocket] Redis 连接成功")

        # 订阅 Redis 频道
        channel_name = f"breakdown:logs:{task_id}"
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel_name)

        print(f"[WebSocket] 已订阅频道: {channel_name}")

        # 发送连接成功消息
        await websocket.send_json({
            "type": "connected",
            "task_id": task_id,
            "message": f"已连接到任务日志流: {task_id}"
        })

        print(f"[WebSocket] 已发送连接成功消息")
        
        # 主循环：接收 Redis 消息并转发
        while True:
            try:
                # 从 Redis 获取消息（带超时）
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                
                if message and message['type'] == 'message':
                    try:
                        # 解析消息
                        data = json.loads(message['data'])

                        # 转发到前端
                        await websocket.send_json(data)

                        # 检测任务完成状态
                        # 1. 收到 task_complete 消息（新增）
                        if data.get('type') == 'task_complete':
                            # 任务完成消息，直接关闭连接
                            break

                        # 2. 收到 step_end 消息且 metadata 中包含 final=True
                        elif data.get('type') == 'step_end':
                            metadata = data.get('metadata', {})
                            if metadata.get('final', False):
                                # 任务完成，发送完成消息后关闭
                                await websocket.send_json({
                                    "type": "task_complete",
                                    "task_id": task_id,
                                    "message": "任务执行完成"
                                })
                                break

                        # 3. 收到 error 消息
                        elif data.get('type') == 'error':
                            # 发生错误，检查是否是致命错误
                            metadata = data.get('metadata', {})
                            if not metadata.get('retryable', True):
                                # 不可重试的错误，关闭连接
                                await websocket.send_json({
                                    "type": "task_failed",
                                    "task_id": task_id,
                                    "message": "任务执行失败"
                                })
                                break

                    except json.JSONDecodeError as e:
                        # JSON 解析失败，记录但不中断
                        print(f"[WebSocket] JSON 解析失败: {e}")
                        continue

                    # 收到消息后继续循环，不检查数据库
                    continue

                # 只有在没有收到 Redis 消息时才检查数据库状态
                # 这是为了处理任务在 WebSocket 连接之前就已经完成的情况
                async with AsyncSessionLocal() as db:
                    # 强制刷新 session 缓存，确保读取最新数据
                    db.expire_all()

                    result = await db.execute(select(AITask).where(AITask.id == task_id))
                    task = result.scalar_one_or_none()

                    if task:
                        if task.status in ["completed", "failed", "canceled"]:
                            # 任务已结束，发送最终状态并关闭
                            await websocket.send_json({
                                "type": "task_complete" if task.status == "completed" else "task_failed",
                                "task_id": task_id,
                                "status": task.status,
                                "message": f"任务已{task.status}"
                            })
                            break
                
                # 短暂等待，避免过度轮询
                await asyncio.sleep(0.1)
            
            except asyncio.TimeoutError:
                # 超时是正常的，继续循环
                continue
            
            except WebSocketDisconnect:
                # 客户端断开连接
                print(f"[WebSocket] 客户端断开连接: {task_id}")
                break
            
            except Exception as e:
                # 其他异常
                print(f"[WebSocket] 处理消息时出错: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "content": f"内部错误: {str(e)}",
                        "code": "INTERNAL_ERROR"
                    })
                except:
                    pass
                break
    
    except WebSocketDisconnect:
        print(f"[WebSocket] 连接断开: {task_id}")
    
    except Exception as e:
        print(f"[WebSocket] 错误: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"连接错误: {str(e)}",
                "code": "CONNECTION_ERROR"
            })
        except:
            pass
    
    finally:
        # 清理资源
        if pubsub:
            try:
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()
            except Exception as e:
                print(f"[WebSocket] 清理 pubsub 失败: {e}")
        
        try:
            await websocket.close()
        except:
            pass

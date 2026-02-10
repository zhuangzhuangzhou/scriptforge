"""Redis 日志发布服务

用于将 Breakdown 任务的执行日志实时发布到 Redis Pub/Sub，
供 WebSocket 端点订阅并推送到前端。

设计要点：
- 使用同步 Redis 客户端（适配 Celery worker 环境）
- 频道命名规范：breakdown:logs:{task_id}
- 统一的 JSON 消息格式
- 发布失败时静默处理，不中断任务执行
"""
import json
import redis
from datetime import datetime
from typing import Optional, Dict, Any
from app.core.config import settings


class RedisLogPublisher:
    """Redis 日志发布器（同步版本）
    
    用于在 Celery worker 中发布实时日志到 Redis Pub/Sub。
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """初始化 Redis 连接
        
        Args:
            redis_url: Redis 连接 URL，默认从配置读取
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self._client: Optional[redis.Redis] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """初始化 Redis 客户端"""
        try:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            self._client.ping()
        except Exception as e:
            print(f"[RedisLogPublisher] 初始化失败: {e}")
            self._client = None
    
    def _get_channel_name(self, task_id: str) -> str:
        """获取频道名称
        
        Args:
            task_id: 任务 ID
            
        Returns:
            频道名称，格式为 breakdown:logs:{task_id}
        """
        return f"breakdown:logs:{task_id}"
    
    def _build_message(
        self,
        message_type: str,
        task_id: str,
        step_name: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> dict:
        """构建统一格式的消息
        
        Args:
            message_type: 消息类型（step_start, stream_chunk, step_end, error, progress）
            task_id: 任务 ID
            step_name: 步骤名称（可选）
            content: 消息内容（可选）
            metadata: 元数据（可选）
            
        Returns:
            消息字典
        """
        message = {
            "type": message_type,
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if step_name is not None:
            message["step_name"] = step_name
        
        if content is not None:
            message["content"] = content
        
        if metadata is not None:
            message["metadata"] = metadata
        
        return message
    
    def publish_log(self, task_id: str, message: dict) -> None:
        """发布日志消息到 Redis
        
        Args:
            task_id: 任务 ID
            message: 消息字典（包含 type, content 等字段）
        """
        if not self._client:
            # Redis 不可用时静默失败
            return
        
        try:
            channel = self._get_channel_name(task_id)
            message_json = json.dumps(message, ensure_ascii=False)
            self._client.publish(channel, message_json)
        except Exception as e:
            # 发布失败不应中断任务执行
            print(f"[RedisLogPublisher] 发布消息失败: {e}")
    
    def publish_step_start(
        self,
        task_id: str,
        step_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """发布步骤开始消息
        
        Args:
            task_id: 任务 ID
            step_name: 步骤名称（如 "提取冲突"）
            metadata: 元数据（如进度信息）
        """
        message = self._build_message(
            message_type="step_start",
            task_id=task_id,
            step_name=step_name,
            content=f"开始执行: {step_name}",
            metadata=metadata
        )
        self.publish_log(task_id, message)
    
    def publish_stream_chunk(
        self,
        task_id: str,
        step_name: str,
        chunk: str
    ) -> None:
        """发布流式内容片段
        
        Args:
            task_id: 任务 ID
            step_name: 步骤名称
            chunk: 内容片段
        """
        message = self._build_message(
            message_type="stream_chunk",
            task_id=task_id,
            step_name=step_name,
            content=chunk
        )
        self.publish_log(task_id, message)
    
    def publish_step_end(
        self,
        task_id: str,
        step_name: str,
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """发布步骤结束消息
        
        Args:
            task_id: 任务 ID
            step_name: 步骤名称
            result: 结果信息（如统计数据）
        """
        message = self._build_message(
            message_type="step_end",
            task_id=task_id,
            step_name=step_name,
            content=f"完成: {step_name}",
            metadata=result
        )
        self.publish_log(task_id, message)
    
    def publish_error(
        self,
        task_id: str,
        error_message: str,
        error_code: Optional[str] = None,
        step_name: Optional[str] = None
    ) -> None:
        """发布错误消息
        
        Args:
            task_id: 任务 ID
            error_message: 错误信息
            error_code: 错误代码（可选）
            step_name: 步骤名称（可选）
        """
        metadata = {}
        if error_code:
            metadata["error_code"] = error_code
        
        message = self._build_message(
            message_type="error",
            task_id=task_id,
            step_name=step_name,
            content=error_message,
            metadata=metadata if metadata else None
        )
        self.publish_log(task_id, message)
    
    def publish_progress(
        self,
        task_id: str,
        progress: int,
        current_step: int,
        total_steps: int,
        step_name: Optional[str] = None
    ) -> None:
        """发布进度更新消息
        
        Args:
            task_id: 任务 ID
            progress: 进度百分比（0-100）
            current_step: 当前步骤编号
            total_steps: 总步骤数
            step_name: 步骤名称（可选）
        """
        metadata = {
            "progress": progress,
            "current_step": current_step,
            "total_steps": total_steps
        }
        
        message = self._build_message(
            message_type="progress",
            task_id=task_id,
            step_name=step_name,
            content=f"进度: {progress}% ({current_step}/{total_steps})",
            metadata=metadata
        )
        self.publish_log(task_id, message)
    
    def close(self) -> None:
        """关闭 Redis 连接"""
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                print(f"[RedisLogPublisher] 关闭连接失败: {e}")
            finally:
                self._client = None

"""Redis 日志发布服务单元测试

测试 RedisLogPublisher 类的所有功能：
- 消息格式正确性
- 发布成功场景
- Redis 不可用时的降级处理
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from app.core.redis_log_publisher import RedisLogPublisher


class TestRedisLogPublisher:
    """RedisLogPublisher 单元测试"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """创建 mock Redis 客户端"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.publish.return_value = 1
        return mock_client
    
    @pytest.fixture
    def publisher(self, mock_redis_client):
        """创建 RedisLogPublisher 实例"""
        with patch('redis.from_url', return_value=mock_redis_client):
            publisher = RedisLogPublisher(redis_url="redis://localhost:6379/0")
            return publisher
    
    def test_initialization_success(self, mock_redis_client):
        """测试成功初始化"""
        with patch('redis.from_url', return_value=mock_redis_client):
            publisher = RedisLogPublisher(redis_url="redis://localhost:6379/0")
            assert publisher._client is not None
            mock_redis_client.ping.assert_called_once()
    
    def test_initialization_failure(self):
        """测试初始化失败时的降级处理"""
        with patch('redis.from_url', side_effect=Exception("Connection failed")):
            publisher = RedisLogPublisher(redis_url="redis://localhost:6379/0")
            assert publisher._client is None
    
    def test_get_channel_name(self, publisher):
        """测试频道名称生成"""
        task_id = "test-task-123"
        channel = publisher._get_channel_name(task_id)
        assert channel == f"breakdown:logs:{task_id}"
    
    def test_build_message_basic(self, publisher):
        """测试基本消息构建"""
        message = publisher._build_message(
            message_type="step_start",
            task_id="task-123",
            step_name="提取冲突",
            content="开始执行"
        )
        
        assert message["type"] == "step_start"
        assert message["task_id"] == "task-123"
        assert message["step_name"] == "提取冲突"
        assert message["content"] == "开始执行"
        assert "timestamp" in message
        
        # 验证时间戳格式
        datetime.fromisoformat(message["timestamp"])
    
    def test_build_message_with_metadata(self, publisher):
        """测试带元数据的消息构建"""
        metadata = {"progress": 50, "total_steps": 5}
        message = publisher._build_message(
            message_type="progress",
            task_id="task-123",
            metadata=metadata
        )
        
        assert message["metadata"] == metadata
    
    def test_publish_step_start(self, publisher, mock_redis_client):
        """测试发布步骤开始消息"""
        task_id = "task-123"
        step_name = "提取冲突"
        metadata = {"progress": 20, "current_step": 1, "total_steps": 5}
        
        publisher.publish_step_start(task_id, step_name, metadata)
        
        # 验证 Redis publish 被调用
        mock_redis_client.publish.assert_called_once()
        
        # 验证频道名称
        call_args = mock_redis_client.publish.call_args
        channel = call_args[0][0]
        assert channel == f"breakdown:logs:{task_id}"
        
        # 验证消息内容
        message_json = call_args[0][1]
        message = json.loads(message_json)
        assert message["type"] == "step_start"
        assert message["task_id"] == task_id
        assert message["step_name"] == step_name
        assert message["metadata"] == metadata
    
    def test_publish_stream_chunk(self, publisher, mock_redis_client):
        """测试发布流式内容片段"""
        task_id = "task-123"
        step_name = "提取冲突"
        chunk = "[\n  {\n    \"type\": \"人物冲突\","
        
        publisher.publish_stream_chunk(task_id, step_name, chunk)
        
        # 验证消息格式
        call_args = mock_redis_client.publish.call_args
        message_json = call_args[0][1]
        message = json.loads(message_json)
        
        assert message["type"] == "stream_chunk"
        assert message["task_id"] == task_id
        assert message["step_name"] == step_name
        assert message["content"] == chunk
    
    def test_publish_step_end(self, publisher, mock_redis_client):
        """测试发布步骤结束消息"""
        task_id = "task-123"
        step_name = "提取冲突"
        result = {"count": 3, "duration_ms": 15000}
        
        publisher.publish_step_end(task_id, step_name, result)
        
        # 验证消息格式
        call_args = mock_redis_client.publish.call_args
        message_json = call_args[0][1]
        message = json.loads(message_json)
        
        assert message["type"] == "step_end"
        assert message["task_id"] == task_id
        assert message["step_name"] == step_name
        assert message["metadata"] == result
    
    def test_publish_error(self, publisher, mock_redis_client):
        """测试发布错误消息"""
        task_id = "task-123"
        error_message = "模型 API 调用失败"
        error_code = "MODEL_API_ERROR"
        step_name = "提取冲突"
        
        publisher.publish_error(task_id, error_message, error_code, step_name)
        
        # 验证消息格式
        call_args = mock_redis_client.publish.call_args
        message_json = call_args[0][1]
        message = json.loads(message_json)
        
        assert message["type"] == "error"
        assert message["task_id"] == task_id
        assert message["step_name"] == step_name
        assert message["content"] == error_message
        assert message["metadata"]["error_code"] == error_code
    
    def test_publish_progress(self, publisher, mock_redis_client):
        """测试发布进度更新消息"""
        task_id = "task-123"
        progress = 60
        current_step = 3
        total_steps = 5
        step_name = "分析角色"
        
        publisher.publish_progress(
            task_id, progress, current_step, total_steps, step_name
        )
        
        # 验证消息格式
        call_args = mock_redis_client.publish.call_args
        message_json = call_args[0][1]
        message = json.loads(message_json)
        
        assert message["type"] == "progress"
        assert message["task_id"] == task_id
        assert message["step_name"] == step_name
        assert message["metadata"]["progress"] == progress
        assert message["metadata"]["current_step"] == current_step
        assert message["metadata"]["total_steps"] == total_steps
    
    def test_publish_when_redis_unavailable(self):
        """测试 Redis 不可用时的降级处理"""
        with patch('redis.from_url', side_effect=Exception("Connection failed")):
            publisher = RedisLogPublisher(redis_url="redis://localhost:6379/0")
            
            # 应该不抛出异常
            publisher.publish_step_start("task-123", "提取冲突")
            publisher.publish_stream_chunk("task-123", "提取冲突", "chunk")
            publisher.publish_step_end("task-123", "提取冲突")
            publisher.publish_error("task-123", "error")
    
    def test_publish_failure_silent(self, publisher, mock_redis_client):
        """测试发布失败时静默处理"""
        mock_redis_client.publish.side_effect = Exception("Publish failed")
        
        # 应该不抛出异常
        publisher.publish_step_start("task-123", "提取冲突")
    
    def test_message_format_all_fields(self, publisher, mock_redis_client):
        """测试消息包含所有必需字段"""
        task_id = "task-123"
        step_name = "提取冲突"
        
        publisher.publish_step_start(task_id, step_name)
        
        call_args = mock_redis_client.publish.call_args
        message_json = call_args[0][1]
        message = json.loads(message_json)
        
        # 验证所有必需字段存在
        required_fields = ["type", "task_id", "timestamp", "step_name"]
        for field in required_fields:
            assert field in message, f"缺少必需字段: {field}"
    
    def test_message_json_serializable(self, publisher, mock_redis_client):
        """测试消息可以被 JSON 序列化和反序列化"""
        task_id = "task-123"
        step_name = "提取冲突"
        metadata = {"count": 3, "items": ["a", "b", "c"]}
        
        publisher.publish_step_end(task_id, step_name, metadata)
        
        call_args = mock_redis_client.publish.call_args
        message_json = call_args[0][1]
        
        # 验证可以反序列化
        message = json.loads(message_json)
        assert isinstance(message, dict)
        
        # 验证可以再次序列化
        re_serialized = json.dumps(message)
        assert isinstance(re_serialized, str)
    
    def test_close_connection(self, publisher, mock_redis_client):
        """测试关闭连接"""
        publisher.close()
        mock_redis_client.close.assert_called_once()
        assert publisher._client is None
    
    def test_close_connection_failure(self, publisher, mock_redis_client):
        """测试关闭连接失败时的处理"""
        mock_redis_client.close.side_effect = Exception("Close failed")
        
        # 应该不抛出异常
        publisher.close()
        assert publisher._client is None
    
    def test_chinese_content_encoding(self, publisher, mock_redis_client):
        """测试中文内容的编码"""
        task_id = "task-123"
        step_name = "提取冲突"
        chunk = "这是一段中文内容，包含特殊字符：《》、""''！？"
        
        publisher.publish_stream_chunk(task_id, step_name, chunk)
        
        # 验证中文内容正确编码
        call_args = mock_redis_client.publish.call_args
        message_json = call_args[0][1]
        message = json.loads(message_json)
        
        assert message["content"] == chunk


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

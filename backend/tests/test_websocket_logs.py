"""WebSocket 实时日志端点测试

测试 WebSocket 端点的功能：
- 连接建立
- Redis 消息订阅和转发
- 任务完成检测
- 错误处理
- 资源清理
"""
import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import WebSocket
from app.api.v1.websocket import websocket_breakdown_logs


@pytest.fixture
def mock_websocket():
    """创建 mock WebSocket"""
    websocket = AsyncMock(spec=WebSocket)
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def mock_redis_client():
    """创建 mock Redis 客户端"""
    redis_client = AsyncMock()
    
    # Mock pubsub
    pubsub = AsyncMock()
    pubsub.subscribe = AsyncMock()
    pubsub.unsubscribe = AsyncMock()
    pubsub.close = AsyncMock()
    pubsub.get_message = AsyncMock(return_value=None)
    
    redis_client.pubsub = Mock(return_value=pubsub)
    
    return redis_client, pubsub


@pytest.fixture
def mock_db_session():
    """创建 mock 数据库会话"""
    db = AsyncMock()
    
    # Mock execute 方法
    result = AsyncMock()
    result.scalar_one_or_none = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    
    return db, result


class TestWebSocketBreakdownLogs:
    """WebSocket 实时日志端点测试"""
    
    @pytest.mark.asyncio
    async def test_connection_success(self, mock_websocket, mock_redis_client):
        """测试成功建立连接"""
        redis_client, pubsub = mock_redis_client
        task_id = "test-task-123"
        
        # Mock get_redis 返回 Redis 客户端
        with patch('app.api.v1.websocket.get_redis', return_value=redis_client):
            # Mock AsyncSessionLocal
            with patch('app.api.v1.websocket.AsyncSessionLocal') as mock_session_class:
                # Mock 数据库查询返回已完成的任务（立即退出循环）
                mock_task = Mock()
                mock_task.status = "completed"
                
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none = AsyncMock(return_value=mock_task)
                
                mock_db = AsyncMock()
                mock_db.execute = AsyncMock(return_value=mock_result)
                
                # Properly mock async context manager
                async def mock_aenter():
                    return mock_db
                
                async def mock_aexit(*args):
                    return None
                
                mock_session = MagicMock()
                mock_session.__aenter__ = mock_aenter
                mock_session.__aexit__ = mock_aexit
                
                mock_session_class.return_value = mock_session
                
                # 执行测试
                await websocket_breakdown_logs(mock_websocket, task_id)
        
        # 验证连接被接受
        mock_websocket.accept.assert_called_once()
        
        # 验证订阅了正确的频道
        pubsub.subscribe.assert_called_once_with(f"breakdown:logs:{task_id}")
        
        # 验证发送了连接成功消息
        calls = mock_websocket.send_json.call_args_list
        assert len(calls) >= 1
        first_call = calls[0][0][0]
        assert first_call['type'] == 'connected'
        assert first_call['task_id'] == task_id
    
    @pytest.mark.asyncio
    async def test_redis_unavailable(self, mock_websocket):
        """测试 Redis 不可用时的处理"""
        task_id = "test-task-123"
        
        # Mock get_redis 返回 None
        with patch('app.api.v1.websocket.get_redis', return_value=None):
            await websocket_breakdown_logs(mock_websocket, task_id)
        
        # 验证发送了错误消息
        mock_websocket.send_json.assert_called_once()
        error_msg = mock_websocket.send_json.call_args[0][0]
        assert error_msg['type'] == 'error'
        assert error_msg['code'] == 'REDIS_UNAVAILABLE'
        
        # 验证连接被关闭（可能被调用多次，所以只检查是否被调用）
        assert mock_websocket.close.called
    
    @pytest.mark.asyncio
    async def test_message_forwarding(self, mock_websocket, mock_redis_client):
        """测试消息转发功能"""
        redis_client, pubsub = mock_redis_client
        task_id = "test-task-123"
        
        # 模拟 Redis 消息
        test_messages = [
            {
                'type': 'message',
                'data': json.dumps({
                    'type': 'step_start',
                    'task_id': task_id,
                    'step_name': '提取冲突',
                    'content': '开始执行: 提取冲突'
                })
            },
            {
                'type': 'message',
                'data': json.dumps({
                    'type': 'stream_chunk',
                    'task_id': task_id,
                    'step_name': '提取冲突',
                    'content': '正在分析...'
                })
            },
            {
                'type': 'message',
                'data': json.dumps({
                    'type': 'step_end',
                    'task_id': task_id,
                    'step_name': '提取冲突',
                    'content': '完成: 提取冲突',
                    'metadata': {'final': True}
                })
            }
        ]
        
        # 设置 get_message 返回测试消息
        message_iter = iter(test_messages)
        pubsub.get_message = AsyncMock(side_effect=lambda **kwargs: next(message_iter, None))
        
        with patch('app.api.v1.websocket.get_redis', return_value=redis_client):
            with patch('app.api.v1.websocket.AsyncSessionLocal') as mock_session_class:
                mock_task = Mock()
                mock_task.status = "running"
                
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none = AsyncMock(return_value=mock_task)
                
                mock_db = AsyncMock()
                mock_db.execute = AsyncMock(return_value=mock_result)
                
                # Properly mock async context manager
                async def mock_aenter():
                    return mock_db
                
                async def mock_aexit(*args):
                    return None
                
                mock_session = MagicMock()
                mock_session.__aenter__ = mock_aenter
                mock_session.__aexit__ = mock_aexit
                
                mock_session_class.return_value = mock_session
                
                await websocket_breakdown_logs(mock_websocket, task_id)
        
        # 验证消息被转发
        calls = mock_websocket.send_json.call_args_list
        
        # 应该至少有：连接消息 + 3条转发消息 + 完成消息
        assert len(calls) >= 4
        
        # 验证第一条是连接消息
        assert calls[0][0][0]['type'] == 'connected'
        
        # 验证转发的消息
        forwarded_messages = [call[0][0] for call in calls[1:-1]]
        assert any(msg['type'] == 'step_start' for msg in forwarded_messages)
        assert any(msg['type'] == 'stream_chunk' for msg in forwarded_messages)
        assert any(msg['type'] == 'step_end' for msg in forwarded_messages)
    
    @pytest.mark.asyncio
    async def test_task_completion_detection(self, mock_websocket, mock_redis_client):
        """测试任务完成检测"""
        redis_client, pubsub = mock_redis_client
        task_id = "test-task-123"
        
        # 模拟收到 final=True 的消息
        final_message = {
            'type': 'message',
            'data': json.dumps({
                'type': 'step_end',
                'task_id': task_id,
                'step_name': '最终步骤',
                'content': '任务完成',
                'metadata': {'final': True}
            })
        }
        
        pubsub.get_message = AsyncMock(return_value=final_message)
        
        with patch('app.api.v1.websocket.get_redis', return_value=redis_client):
            with patch('app.api.v1.websocket.AsyncSessionLocal') as mock_session_class:
                mock_task = Mock()
                mock_task.status = "running"
                
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none = AsyncMock(return_value=mock_task)
                
                mock_db = AsyncMock()
                mock_db.execute = AsyncMock(return_value=mock_result)
                
                # Properly mock async context manager
                async def mock_aenter():
                    return mock_db
                
                async def mock_aexit(*args):
                    return None
                
                mock_session = MagicMock()
                mock_session.__aenter__ = mock_aenter
                mock_session.__aexit__ = mock_aexit
                
                mock_session_class.return_value = mock_session
                
                await websocket_breakdown_logs(mock_websocket, task_id)
        
        # 验证发送了完成消息
        calls = mock_websocket.send_json.call_args_list
        completion_messages = [call[0][0] for call in calls if call[0][0].get('type') == 'task_complete']
        assert len(completion_messages) >= 1
    
    @pytest.mark.asyncio
    async def test_error_message_handling(self, mock_websocket, mock_redis_client):
        """测试错误消息处理"""
        redis_client, pubsub = mock_redis_client
        task_id = "test-task-123"
        
        # 模拟收到不可重试的错误消息
        error_message = {
            'type': 'message',
            'data': json.dumps({
                'type': 'error',
                'task_id': task_id,
                'content': '模型调用失败',
                'metadata': {'retryable': False}
            })
        }
        
        pubsub.get_message = AsyncMock(return_value=error_message)
        
        with patch('app.api.v1.websocket.get_redis', return_value=redis_client):
            with patch('app.api.v1.websocket.AsyncSessionLocal') as mock_session_class:
                mock_task = Mock()
                mock_task.status = "running"
                
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none = AsyncMock(return_value=mock_task)
                
                mock_db = AsyncMock()
                mock_db.execute = AsyncMock(return_value=mock_result)
                
                # Properly mock async context manager
                async def mock_aenter():
                    return mock_db
                
                async def mock_aexit(*args):
                    return None
                
                mock_session = MagicMock()
                mock_session.__aenter__ = mock_aenter
                mock_session.__aexit__ = mock_aexit
                
                mock_session_class.return_value = mock_session
                
                await websocket_breakdown_logs(mock_websocket, task_id)
        
        # 验证发送了失败消息
        calls = mock_websocket.send_json.call_args_list
        failure_messages = [call[0][0] for call in calls if call[0][0].get('type') == 'task_failed']
        assert len(failure_messages) >= 1
    
    @pytest.mark.asyncio
    async def test_json_parse_error_handling(self, mock_websocket, mock_redis_client):
        """测试 JSON 解析错误处理"""
        redis_client, pubsub = mock_redis_client
        task_id = "test-task-123"
        
        # 模拟收到无效的 JSON 消息
        invalid_messages = [
            {'type': 'message', 'data': 'invalid json'},
            {'type': 'message', 'data': json.dumps({'type': 'step_end', 'metadata': {'final': True}})}
        ]
        
        message_iter = iter(invalid_messages)
        pubsub.get_message = AsyncMock(side_effect=lambda **kwargs: next(message_iter, None))
        
        with patch('app.api.v1.websocket.get_redis', return_value=redis_client):
            with patch('app.api.v1.websocket.AsyncSessionLocal') as mock_session_class:
                mock_task = Mock()
                mock_task.status = "running"
                
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none = AsyncMock(return_value=mock_task)
                
                mock_db = AsyncMock()
                mock_db.execute = AsyncMock(return_value=mock_result)
                
                # Properly mock async context manager
                async def mock_aenter():
                    return mock_db
                
                async def mock_aexit(*args):
                    return None
                
                mock_session = MagicMock()
                mock_session.__aenter__ = mock_aenter
                mock_session.__aexit__ = mock_aexit
                
                mock_session_class.return_value = mock_session
                
                # 不应该抛出异常
                await websocket_breakdown_logs(mock_websocket, task_id)
        
        # 验证连接正常建立
        mock_websocket.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resource_cleanup(self, mock_websocket, mock_redis_client):
        """测试资源清理"""
        redis_client, pubsub = mock_redis_client
        task_id = "test-task-123"
        
        # 模拟任务完成
        with patch('app.api.v1.websocket.get_redis', return_value=redis_client):
            with patch('app.api.v1.websocket.AsyncSessionLocal') as mock_session_class:
                mock_task = Mock()
                mock_task.status = "completed"
                
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none = AsyncMock(return_value=mock_task)
                
                mock_db = AsyncMock()
                mock_db.execute = AsyncMock(return_value=mock_result)
                
                # Properly mock async context manager
                async def mock_aenter():
                    return mock_db
                
                async def mock_aexit(*args):
                    return None
                
                mock_session = MagicMock()
                mock_session.__aenter__ = mock_aenter
                mock_session.__aexit__ = mock_aexit
                
                mock_session_class.return_value = mock_session
                
                await websocket_breakdown_logs(mock_websocket, task_id)
        
        # 验证取消订阅
        pubsub.unsubscribe.assert_called_once()
        
        # 验证关闭 pubsub
        pubsub.close.assert_called_once()
        
        # 验证关闭 WebSocket
        assert mock_websocket.close.called
    
    @pytest.mark.asyncio
    async def test_database_status_check(self, mock_websocket, mock_redis_client):
        """测试数据库状态检查"""
        redis_client, pubsub = mock_redis_client
        task_id = "test-task-123"
        
        # 模拟没有 Redis 消息，但数据库显示任务已完成
        pubsub.get_message = AsyncMock(return_value=None)
        
        with patch('app.api.v1.websocket.get_redis', return_value=redis_client):
            with patch('app.api.v1.websocket.AsyncSessionLocal') as mock_session_class:
                # 第一次查询返回 running，第二次返回 completed
                mock_task_running = Mock()
                mock_task_running.status = "running"
                
                mock_task_completed = Mock()
                mock_task_completed.status = "completed"
                
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none = AsyncMock(side_effect=[mock_task_running, mock_task_completed])
                
                mock_db = AsyncMock()
                mock_db.execute = AsyncMock(return_value=mock_result)
                
                # Properly mock async context manager
                async def mock_aenter():
                    return mock_db
                
                async def mock_aexit(*args):
                    return None
                
                mock_session = MagicMock()
                mock_session.__aenter__ = mock_aenter
                mock_session.__aexit__ = mock_aexit
                
                mock_session_class.return_value = mock_session
                
                await websocket_breakdown_logs(mock_websocket, task_id)
        
        # 验证发送了完成消息
        calls = mock_websocket.send_json.call_args_list
        completion_messages = [call[0][0] for call in calls if call[0][0].get('type') == 'task_complete']
        assert len(completion_messages) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

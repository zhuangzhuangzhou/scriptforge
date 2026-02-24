# WebSocket 批次切换推送 - 验证报告

## ✅ 验证通过的部分

### 1. RedisLogPublisher.publish_batch_switch 方法
**位置**: `app/core/redis_log_publisher.py:426-455`

```python
def publish_batch_switch(
    self,
    old_task_id: str,
    new_task_id: str,
    new_batch_id: str,
    new_batch_number: int
) -> None:
    msg = self._build_message(
        message_type="batch_switch",
        task_id=old_task_id,
        content=f"批次 {new_batch_number} 已开始拆解",
        metadata={
            "new_task_id": new_task_id,
            "new_batch_id": new_batch_id,
            "new_batch_number": new_batch_number,
            "auto_switch": True
        }
    )
    self.publish_log(old_task_id, msg)
```

✅ **验证结果**:
- 方法签名正确
- 使用 `_build_message` 构建消息 (统一格式)
- 消息类型: `batch_switch`
- 发送到旧任务的频道: `breakdown:logs:{old_task_id}`
- metadata 包含所有必要信息

### 2. _trigger_next_task_sync 调用推送
**位置**: `app/tasks/breakdown_tasks.py:138-156`

```python
# 推送批次切换消息
try:
    from app.core.redis_log_publisher import RedisLogPublisher
    log_publisher = RedisLogPublisher()
    
    log_publisher.publish_batch_switch(
        old_task_id=completed_task_id,
        new_task_id=str(new_task.id),
        new_batch_id=str(next_batch.id),
        new_batch_number=next_batch.batch_number
    )
    
    logger.info(f"已推送批次切换消息: {current_batch_number} -> {next_batch.batch_number}")
except Exception as ws_error:
    logger.warning(f"推送批次切换消息失败: {ws_error}")
```

✅ **验证结果**:
- 在创建新任务后立即推送
- 使用 try-except 包裹,推送失败不影响主流程
- 记录日志便于调试
- 参数传递正确

## ⚠️ 发现的问题

### 问题 1: WebSocket 频道订阅逻辑
**位置**: `app/api/v1/websocket.py:64-225`

**问题**: WebSocket 端点订阅的是 `breakdown:logs:{task_id}`,这是正确的。
但需要确认前端连接的是**旧任务的 WebSocket**,才能收到 `batch_switch` 消息。

**验证**:
```python
# WebSocket 订阅频道
channel_name = f"breakdown:logs:{task_id}"  # ✅ 正确

# 推送消息到旧任务频道
self.publish_log(old_task_id, msg)  # ✅ 正确
```

**结论**: ✅ 频道命名一致,逻辑正确

### 问题 2: 消息转发逻辑
**位置**: `app/api/v1/websocket.py:407-598`

**检查点**: `/ws/breakdown-logs/{task_id}` 端点是否会转发 `batch_switch` 消息?

```python
# 主循环：接收 Redis 消息并转发
while True:
    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
    
    if message and message['type'] == 'message':
        data = json.loads(message['data'])
        
        # 转发到前端
        await websocket.send_json(data)  # ✅ 会转发所有消息类型
        
        # 检测任务完成状态
        if data.get('type') == 'task_complete':
            break
```

**结论**: ✅ WebSocket 会转发所有消息,包括 `batch_switch`

### 问题 3: 前端 WebSocket 连接
**位置**: `frontend/src/hooks/useConsoleLogger.ts:178-239`

**问题**: 前端连接的是哪个 WebSocket 端点?

需要检查:
1. 前端连接的是 `/ws/breakdown/{task_id}` 还是 `/ws/breakdown-logs/{task_id}`?
2. 前端是否处理 `batch_switch` 消息?

**待验证**: ⏳ 需要检查前端代码

## ❌ 发现的严重问题

### 严重问题: WebSocket 连接时机
**场景分析**:
```
批次 7 任务完成
    ↓
前端 WebSocket 收到 task_complete 消息
    ↓
前端关闭 WebSocket 连接 (ws.close())
    ↓
后端推送 batch_switch 消息
    ↓
❌ 前端已断开,收不到消息!
```

**代码证据**:
```typescript
// frontend/src/hooks/useConsoleLogger.ts:216-218
if (data.final_status) {
    ws.close();  // ❌ 问题: 立即关闭连接
}
```

**根本原因**: 
- `task_complete` 消息包含 `final: true`
- 前端收到后立即关闭 WebSocket
- `batch_switch` 消息在 `task_complete` 之后发送
- 前端已断开,收不到 `batch_switch` 消息

## 🔧 修复方案

### 方案 1: 调整消息发送顺序 (推荐)
在 `_trigger_next_task_sync` 中,**先推送 batch_switch,再推送 task_complete**

```python
# ✅ 正确顺序
# 1. 先推送批次切换消息
log_publisher.publish_batch_switch(...)

# 2. 再推送任务完成消息
log_publisher.publish_task_complete(completed_task_id, TaskStatus.COMPLETED)
```

### 方案 2: 延迟关闭 WebSocket
前端收到 `task_complete` 后,延迟 2 秒再关闭连接

```typescript
if (data.final_status) {
    // 延迟关闭,等待可能的 batch_switch 消息
    setTimeout(() => {
        ws.close();
    }, 2000);
}
```

### 方案 3: batch_switch 消息不关闭连接
前端收到 `batch_switch` 消息后,不关闭当前连接,而是:
1. 保存新任务信息
2. 通知父组件切换批次
3. 父组件创建新的 WebSocket 连接
4. 旧连接自然超时关闭

## 📊 验证结论

### ✅ 已验证通过
1. ✅ RedisLogPublisher.publish_batch_switch 方法实现正确
2. ✅ _trigger_next_task_sync 调用推送方法
3. ✅ 消息格式正确
4. ✅ Redis 频道命名一致
5. ✅ WebSocket 端点会转发消息

### ❌ 发现的问题
1. ❌ **严重**: WebSocket 连接时机问题 - 前端可能在收到 batch_switch 前就关闭连接
2. ⏳ **待验证**: 前端是否处理 batch_switch 消息
3. ⏳ **待验证**: 前端连接的是哪个 WebSocket 端点

### 🔧 必须修复
**优先级 P0**: 修复 WebSocket 连接时机问题
- 方案 1: 调整消息发送顺序 (最简单)
- 方案 2: 延迟关闭连接 (兼容性好)
- 方案 3: 修改前端逻辑 (最彻底)

## 建议
**立即修复**: 采用方案 1 + 方案 2 组合
1. 后端: 先发送 batch_switch,再发送 task_complete
2. 前端: 延迟 2 秒关闭连接,确保收到所有消息


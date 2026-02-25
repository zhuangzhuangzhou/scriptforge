# WebSocket 消息推送模式

## 概述

本文档记录 WebSocket 实时消息推送的最佳实践和常见陷阱。

---

## 架构设计

### 双频道模式

项目使用两个独立的 WebSocket 频道:

| 频道 | 用途 | 消息类型 |
|------|------|----------|
| `breakdown:{task_id}` | 任务进度更新 | `progress`, `status_change` |
| `breakdown:logs:{task_id}` | 流式日志和事件 | `step_start`, `stream_chunk`, `batch_switch` |

**为什么分离?**
- 不同的消息类型有不同的处理逻辑
- 前端可以选择性订阅
- 降低单个频道的消息量

---

## Pattern: 添加新的消息类型

### 问题
需要在现有 WebSocket 基础上添加新的实时通知功能。

### 解决方案

**步骤 1: 选择正确的频道**

```python
# ❌ 错误: 随意选择频道
redis_client.publish(f"breakdown:{task_id}", message)

# ✅ 正确: 根据消息性质选择频道
# 进度类消息 → breakdown:{task_id}
# 日志类消息 → breakdown:logs:{task_id}
redis_client.publish(f"breakdown:logs:{task_id}", message)
```

**步骤 2: 使用统一的消息构建方法**

```python
# ✅ 使用 RedisLogPublisher._build_message
def publish_batch_switch(
    self,
    old_task_id: str,
    new_task_id: str,
    new_batch_id: str,
    new_batch_number: int
) -> None:
    """发布批次切换消息"""
    msg = self._build_message(
        message_type="batch_switch",  # 新的消息类型
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

**步骤 3: 在正确的时机推送**

```python
# ❌ 错误: 在事务提交前推送
log_publisher.publish_batch_switch(...)
db.commit()  # 如果失败,前端已收到消息但数据未保存

# ✅ 正确: 在事务提交后推送
db.commit()  # 先确保数据已保存
log_publisher.publish_batch_switch(...)  # 再推送消息
```

**步骤 4: 添加错误处理**

```python
# ✅ 推送失败不应影响主流程
try:
    log_publisher.publish_batch_switch(...)
    logger.info(f"已推送批次切换消息: {old_batch} -> {new_batch}")
except Exception as ws_error:
    logger.warning(f"推送批次切换消息失败: {ws_error}")
    # 不抛出异常,让降级机制接管
```

### 为什么这样做?

1. **数据一致性**: 事务提交后推送,确保前端收到消息时数据已准备好
2. **可靠性**: 推送失败不影响主流程,降级机制(轮询)仍能工作
3. **可维护性**: 使用统一的消息格式,便于前端处理

---

## Pattern: 降级设计

### 问题
WebSocket 推送可能失败(Redis 不可用、网络问题等),如何保证功能可用?

### 解决方案: 双保险机制

```python
# 主要机制: WebSocket 实时推送
try:
    log_publisher.publish_batch_switch(...)
except Exception:
    logger.warning("WebSocket 推送失败")
    # 不抛出异常,让降级机制接管

# 降级机制: 定时轮询 (前端)
# 每 30 秒轮询一次批次状态
setInterval(() => {
    fetchBatchProgress();
}, 30000);
```

### 为什么这样做?

- **99% 情况**: WebSocket 推送成功,延迟 < 0.5 秒
- **1% 情况**: WebSocket 失败,降级到轮询,延迟 < 30 秒
- **用户体验**: 大部分时间享受实时更新,偶尔降级也可接受

---

## Common Mistake: 消息发送顺序错误

### 症状
前端收到 `task_complete` 消息后立即关闭 WebSocket,错过了后续的 `batch_switch` 消息。

### 原因
消息发送顺序不当:

```python
# ❌ 错误顺序
log_publisher.publish_task_complete(task_id)  # 前端收到后关闭连接
_trigger_next_task_sync(...)  # 触发下一批次
    └─> publish_batch_switch(...)  # 消息发送时连接已关闭
```

### 修复方案 1: 延迟关闭 (当前实现)

```typescript
// 前端: 延迟 2 秒关闭 WebSocket
if (data.final_status) {
    setTimeout(() => {
        ws.close();
    }, 2000);  // 给 batch_switch 消息留出时间
}
```

### 修复方案 2: 调整发送顺序 (更优)

```python
# ✅ 更好的顺序
_trigger_next_task_sync(...)  # 先触发下一批次
    └─> publish_batch_switch(...)  # 先发送 batch_switch
log_publisher.publish_task_complete(task_id)  # 最后发送 task_complete
```

### 预防
- 设计消息流时,考虑消息的依赖关系
- 关键消息应该先发送,状态消息后发送
- 或者使用延迟关闭作为兜底

---

## Gotcha: 频道命名一致性

> **Warning**: WebSocket 频道命名必须在后端推送和前端订阅时完全一致。
>
> 常见错误:
> - 后端: `breakdown:logs:{task_id}`
> - 前端: `breakdown-logs:{task_id}` (使用了 `-` 而不是 `:`)
>
> 结果: 前端收不到任何消息,且没有明显的错误提示。

**预防**:
- 使用常量定义频道名称
- 添加集成测试验证消息能正常接收

---

## 性能考虑

### 消息大小优化

```python
# ❌ 不好: 发送大量不必要的数据
msg = {
    "type": "batch_switch",
    "full_batch_data": batch.to_dict(),  # 包含所有字段
    "full_task_data": task.to_dict(),
    # ...
}

# ✅ 好: 只发送必要的字段
msg = {
    "type": "batch_switch",
    "metadata": {
        "new_task_id": str(task.id),
        "new_batch_id": str(batch.id),
        "new_batch_number": batch.batch_number
    }
}
```

### 推送频率控制

```python
# ❌ 不好: 高频推送进度更新
for i in range(100):
    publish_progress(i)  # 100 次推送

# ✅ 好: 限制推送频率
last_publish = 0
for i in range(100):
    if time.time() - last_publish > 0.5:  # 最多 2 次/秒
        publish_progress(i)
        last_publish = time.time()
```

---

## 测试建议

### 单元测试

```python
def test_publish_batch_switch():
    """测试批次切换消息推送"""
    publisher = RedisLogPublisher()

    # 推送消息
    publisher.publish_batch_switch(
        old_task_id="task-1",
        new_task_id="task-2",
        new_batch_id="batch-2",
        new_batch_number=2
    )

    # 验证消息格式
    msg = redis_client.get_last_message("breakdown:logs:task-1")
    assert msg["type"] == "batch_switch"
    assert msg["metadata"]["new_batch_number"] == 2
```

### 集成测试

```python
def test_batch_switch_end_to_end():
    """测试批次切换的完整流程"""
    # 1. 启动批次 1
    task_1 = start_breakdown(batch_1)

    # 2. 等待批次 1 完成
    wait_for_completion(task_1)

    # 3. 验证批次 2 自动启动
    task_2 = get_current_task(batch_2)
    assert task_2 is not None

    # 4. 验证 WebSocket 消息
    messages = get_websocket_messages("breakdown:logs:" + task_1.id)
    batch_switch_msg = [m for m in messages if m["type"] == "batch_switch"]
    assert len(batch_switch_msg) == 1
```

---

## 相关文档

- [数据库事务管理](./database-transactions.md)
- [前端 WebSocket 处理](../frontend/websocket-handling.md)
- [跨层数据流指南](../guides/cross-layer-thinking-guide.md)

---

## 更新日志

| 日期 | 更新内容 | 作者 |
|------|----------|------|
| 2026-02-23 | 初始版本: WebSocket 消息推送模式 | Claude Opus 4.6 |

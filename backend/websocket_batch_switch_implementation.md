# WebSocket 批次切换推送 - 完整实现方案

## 方案概述

利用现有的 WebSocket 基础设施,在批次完成时实时推送下一批次信息,实现 0 延迟的批次切换。

## 架构设计

```
批次 7 完成
    ↓
后端 _trigger_next_task_sync()
    ↓
创建批次 8 任务
    ↓
通过 Redis Pub/Sub 推送 batch_switch 消息
    ↓
WebSocket 转发到前端
    ↓
前端立即切换到批次 8 (0 延迟)
```

## 后端实现

### 1. RedisLogPublisher 新增方法 ✅

```python
def publish_batch_switch(
    self,
    old_task_id: str,
    new_task_id: str,
    new_batch_id: str,
    new_batch_number: int
) -> None:
    """发布批次切换消息"""
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

### 2. breakdown_tasks.py 调用推送 ✅

```python
def _trigger_next_task_sync(...):
    # ... 创建新任务 ...
    
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
    except Exception as ws_error:
        logger.warning(f"推送批次切换消息失败: {ws_error}")
```

## 前端实现

### 方案 A: 在 useConsoleLogger 中处理 (推荐)

**优点**: 
- 利用现有 WebSocket 连接
- 无需额外连接
- 实时性最好

**实现位置**: `frontend/src/hooks/useConsoleLogger.ts`

```typescript
// 在 ws.onmessage 中添加
ws.onmessage = (event) => {
  try {
    const data = JSON.parse(event.data);
    
    // 🔧 新增：处理批次切换消息
    if (data.type === 'batch_switch') {
      const { new_task_id, new_batch_id, new_batch_number } = data.metadata;
      
      addLog('info', `批次 ${new_batch_number} 已开始拆解，正在切换...`);
      
      // 触发回调，通知父组件切换批次
      if (options.onBatchSwitch) {
        options.onBatchSwitch({
          newTaskId: new_task_id,
          newBatchId: new_batch_id,
          newBatchNumber: new_batch_number
            }
      
      return; // 不关闭当前连接，让父组件处理
    }
    
    // ... 其他消息处理 ...
  } catch (error) {
    console.error('解析 WebSocket 消息失败:', error);
  }
};
```

### 方案 B: 在 Workspace 组件中处理

**实现位置**: `frontend/src/pages/user/Workspace/index.tsx`

```typescript
// 1. 修改 useConsoleLogger 调用，添加回调
const { logs, addLog, clearLogs } = useConsoleLogger(breakdownTaskId, {
  enableWebSocket: true,
  onBatchSwitch: async (switchInfo) => {
    console.log('[Workspace] 收到批次切换消息:', switchInfo);
    
    // 立即刷新批次列表
    await fetchBatches();
    
    // 查找新批次
    const newBatch = batches.find === switchInfo.newBatchId);
    if (newBatch) {
      setSelectedBatch(newBatch);
      setBreakdownTaskId(switchInfo.newTaskId);
      message.info(`已自动切换到批次 ${switchInfo.newBatchNumber}`);
    }
  }
});
```

## 消息格式

### batch_switch 消息

```json
{
  "type": "batch_switch",
  "task_id": "old-task-id",
  "content": "批次 9 已开始拆解",
  "timestamp": "2026-02-23T10:30:00Z",
  "metadata": {
    "new_task_id": "new-task-id",
    "new_batch_id": "new-batch-id",
    "new_batch_number": 9,
    "auto_switch": true
  }
}
```

## 优势对比

### 当前方案 (30秒轮询)
- 批次切换延迟: 0-30秒
- API 调用: 每30秒一次
- 用户体验: 有延迟感

### WebSocket 推送方案
- 批次切换延迟: 0秒 (实时)
- API 调用: 按需刷新
- 用户体验: 无缝切换

## 实现步骤

### 后端 ✅
1. ✅ 在 `RedisLogPublisher` 中添加 `publish_batch_switch` 方法
2. ✅ 在 `_trigger_next_task_sync` 中调用推送方法

### 前端 (待实现)
1. ⏳ 修改 `useConsoleLogger` 的 TypeScript 接口,添加 `onBatchSwitch` 回调
2. ⏳ 在 `ws.onmessage` 中添加 `batch_switch` 消息处理
3. ⏳ 在 `Workspace` 组件中实现批次切换逻辑

## 测试验证

### 测试场景
1. 批次 7 完成 → 立即显示批次 8 开始
2. WebSocket 断开 → 降级到轮询模式
3. 快速批次切换 → 不跳过中间批次

### 预期结果
- 批次切换延迟 < 1 秒
- 控制台显示切换消息
- 前端自动连接新任务 WebSocket

## 兼容性

### 降级策略
如果 WebSocket 不可用或推送失败:
1. 前端仍然保持 30 秒轮询
2. 通过 `pollBatchProgress` 检测批次变化
3. 用户体验略有延迟,但功能正常

### 向后兼容
- 不影响现有的单批次拆解
- 不影响手动批次切换
- 只在"全部拆解"模式下生效


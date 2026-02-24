# Cross-Layer 检查报告

## 📊 变更范围

### 涉及的层次 (5 层)
1. **后端任务层**: `backend/app/tasks/breakdown_tasks.py`
2. **后端基础设施层**: `backend/app/core/redis_log_publisher.py`
3. **后端 API 层**: `backend/app/api/v1/breakdown.py`
4. **前端 Hooks 层**: `frontend/src/hooks/useConsoleLogger.ts`
5. **前端 UI 层**: `frontend/src/pages/user/Workspace/index.tsx`

### 变更类型
- WebSocket 实时推送批次切换消息
- 批次状态同步优化
- 轮询逻辑优化

---

## ✅ Dimension A: Cross-Layer Data Flow

### 数据流路径

#### 批次切换推送流 (新增):
```
批次 7 完成 (breakdown_tasks.py)
    ↓
_trigger_next_task_sync() 创建批次 8
    ↓
RedisLogPublisher.publish_batch_switch()
    ↓
Redis Pub/Sub (breakdown:logs:{task_7_id})
    ↓
WebSocket 端点转发 (websocket.py)
    ↓
useConsoleLogger 接收 (useConsoleLogger.ts)
    ↓
触发 onBatchSwitch 回调
    ↓
Workspace 组件切换批次 (index.tsx)
```

#### 批次进度轮询流 (优化):
```
Workspace 组件 (index.tsx)
    ↓
pollBatchProgress() 每 30 秒
    ↓
GET /api/v1/breakdown/batch-progress/{project_id}
    ↓
检测 current_task.batch_number 变化
    ↓
立即刷新 batches 列表
    ↓
切换 selectedBatch
```

### ❌ 发现的问题

#### 问题 1: WebSocket 连接时机冲突 (P0 严重)

**问题描述**:
- 前端收到 `task_complete` 消息后立即关闭 WebSocket
- `batch_switch` 消息在 `task_complete` 之后发送
- 前端已断开,收不到 `batch_switch` 消息

**代码位置**:
```typescript
// frontend/src/hooks/useConsoleLogger.ts:216-218 (修复前)
if (data.final_status) {
    ws.close();  // ❌ 立即关闭
}
```

**修复方案**: ✅ 已修复
1. 添加 `batch_switch` 消息处理
2. 延迟 2 秒关闭 WebSocket,等待可能的批次切换消息
3. 添加 `onBatchSwitch` 回调接口

**修复后代码**:
```typescript
// 处理批次切换消息
if (data.type === 'batch_switch') {
    const { new_task_id, new_batch_id, new_batch_number } = data.metadata || {};
    addLog('info', `批次 ${new_batch_number} 已开始拆解，正在切换...`);
    
    if (options.onBatchSwitch) {
        options.onBatchSwitch({
            newTaskId: new_task_id,
            newBatchId: new_batch_id,
            newBatchNumber: new_batch_number
        });
    }
    return;
}

// 延迟关闭 WebSocket
if (data.final_status) {
    setTimeout(() => {
        ws.close();
    }, 2000);
}
```

#### 问题 2: 前端 Workspace 组件缺少 onBatchSwitch 实现 (P1 重要)

**问题描述**:
- `useConsoleLogger` 已支持 `onBatchSwitch` 回调
- 但 `Workspace` 组件没有传入该回调
- 批次切换消息无法触发 UI 更新

**待修复**: ⏳ 需要在 `Workspace/index.tsx` 中实现

---

## ✅ Dimension B: Code Reuse

### 检查点 1: 批次状态常量

<function_calls>
<invoke name="Bash">
<parameter name="command">grep -r "BATCH_STATUS\|BatchStatus" frontend/src/ --include="*.tsx" --include="*.ts" | head -20
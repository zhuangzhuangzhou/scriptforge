# 全部拆解功能问题修复方案

## 问题清单

1. ✅ Console 显示批次号不对 (仍显示批次1)
2. ⏳ 左侧列表拆解状态不显示动画
3. ⏳ 左侧列表无法向下滑动
4. ⏳ 退出重进 Console 无法正确呼出
5. ⏳ 其它已修复的问题仍不正常
6. ✅ Token 过期时间调整为 120 分钟
7. ⏳ 系统检查全部拆解逻辑

---

## 已完成的修复

### 1. Console 显示批次号修复 ✅

**问题**: Console 显示的批次号通过查找 `batches` 数组获取,但数组可能未及时更新

**修复**: 直接使用 `selectedBatch.batch_number`

```typescript
// 修复前
batchNumber={(() => {
    const activeBatchId = executingBatchId || selectedBatch?.id;
    const activeBatch = batches.find(b => b.id === activeBatchId);
    return activeBatch?.batch_number || 0;
})()}

// 修复后
batchNumber={selectedBatch?.batch_number || 0}
```

**文件**: `frontend/src/pages/user/Workspace/index.tsx:1809`

### 2. Token 过期时间调整 ✅

**修改**: 从 30 分钟调整为 120 分钟

**文件**: `backend/app/core/config.py:36`

```python
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 修改为 120 分钟
```

---

## 待修复的问题

### 3. 左侧列表拆解状态不显示动画

**分析**: BatchCard 组件的动画逻辑已存在,需要检查:
1. 批次状态是否正确更新
2. 动画 CSS 类是否正确应用

**检查点**:
- `BatchCard.tsx:47` - `animate-pulse` 类
- `BatchCard.tsx:53` - `animate-spin` 类
- 批次状态更新逻辑

### 4. 左侧列表无法向下滑动

**分析**: BatchList 使用了 `no-scrollbar` 类,可能导致滚动不可见

**检查点**:
- `BatchList.tsx:43` - 滚动容器样式
- `handleBatchScroll` 函数是否正确触发
- CSS 中 `no-scrollbar` 类的定义

**可能的修复**:
```tsx
// 移除 no-scrollbar 或添加自定义滚动条样式
<div className="flex-1 overflow-y-auto divide-y divide-slate-800/30" onScroll={onScroll}>
```

### 5. 退出重进 Console 无法正确呼出

**分析**: 需要检查页面加载时的状态恢复逻辑

**检查点**:
1. 页面加载时是否检测正在进行的任务
2. `fetchBatches` 中的自动检测逻辑 (line 627-653)
3. `showConsole` 状态是否正确设置

**关键代码**:
```typescript
// Workspace/index.tsx:627-653
if (pageNum === 1 && !breakdownTaskId) {
    const processingBatch = newItems.find(
        (b: Batch) => b.breakdown_status === BATCH_STATUS.IN_PROGRESS ||
                      b.breakdown_status === BATCH_STATUS.QUEUED
    );
    if (processingBatch) {
        // 获取任务 ID 并连接 WebSocket
        const taskRes = await breakdownApi.getBatchCurrentTask(processingBatch.id);
        const taskId = taskRes.data?.task_id;
        if (taskId) {
            setBreakdownTaskId(taskId);
            setShowConsole(true);  // 自动打开控制台
        }
    }
}
```

### 6. 系统检查全部拆解逻辑

**需要检查的完整流程**:

#### 6.1 启动全部拆解
```
用户点击"全部拆解"
  → handleAllBreakdown()
  → breakdownApi.startBatchBreakdown()
  → 后端创建任务链
  → 返回启动的任务数量
```

#### 6.2 批次状态更新
```
后端任务执行
  → 更新批次状态为 in_progress
  → 推送 WebSocket 消息
  → 前端接收并更新 UI
```

#### 6.3 批次自动切换
```
批次 N 完成
  → _trigger_next_task_sync()
  → 创建批次 N+1 任务
  → publish_batch_switch()
  → 前端 onBatchSwitch 回调
  → 刷新批次列表
  → 切换到新批次
```

#### 6.4 进度轮询
```
pollBatchProgress() 每 30 秒执行
  → getBatchProgress()
  → 检测 current_task
  → 如果批次号变化,刷新列表并切换
  → 更新进度显示
```

---

## 关键问题分析

### 问题 1: 批次切换时显示消失

**可能原因**:
1. `selectedBatch` 在切换时被设置为 null
2. 批次列表刷新时有延迟
3. Console 的 `batchNumber` 计算逻辑有问题 (已修复)

**需要检查**:
- `onBatchSwitch` 回调中的状态更新顺序
- 是否有地方错误地清空了 `selectedBatch`

### 问题 2: 状态不显示

**可能原因**:
1. 批次状态未正确更新
2. 批次列表未及时刷新
3. WebSocket 消息未正确接收

**需要检查**:
- `pollBatchProgress` 是否正确执行
- 批次列表刷新逻辑
- WebSocket 连接状态

---

## 下一步行动

### 优先级 P0 (立即修复)
1. ✅ 修复 Console 批次号显示
2. ✅ 调整 Token 过期时间
3. ⏳ 修复左侧列表滚动问题
4. ⏳ 修复退出重进 Console 呼出问题

### 优先级 P1 (重要)
5. ⏳ 检查批次状态动画显示
6. ⏳ 系统测试全部拆解流程

### 优先级 P2 (可选)
7. ⏳ 优化批次切换的用户体验
8. ⏳ 添加更多错误处理和提示

---

## 测试计划

### 测试场景 1: 全部拆解基本流程
1. 启动全部拆解
2. 观察批次状态变化
3. 观察 Console 批次号显示
4. 观察批次自动切换

### 测试场景 2: 页面刷新
1. 全部拆解进行中
2. 刷新页面
3. 检查 Console 是否自动打开
4. 检查是否连接到正确的批次

### 测试场景 3: 批次列表滚动
1. 创建多个批次 (>10 个)
2. 尝试向下滚动
3. 检查是否能看到所有批次
4. 检查滚动加载是否正常

---

## 更新日期
2026-02-23

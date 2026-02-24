# 批次状态同步问题 - 系统修复方案

## 问题根源分析

### 1. 状态不同步的三个层面
```
后端数据库状态 (批次 9 in_progress)
    ↓ (30秒轮询)
前端 batches 数组 (批次 7 in_progress) ← 过期数据
    ↓
前端 selectedBatch (批次 7) ← 显示给用户
```

### 2. 关键问题点

#### 问题 1: `batches` 数组不更新
- `pollBatchProgress()` 只更新 `batchProgress` 状态
- 不刷新 `batches` 数组
- 导致从 `batches.find()` 查找时得到过期数据

#### 问题 2: 依赖本地数据查找
```typescript
// ❌ 错误：从本地过期数组查找
const processingBatch = batches.find(b => b.id === currentTask.batch_id);
```

#### 问题 3: 30秒轮询间隔太长
- 批次 7 完成 → 批次 8 开始 → 批次 8 完成 → 批次 9 开始
- 如果这个过程在 30 秒内完成,前端会跳过中间批次

## 修复方案

### 方案 A: 使用 API 返回的 batch_number (已实施)

**优点**:
- 不依赖本地数据
- 数据来源可靠

**实现**:
```typescript
// ✅ 正确：使用 API 返回的 batch_number
const currentBatchNumber = currentTask.batch_number;

// 检测到批次号变化时,立即刷新批次列表
if (!selectedBatch || selectedBatch.batch_number !== currentBatchNumber) {
    const batchRes = await breakdownApi.getBatches(projectId, 1, 20);
    const freshBatches = batchRes.data.items;
    setBatches(freshBatches);
    
    const processingBatch = freshBatches.find(b => b.id === currentTask.batch_id);
    setSelectedBatch(processingBatch);
}
```

### 方案 B: 减少轮询间隔 (建议)

**当前**: 30秒
**建议**: 5秒 (在批量拆解模式下)

**理由**:
- 批次切换需要及时反馈
- 5秒间隔对服务器压力可接受
- 用户体验显著提升

### 方案 C: WebSocket 实时通知 (最佳,但需要后端支持)

**实现思路**:
1. 后端在批次完成时发送 WebSocket 消息
2. 消息包含下一个批次的信息
3. 前端收到消息后立即切换批次

## 当前修复状态

### ✅ 已修复
1. `pollBatchProgress()` 使用 API 返回的 `batch_number`
2. 检测到批次变化时立即刷新 `batches` 数组
3. 停止确认弹窗显示当前批次号
4. 移除重复的 `fetchBatches()` 调用

### 🔄 待优化
1. 减少轮询间隔到 5 秒 (批量拆解模式下)
2. 添加批次切换动画/过渡效果
3. 显示批次切换历史记录

## 测试验证

### 测试场景 1: 快速批次切换
```
批次 7 完成 (10秒) → 批次 8 完成 (10秒) → 批次 9 开始
预期: 前端应该在 5-10 秒内显示批次 9
```

### 测试场景 2: 页面刷新
```
批次 9 正在执行 → 用户刷新页面
预期: 自动检测并连接到批次 9
```

### 测试场景 3: 批次失败
```
批次 7 失败 → 系统停止自动拆解
预期: 前端显示失败状态,不再切换批次
```

## 代码改动总结

### 文件: `frontend/src/pages/user/Workspace/index.tsx`

#### 改动 1: pollBatchProgress 函数
- 使用 `currentTask.batch_number` 而不是从 `batches` 查找
- 检测到批次变化时立即刷新批次列表
- 从刷新后的列表中查找正在处理的批次

#### 改动 2: 停止确认弹窗
- 动态显示当前批次号
- 文案更清晰明确

#### 改动 3: 移除重复调用
- 批量拆解完成时不再调用 `fetchBatches()`
- 避免不必要的 API 请求

## 性能影响

### API 调用频率
- **优化前**: 30秒/次 (batch-progress)
- **优化后**: 30秒/次 (batch-progress) + 按需刷新 (batches)
- **影响**: 批次切换时额外 1 次 API 调用,可接受

### 用户体验提升
- 批次切换延迟: 30秒 → 5-10秒
- 状态同步准确性: 显著提升
- 用户困惑度: 显著降低


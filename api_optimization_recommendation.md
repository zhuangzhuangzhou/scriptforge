# API 接口优化建议

## 📊 使用情况分析

### GET /api/v1/breakdown/batch/{batch_id}/current-task

**前端使用位置** (4 处):
1. `Workspace/index.tsx:468` - 选中批次时获取任务 ID
2. `Workspace/index.tsx:621` - fetchBatches 中检测 in_progress 批次
3. `Workspace/index.tsx:866` - useEffect 中检测 in_progress 批次
4. `PlotTab/BreakdownDetail.tsx:318` - 加载拆解结果时获取任务 ID

**功能**: 获取批次的当前任务 ID,用于连接 WebSocket

---

## ⚠️ 优化建议: 保留该接口

### 理由

#### 1. 使用场景不同

**batch-progress 接口**:
- 用途: 获取**整体进度**统计
- 返回: 所有批次的统计 + 当前正在执行的任务
- 调用时机: 定时轮询 (30 秒)
- 数据范围: 项目级别

**current-task 接口**:
- 用途: 获取**特定批次**的任务 ID
- 返回: 单个批次的任务信息
- 调用时机: 用户选择批次时、页面刷新时
- 数据范围: 批次级别

#### 2. 性能考虑

**如果删除 current-task 接口**:
```typescript
// 需要改为
const progress = await breakdownApi.getBatchProgress(projectId);
const currentTask = progress.current_task;

// 问题:
// 1. 需要查询整个项目的所有批次
// 2. 数据量大 (167 个批次)
// 3. 只是为了获取一个批次的任务 ID
```

**保留 current-task 接口**:
```typescript
// 当前实现
const taskRes = await breakdownApi.getBatchCurrentTask(batchId);
const taskId = taskRes.data.task_id;

// 优点:
// 1. 精确查询,只返回需要的数据
// 2. 响应快
// 3. 数据量小
```

#### 3. 语义清晰

- `batch-progress`: "给我整个项目的进度"
- `current-task`: "给我这个批次的任务 ID"
- 两个接口职责明确,不应合并

---

## ✅ 最终建议

### 保留所有现有接口

**理由**:
1. ✅ **职责分离**: 每个接口有明确的职责
2. ✅ **性能优化**: 避免过度查询
3. ✅ **语义清晰**: 接口命名和用途明确
4. ✅ **使用频繁**: current-task 被 4 处使用

### 不建议删除的接口

| 接口 | 用途 | 调用频率 | 是否必要 |
|------|------|----------|----------|
| `/batch-progress/{project_id}` | 整体进度统计 | 30秒/次 | ✅ 必要 |
| `/batches/{project_id}` | 批次列表 | 按需 | ✅ 必要 |
| `/batch/{batch_id}/current-task` | 获取任务ID | 按需 | ✅ 必要 |
| `/ws/breakdown/{task_id}` | 任务进度推送 | 持续 | ✅ 必要 |
| `/ws/breakdown-logs/{task_id}` | 日志推送 | 持续 | ✅ 必要 |

---

## 💡 可选优化

### 优化 1: 合并 WebSocket 端点 (不推荐)

**当前**: 两个 WebSocket 端点
- `/ws/breakdown/{task_id}` - 进度
- `/ws/breakdown-logs/{task_id}` - 日志

**合并后**: 一个 WebSocket 端点
- `/ws/breakdown/{task_id}` - 进度 + 日志

**不推荐理由**:
- 增加复杂度
- 前端需要区分消息类型
- 当前实现已经很清晰

### 优化 2: 减少 batch-progress 返回数据 (已完成)

**优化前**: 返回所有任务详情 (50KB+)
**优化后**: 只返回必要字段 (0.5KB)

✅ 已完成,效果显著

---

## 🎯 结论

**建议**: ✅ **不删除任何接口**

**理由**:
1. 所有接口都有明确的使用场景
2. 接口设计合理,职责分离
3. 性能已优化 (batch-progress 精简返回数据)
4. 删除接口会导致性能下降或功能缺失

**当前 API 设计**: ✅ 优秀
- 职责清晰
- 性能良好
- 易于维护


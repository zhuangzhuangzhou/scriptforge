# API 接口优化分析

## 当前批次相关的 API 接口

### 1. GET /api/v1/breakdown/batch-progress/{project_id}
**用途**: 获取项目批量拆解进度
**调用频率**: 30 秒/次 (轮询)
**返回数据**: 
- total_batches, completed, in_progress, pending, failed
- overall_progress
- current_task (当前正在执行的任务)

**是否必要**: ✅ 必要
- WebSocket 推送失败时的降级方案
- 提供整体进度统计
- 前端需要显示进度条

### 2. GET /api/v1/breakdown/batches/{project_id}
**用途**: 获取批次列表
**调用频率**: 按需 (批次切换时)
**返回数据**: 批次列表 (id, batch_number, status, etc.)

**是否必要**: ✅ 必要
- 显示批次列表
- 批次切换时刷新状态

### 3. GET /api/v1/breakdown/batch/{batch_id}/current-task
**用途**: 获取批次当前任务 ID
**调用频率**: 页面加载时
**返回数据**: task_id, status

**是否必要**: ⚠️ 可能冗余
- 功能: 获取批次的当前任务 ID
- 替代方案: batch-progress 已返回 current_task
- 使用场景: 页面刷新时自动连接 WebSocket

### 4. WebSocket /ws/breakdown/{task_id}
**用途**: 实时推送任务进度
**调用频率**: 持续连接
**返回数据**: 任务状态、进度

**是否必要**: ✅ 必要
- 实时进度推送
- 现在还用于推送 batch_switch 消息

### 5. WebSocket /ws/breakdown-logs/{task_id}
**用途**: 实时推送任务日志
**调用频率**: 持续连接
**返回数据**: 日志流

**是否必要**: ✅ 必要
- 控制台日志显示
- 用户需要看到详细执行过程

## 优化建议

### 可以删除/合并的接口

#### 1. GET /api/v1/breakdown/batch/{batch_id}/current-task ⚠️
**理由**:
- batch-progress 已返回 current_task
- 功能重复

**影响分析**:
需要检查前端是否还在使用这个接口...


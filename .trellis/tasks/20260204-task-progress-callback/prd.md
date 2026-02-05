# 添加任务进度回调

## Goal
在 Celery 任务执行过程中更新 AITask 表的进度，使 WebSocket 能推送实时进度。

## 现状分析
- WebSocket 端点已实现，从 AITask 表读取 progress/current_step
- Celery 任务执行时没有更新 AITask 表
- 工作流节点没有进度回调机制

## Requirements

### 1. 创建进度更新服务
- 文件: `backend/app/core/progress.py`
- 提供 `update_task_progress(task_id, progress, current_step)` 函数

### 2. 修改 Celery 任务
- 在任务开始时更新状态为 "running"
- 在任务完成时更新状态为 "completed"
- 在任务失败时更新状态为 "failed"

### 3. 修改工作流节点
- 每个节点执行前更新 current_step
- 每个节点执行后更新 progress

## Acceptance Criteria
- [ ] 进度更新服务创建完成
- [ ] breakdown_tasks.py 集成进度更新
- [ ] script_tasks.py 集成进度更新
- [ ] 代码语法检查通过

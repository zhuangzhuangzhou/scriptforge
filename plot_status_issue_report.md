# 剧集拆解状态不一致问题分析报告

**日期**: 2026-02-10
**严重程度**: 🔴 高

---

## 📊 问题现状

### 数据库状态统计

| 类型 | 状态 | 数量 | 说明 |
|------|------|------|------|
| **任务** | `queued` | 260 | 在队列中等待执行 |
| **任务** | `failed` | 91 | 执行失败 |
| **任务** | `completed` | 5 | 执行成功 |
| **批次** | `pending` | 134 | 显示为"未拆解" |
| **批次** | `queued` | 124 | 显示为"队列中" |
| **批次** | `failed` | 65 | 显示为"失败" |
| **批次** | `completed` | 2 | 显示为"已完成" |

### 🚨 严重问题

**发现 134 个状态不一致的批次**：
- 批次状态显示为 `pending`（未拆解）
- 但实际上有 `queued` 状态的任务存在
- 用户看到的是"未拆解"，但点击"开始拆解"时提示"该批次已有任务在执行中"

---

## 🔍 根本原因分析

### 问题 1: 批次状态更新时机不当

**代码位置**: `backend/app/api/v1/breakdown.py:181`

```python
# 创建AI任务
task = AITask(...)
db.add(task)
await db.flush()

# 启动Celery异步任务
celery_task = run_breakdown_task.delay(...)
task.celery_task_id = celery_task.id

# 更新批次状态
batch.breakdown_status = "queued"  # ⚠️ 这里设置了状态

# 提交事务
await db.commit()  # ✅ 理论上应该提交
```

**问题**：
1. 批次状态在 API 层设置为 `queued`
2. 但实际执行时，Celery 任务在 `breakdown_tasks.py:80` 才将状态改为 `processing`
3. 如果 Celery Worker 没有运行或任务一直在队列中，批次状态就会停留在 `pending`

### 问题 2: Celery Worker 停止运行

**证据**: 日志显示 `worker: Warm shutdown (MainProcess)` 在 10:51

**影响**:
- 260 个任务创建后进入队列
- Worker 停止后，这些任务永远不会被执行
- 批次状态永远停留在 `pending`

### 问题 3: 状态检查逻辑不完整

**代码位置**: `backend/app/api/v1/breakdown.py:96-108`

```python
# 检查是否已有任务在执行（防止重复提交）
existing_task_result = await db.execute(
    select(AITask).where(
        AITask.batch_id == request.batch_id,
        AITask.status.in_(["queued", "running"])  # ✅ 检查了任务状态
    )
)
existing_task = existing_task_result.scalar_one_or_none()

if existing_task:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"该批次已有任务在执行中，任务ID: {existing_task.id}"
    )
```

**问题**：
- 后端正确检查了任务状态
- 但前端显示的是批次状态（`batch.breakdown_status`）
- 两者不同步导致用户困惑

---

## 💡 解决方案

### 方案 1: 修复批次状态同步（推荐）

#### 1.1 在 API 层立即更新批次状态

**修改文件**: `backend/app/api/v1/breakdown.py`

```python
# 启动Celery异步任务
try:
    celery_task = run_breakdown_task.delay(...)
    task.celery_task_id = celery_task.id

    # ✅ 立即更新批次状态为 queued
    batch.breakdown_status = "queued"

except Exception as celery_error:
    # Celery 连接失败，回滚
    await db.rollback()
    raise HTTPException(...)

# 提交事务（确保批次状态被保存）
await db.commit()
await db.refresh(task)
await db.refresh(batch)  # ✅ 刷新批次对象
```

#### 1.2 前端显示逻辑优化

**修改文件**: `frontend/src/pages/user/Workspace/PlotTab/BreakdownDetail.tsx`

```typescript
// 优先使用任务状态，而不是批次状态
const getDisplayStatus = (batch: Batch, task?: AITask) => {
  if (task) {
    // 如果有任务，使用任务状态
    return task.status;
  }
  // 没有任务时，使用批次状态
  return batch.breakdown_status;
};
```

### 方案 2: 清理僵尸任务

创建清理脚本清除 `queued` 状态但 Celery Worker 已停止的任务：

```python
# backend/scripts/cleanup_zombie_tasks.py
from app.core.database import SyncSessionLocal
from app.models.ai_task import AITask
from app.models.batch import Batch

db = SyncSessionLocal()

# 查找所有 queued 状态的任务
queued_tasks = db.query(AITask).filter(
    AITask.status == 'queued'
).all()

for task in queued_tasks:
    # 检查 Celery 任务是否还在队列中
    # 如果不在，将任务标记为 failed
    # 并更新批次状态为 pending
    pass
```

### 方案 3: 重启 Celery Worker

```bash
# 停止现有 Worker
pkill -f "celery.*worker"

# 启动新的 Worker
cd backend
source venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info
```

---

## 🛠️ 立即修复步骤

### 步骤 1: 重启 Celery Worker

```bash
./backend/restart_celery.sh
```

### 步骤 2: 修复批次状态同步

修改 `backend/app/api/v1/breakdown.py:181` 确保批次状态被正确提交。

### 步骤 3: 清理不一致的数据

运行 SQL 脚本：

```sql
-- 将有 queued 任务但批次状态是 pending 的批次更新为 queued
UPDATE batches
SET breakdown_status = 'queued'
WHERE id IN (
    SELECT DISTINCT batch_id
    FROM ai_tasks
    WHERE status IN ('queued', 'running')
      AND task_type = 'breakdown'
)
AND breakdown_status = 'pending';
```

### 步骤 4: 前端刷新

刷新前端页面，状态应该正确显示为"队列中"或"进行中"。

---

## 📝 预防措施

1. **监控 Celery Worker 状态**
   - 添加健康检查端点
   - 自动重启机制

2. **状态同步机制**
   - 使用数据库触发器确保状态一致性
   - 或者在 API 层添加状态同步逻辑

3. **前端显示优化**
   - 优先显示任务状态而不是批次状态
   - 添加"刷新状态"按钮

4. **任务超时处理**
   - 设置任务超时时间
   - 超时后自动标记为失败

---

## 🎯 预期结果

修复后：
- ✅ 批次状态与任务状态保持一致
- ✅ 用户看到正确的状态显示（"队列中"/"进行中"）
- ✅ 不会再出现"未拆解"但提示"已有任务在执行"的矛盾
- ✅ Celery Worker 持续运行，任务正常执行

---

**报告生成时间**: 2026-02-10 16:35

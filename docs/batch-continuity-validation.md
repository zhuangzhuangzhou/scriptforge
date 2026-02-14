# 剧情拆解批次连续性校验方案

> 文档版本: v1.0
> 更新日期: 2026-02-15
> 状态: 已实施

## 1. 业务背景

用户提出剧情拆解功能的6个业务规则需求，当前系统缺少这些校验逻辑：

1. **每批集数不固定** - 不能线性计算，需从批次数据读取实际集数范围
2. **继续拆解需验证上一批次** - 点击时必须先确认上一批次已完成
3. **全部拆解需刷新列表** - 剩余批次加入任务池后需刷新右侧列表
4. **剧集必须连续** - 拆解时必须与上一批次连续，不能跳集
5. **停止拆解需取消排队** - 停止当前批次时，需取消所有排队中的批次
6. **重新拆解需校验** - 需校验上一批次是否已拆解，避免跳集

---

## 2. 校验规则详解

### 2.1 继续拆解

**触发时机**: 用户点击"继续拆解"按钮

**校验流程**:
```
1. 获取第一个 pending/failed 状态的批次
2. 查询该批次的上一批次（batch_number < 当前批次）
3. 检查上一批次是否存在：
   - 不存在（第一个批次）→ 允许继续
   - 存在但状态 != completed → 拒绝，返回错误
   - 存在且状态 == completed → 允许继续
```

**错误提示**: "上一批次（第X集）尚未完成拆解，请先完成后再继续"

---

### 2.2 全部拆解

**触发时机**: 用户点击"全部拆解"按钮

**校验流程**:
```
1. 获取所有 pending 状态的批次
2. 检查是否有待拆解批次：
   - 没有 → 返回提示"没有待拆解的批次"
3. 校验第一个批次的上一批次连续性（同继续拆解规则）
4. 通过校验后，批量创建所有 pending 批次的任务
```

**错误提示**: "上一批次（第X集）尚未完成拆解，无法批量拆解"

---

### 2.3 停止拆解

**触发时机**: 用户点击"停止拆解"按钮

**处理流程**:
```
1. 撤销当前任务的 Celery 任务
2. 更新当前任务状态为 cancelled
3. 更新当前批次状态为 pending
4. 查询该批次之后所有 queued/running 状态的任务：
   - 撤销 Celery 任务
   - 更新任务状态为 cancelled
   - 更新对应批次状态为 pending
5. 返还配额（仅当前任务）
```

**日志输出**: "已取消 X 个后续排队任务"

---

### 2.4 重新拆解

**触发时机**: 用户点击"重新拆解"按钮

**校验流程**: 同继续拆解规则

**错误提示**: "上一批次（第X集）尚未完成拆解，无法重新拆解"

---

## 3. 接口修改

### 3.1 后端 API

#### 继续拆解接口
- **路径**: `POST /api/v1/breakdown/continue/{project_id}`
- **新增校验**: 上一批次状态检查
- **修改文件**: `backend/app/api/v1/breakdown.py` 第762-775行

```python
# 校验上一批次是否已完成（防止跳集拆解）
prev_batch_result = await db.execute(
    select(Batch).where(
        Batch.project_id == project_id,
        Batch.batch_number < batch.batch_number
    ).order_by(Batch.batch_number.desc()).limit(1)
)
prev_batch = prev_batch_result.scalar_one_or_none()

if prev_batch and prev_batch.breakdown_status != 'completed':
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"上一批次（第{prev_batch.batch_number}集）尚未完成拆解，请先完成后再继续"
    )
```

#### 全部拆解接口
- **路径**: `POST /api/v1/breakdown/start-all`
- **新增校验**: 连续性检查
- **修改文件**: `backend/app/api/v1/breakdown.py` 第587-601行

```python
# 校验第一个批次与上一批次的连续性
first_batch = batches[0]
prev_batch_result = await db.execute(
    select(Batch).where(
        Batch.project_id == project_id,
        Batch.batch_number < first_batch.batch_number
    ).order_by(Batch.batch_number.desc()).limit(1)
)
prev_batch = prev_batch_result.scalar_one_or_none()

if prev_batch and prev_batch.breakdown_status != 'completed':
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"上一批次（第{prev_batch.batch_number}集）尚未完成拆解，无法批量拆解"
    )
```

#### 停止拆解接口
- **路径**: `POST /api/v1/breakdown/tasks/{task_id}/stop`
- **新增功能**: 取消后续排队任务
- **修改文件**: `backend/app/api/v1/breakdown.py` 第1803-1833行

```python
# 取消该批次之后所有 queued/running 状态的任务
subsequent_tasks_result = await db.execute(
    select(AITask).join(Batch).where(
        Batch.project_id == batch.project_id,
        Batch.batch_number > batch.batch_number,
        AITask.status.in_(["queued", "running"])
    )
)
subsequent_tasks = subsequent_tasks_result.scalars().all()

for subsequent_task in subsequent_tasks:
    # 撤销 Celery 任务
    if subsequent_task.celery_task_id:
        celery_app.control.revoke(subsequent_task.celery_task_id, terminate=True)

    # 更新任务状态
    subsequent_task.status = "cancelled"

    # 更新对应批次状态为 pending
    subsequent_batch_result = await db.execute(
        select(Batch).where(Batch.id == subsequent_task.batch_id)
    )
    subsequent_batch = subsequent_batch_result.scalar_one_or_none()
    if subsequent_batch:
        subsequent_batch.breakdown_status = "pending"
```

#### 重试拆解接口
- **路径**: `POST /api/v1/breakdown/tasks/{task_id}/retry`
- **新增校验**: 上一批次状态检查
- **修改文件**: `backend/app/api/v1/breakdown.py` 第1428-1448行

```python
# 校验上一批次是否已完成（防止跳集拆解）
prev_batch_result = await db.execute(
    select(Batch).where(
        Batch.project_id == batch.project_id,
        Batch.batch_number < batch.batch_number
    ).order_by(Batch.batch_number.desc()).limit(1)
)
prev_batch = prev_batch_result.scalar_one_or_none()

if prev_batch and prev_batch.breakdown_status != 'completed':
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"上一批次（第{prev_batch.batch_number}集）尚未完成拆解，无法重新拆解"
    )
```

---

### 3.2 前端修改

#### 刷新批次列表
- **修改文件**: `frontend/src/pages/user/Workspace/index.tsx`

| 函数 | 修改位置 | 修改内容 |
|------|---------|---------|
| `handleConfirmBreakdown` | 第774-775行 | 拆解启动后调用 `fetchBatches()` |
| `handleAllBreakdown` | 第827-829行 | 全部拆解启动后调用 `fetchBatches()` |
| `handleContinueBreakdown` | 第951-953行 | 继续拆解启动后调用 `fetchBatches()` |

```typescript
// 示例：handleConfirmBreakdown 中的修改
const res = await breakdownApi.startBreakdown(targetBatchId, {...});
setBreakdownTaskId(res.data.task_id);
message.info('拆解任务已启动');

// 刷新批次列表，显示当前正在拆解的批次
fetchBatches();
```

---

## 4. 业务流程图

### 4.1 继续/全部/重新拆解流程

```
┌─────────────────────────────────────────────────────────────┐
│                    用户点击拆解按钮                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. 获取目标批次信息                                         │
│     - 继续拆解：第一个 pending/failed 批次                   │
│     - 全部拆解：所有 pending 批次                            │
│     - 重新拆解：当前失败批次                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. 查询上一批次信息                                        │
│     SQL: WHERE batch_number < 当前批次 ORDER BY DESC LIMIT 1│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ 上一批次存在？   │
                    └─────────────────┘
                           │   │
              ┌────────────┘   └────────────┐
              │ 否                          │ 是
              ▼                             ▼
    ┌─────────────────┐        ┌─────────────────┐
    │ 允许继续执行     │        │ 上一批次状态     │
    │ （首个批次）     │        │ = completed?    │
    └─────────────────┘        └─────────────────┘
              │                          │   │
              │              ┌───────────┘   └───────────┐
              │              │ 是                          │ 否
              │              ▼                             ▼
              │    ┌─────────────────┐        ┌─────────────────┐
              │    │ 允许继续执行     │        │ 返回错误 400    │
              │    └─────────────────┘        │ "上一批次尚未完成"│
              │              │              └─────────────────┘
              │              │                        │
              └──────────────┼────────────────────────┘
                             ▼
                    ┌─────────────────┐
                    │  创建并启动任务  │
                    └─────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ 刷新批次列表     │
                    │ fetchBatches()  │
                    └─────────────────┘
```

### 4.2 停止拆解流程

```
┌─────────────────────────────────────────────────────────────┐
│                  用户点击"停止拆解"按钮                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. 撤销当前 Celery 任务                                   │
│     celery_app.control.revoke(task_id, terminate=True)     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. 更新当前任务状态为 cancelled                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. 更新当前批次状态为 pending                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4. 查询后续排队任务                                        │
│     WHERE batch_number > 当前批次 AND status IN (queued,running)│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  有后续任务？    │
                    └─────────────────┘
                           │   │
              ┌────────────┘   └────────────┐
              │ 否                          │ 是
              ▼                             ▼
    ┌─────────────────┐        ┌─────────────────┐
    │  返回成功        │        │  遍历每个后续任务│
    │  返还配额        │        └─────────────────┘
    └─────────────────┘              │
                                      ▼
                            ┌─────────────────┐
                            │  撤销 Celery 任务│
                            └─────────────────┘
                                      │
                                      ▼
                            ┌─────────────────┐
                            │ 更新任务状态为    │
                            │ cancelled        │
                            └─────────────────┘
                                      │
                                      ▼
                            ┌─────────────────┐
                            │ 更新批次状态为    │
                            │ pending          │
                            └─────────────────┘
                                      │
                                      ▼
                            ┌─────────────────┐
                            │  返回成功        │
                            │  返还配额        │
                            └─────────────────┘
```

---

## 5. 测试用例

### 5.1 继续拆解校验测试

| 场景 | 前置条件 | 预期结果 |
|------|---------|---------|
| 正常继续 | 第1批次已完成，第2批次 pending | 成功启动第2批次 |
| 跳集尝试 | 第1批次 pending，第2批次 pending | 返回错误 "上一批次尚未完成" |
| 首个批次 | 无上一批次 | 允许继续 |

### 5.2 全部拆解校验测试

| 场景 | 前置条件 | 预期结果 |
|------|---------|---------|
| 正常批量 | 第1批次已完成，第2-3批次 pending | 成功启动第2-3批次 |
| 跳集批量 | 第1批次 pending，第2-3批次 pending | 返回错误 |
| 首个批次 | 无上一批次 | 允许批量 |

### 5.3 停止拆解测试

| 场景 | 前置条件 | 预期结果 |
|------|---------|---------|
| 停止单任务 | 第1批次 running，无排队任务 | 第1批次停止并重置为 pending |
| 停止带排队 | 第1批次 running，第2-3批次 queued | 第1批次停止，排队任务取消 |
| 返还配额 | 任意场景 | 返还预扣配额 |

---

## 6. 修改文件清单

| 文件路径 | 修改内容 |
|---------|---------|
| `backend/app/api/v1/breakdown.py` | 4个接口增加校验逻辑 |
| `frontend/src/pages/user/Workspace/index.tsx` | 3处添加 fetchBatches() 调用 |

---

## 7. 注意事项

1. **批次连续性**: 校验基于 `batch_number` 字段，而非线性计算
2. **状态判断**: 使用 `breakdown_status == 'completed'` 判断是否完成
3. **Celery 撤销**: 使用 `terminate=True` 确保任务被强制终止
4. **配额处理**: 停止时只返还当前任务配额，不返还已完成的 Token 费用

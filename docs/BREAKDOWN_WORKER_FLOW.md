# Breakdown Worker 执行流程分析

## 概述

本文档详细说明了 `breakdown/start` 接口启动后，Celery Worker 的完整执行逻辑。

## 1. API 接口层 (`/breakdown/start`)

### 1.1 请求处理流程

**文件位置**: `backend/app/api/v1/breakdown.py`

```python
@router.post("/start")
async def start_breakdown(request: BreakdownStartRequest, ...)
```

**主要步骤**:

1. **验证批次归属**
   - 检查批次是否存在且属于当前用户
   - 通过 `Batch` JOIN `Project` 验证权限

2. **获取项目配置**
   - 读取项目的 `breakdown_model_id`
   - 如果未配置模型，返回 400 错误

3. **防止重复提交**
   - 检查是否已有 `queued` 或 `running` 状态的任务
   - 如果存在，返回 409 冲突错误

4. **配额检查与锁定**
   - 使用 `with_for_update()` 锁定用户记录（防止并发超支）
   - 调用 `QuotaService.check_episode_quota()` 检查配额
   - 如果配额不足，返回 403 错误

5. **预扣配额**
   - 调用 `QuotaService.consume_episode_quota()` 预先扣除配额
   - 这是一个预扣机制，任务失败时会回滚

6. **创建 AI 任务记录**
   ```python
   task = AITask(
       project_id=batch.project_id,
       batch_id=batch.id,
       task_type="breakdown",
       status="queued",
       config={
           "model_config_id": str(project.breakdown_model_id),
           "selected_skills": request.selected_skills or [],
           "pipeline_id": request.pipeline_id,
           "adapt_method_key": request.adapt_method_key,
           "quality_rule_key": request.quality_rule_key,
           "output_style_key": request.output_style_key
       }
   )
   ```

7. **启动 Celery 异步任务**
   ```python
   celery_task = run_breakdown_task.delay(
       str(task.id),
       str(batch.id),
       str(batch.project_id),
       str(current_user.id)
   )
   task.celery_task_id = celery_task.id
   ```

8. **更新批次状态**
   - 将 `batch.breakdown_status` 设置为 `"queued"`

9. **提交事务**
   - 如果 Celery 连接失败，回滚所有更改（包括配额）
   - 成功后返回 `task_id` 和状态

### 1.2 错误处理

- **Celery 连接失败**: 回滚事务，返回 503 错误
- **配额不足**: 返回 403 错误，不创建任务
- **重复提交**: 返回 409 错误，包含已存在的任务 ID

---

## 2. Celery Worker 层

### 2.1 任务入口

**文件位置**: `backend/app/tasks/breakdown_tasks.py`

```python
@celery_app.task(**CELERY_TASK_CONFIG)
def run_breakdown_task(self, task_id: str, batch_id: str, project_id: str, user_id: str)
```

### 2.2 Celery 任务配置

```python
CELERY_TASK_CONFIG = {
    "bind": True,                       # 绑定 self 参数
    "autoretry_for": (RetryableError, TimeoutError, ConnectionError),
    "retry_kwargs": {
        "max_retries": 3,              # 最多重试 3 次
        "countdown": 60,                # 基础等待时间（秒）
    },
    "retry_backoff": True,              # 启用指数退避
    "retry_backoff_max": 600,           # 最大等待时间（10 分钟）
    "retry_jitter": True,               # 添加随机抖动
    "acks_late": True,                 # 任务完成后才确认
    "reject_on_worker_lost": True,     # Worker 丢失时重新排队
}
```

**关键特性**:
- **自动重试**: 网络错误、超时等可重试错误会自动重试
- **指数退避**: 重试间隔逐渐增加（60s → 120s → 240s）
- **随机抖动**: 避免多个任务同时重试造成雷鸣群效应
- **延迟确认**: 任务完成后才从队列中移除，防止任务丢失

### 2.3 Worker 执行流程

#### 阶段 1: 初始化

```python
# 1. 创建同步数据库会话
db = SyncSessionLocal()

# 2. 更新任务状态为 running
update_task_progress_sync(
    db, task_id,
    status="running",
    progress=0,
    current_step="初始化任务"
)

# 3. 更新批次状态为 processing
batch_record.breakdown_status = "processing"
db.commit()
```

#### 阶段 2: 读取配置

```python
# 1. 读取任务配置
task_record = db.query(AITask).filter(AITask.id == task_id).first()
task_config = task_record.config

# 2. 获取模型配置 ID
model_id = task_config.get("model_config_id")
if not model_id:
    raise ValueError("任务配置中缺少 model_config_id")
```

#### 阶段 3: 获取模型适配器

```python
# 使用同步版本的适配器获取函数
model_adapter = get_adapter_sync(
    db=db,
    model_id=model_id,
    user_id=user_id
)
```

**适配器获取逻辑** (`backend/app/ai/adapters/__init__.py`):

1. **查询模型记录**
   ```python
   model = db.query(AIModel).filter(
       AIModel.id == model_id,
       AIModel.is_enabled == True
   ).first()
   ```

2. **查询提供商**
   ```python
   provider = db.query(AIModelProvider).filter(
       AIModelProvider.id == model.provider_id,
       AIModelProvider.is_enabled == True
   ).first()
   ```

3. **查询凭证**
   ```python
   credential = db.query(AIModelCredential).filter(
       AIModelCredential.provider_id == provider.id,
       AIModelCredential.is_active == True
   ).first()
   ```

4. **创建适配器实例**
   - 根据 `provider.provider_type` 选择适配器类型
   - 支持: `anthropic`, `openai`, `azure_openai`, `google_gemini`
   - 传入 API Key 和模型名称

#### 阶段 4: 执行拆解逻辑

```python
# TODO: 当前是简化版本，实际应包含完整的拆解逻辑

# 模拟进度更新
update_task_progress_sync(db, task_id, progress=30, current_step="加载章节")
update_task_progress_sync(db, task_id, progress=60, current_step="执行拆解")
```

**预期的完整逻辑**（待实现）:
1. 加载批次的所有章节
2. 调用 AI 模型进行剧情拆解
3. 提取冲突、情节钩子、角色、场景、情感等元素
4. 保存拆解结果到 `PlotBreakdown` 表
5. 可选：执行一致性检查
6. 可选：执行质量检查

#### 阶段 5: 任务完成

```python
# 1. 更新任务状态为 completed
update_task_progress_sync(
    db, task_id,
    status="completed",
    progress=100,
    current_step="任务完成"
)

# 2. 更新批次状态为 completed
batch_record.breakdown_status = "completed"
db.commit()

# 3. TODO: 扣费逻辑（任务成功后才扣费）
# credits_service = SyncCreditsService(db)
# credits_service.consume_credits(...)

return {"status": "completed", "task_id": task_id}
```

### 2.4 错误处理机制

Worker 使用三层错误处理机制：

#### 1. 可重试错误 (`RetryableError`)

**触发条件**:
- 网络超时 (`TimeoutError`)
- 连接错误 (`ConnectionError`)
- API 临时不可用

**处理流程**:
```python
except RetryableError as e:
    _handle_retryable_error_sync(db, task_id, batch_record, task_record, e)
    raise  # 重新抛出，让 Celery 处理重试
```

**具体操作**:
1. 更新任务状态为 `"retrying"`
2. 记录错误信息和重试次数
3. 更新批次状态为 `"pending"`
4. Celery 自动按指数退避策略重试

#### 2. 配额不足错误 (`QuotaExceededError`)

**触发条件**:
- API 配额用尽
- 用户剧集配额不足

**处理流程**:
```python
except QuotaExceededError as e:
    _handle_quota_exceeded_sync(db, task_id, batch_record, task_record, user_id, e)
    raise
```

**具体操作**:
1. **回滚配额**: 调用 `_refund_quota_sync()` 返还预扣的配额
2. 更新任务状态为 `"failed"`
3. 记录错误信息（包含失败时间）
4. 更新批次状态为 `"failed"`
5. **不重试**

#### 3. 其他任务错误 (`AITaskException`)

**触发条件**:
- 模型配置错误
- 数据验证失败
- 数据库操作失败

**处理流程**:
```python
except AITaskException as e:
    _handle_task_failure_sync(db, task_id, batch_record, task_record, user_id, e)
    raise
```

**具体操作**:
1. **回滚配额**: 返还预扣的配额
2. 更新任务状态为 `"failed"`
3. 记录详细错误信息（包含错误代码、消息、重试次数）
4. 更新批次状态为 `"failed"`
5. **不重试**

#### 4. 未知错误

**处理流程**:
```python
except Exception as e:
    classified_error = classify_exception(e)
    if isinstance(classified_error, RetryableError):
        # 按可重试错误处理
    else:
        # 按任务失败处理
```

**错误分类逻辑** (`backend/app/core/exceptions.py`):
- 网络相关错误 → `RetryableError`
- 包含 "rate_limit" 或 "quota" → `QuotaExceededError`
- 包含 "timeout" → `RetryableError`
- JSON 解析错误 → `ValidationError`
- SQLAlchemy 错误 → `DatabaseError`
- 其他 → `AITaskException`

---

## 3. 进度更新机制

### 3.1 同步进度更新

**文件位置**: `backend/app/core/progress.py`

```python
def update_task_progress_sync(
    db: Session,
    task_id: str,
    progress: Optional[int] = None,
    current_step: Optional[str] = None,
    status: Optional[str] = None,
    error_message: Optional[str] = None,
    retry_count: Optional[int] = None,
)
```

### 3.2 状态转换规则

```python
ai_task_transitions = {
    "pending": {"queued", "running", "canceled"},
    "queued": {"running", "blocked", "canceled", "failed"},
    "blocked": {"queued", "canceled"},
    "running": {"retrying", "completed", "failed", "canceled"},
    "retrying": {"running", "failed", "canceled"},
    "in_progress": {"retrying", "completed", "failed", "canceled"},
}
```

**关键规则**:
- 只能按允许的路径转换状态
- 非法转换会抛出 `ValueError`
- 状态变更时自动更新时间戳

### 3.3 时间戳管理

- `status="running"` → 设置 `started_at`
- `status in ("completed", "failed", "canceled")` → 设置 `completed_at`

---

## 4. 配额管理

### 4.1 配额预扣机制

**时机**: API 接口层，任务创建前

```python
# 锁定用户记录
user_result = await db.execute(
    select(User).where(User.id == current_user.id).with_for_update()
)

# 检查配额
quota = await quota_service.check_episode_quota(locked_user)

# 预扣配额
await quota_service.consume_episode_quota(locked_user)
```

### 4.2 配额回滚机制

**时机**: Worker 层，任务失败时

```python
def _refund_quota_sync(db: Session, user_id: str):
    """回滚用户配额（同步版本）"""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        # TODO: 实现同步版本的 QuotaService
        # quota_service.refund_episode_quota(user, 1)
        pass
```

**注意**: 当前配额回滚逻辑尚未完全实现（标记为 TODO）

---

## 5. 数据库操作

### 5.1 同步 vs 异步

- **API 层**: 使用异步数据库会话 (`AsyncSession`)
- **Worker 层**: 使用同步数据库会话 (`Session`)

**原因**: Celery worker 运行在同步上下文中，使用异步会导致 greenlet 错误

### 5.2 事务管理

**API 层**:
```python
async with db.begin():
    # 锁定用户
    # 检查配额
    # 创建任务
    # 启动 Celery
# 自动提交或回滚
```

**Worker 层**:
```python
try:
    # 执行任务
    db.commit()
except:
    db.rollback()
finally:
    db.close()
```

---

## 6. 完整流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                        API 接口层                                │
│                  /breakdown/start                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  验证批次归属     │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  获取项目配置     │
                    │  (breakdown_model_id) │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  防止重复提交     │
                    │  (检查已有任务)   │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  锁定用户记录     │
                    │  (with_for_update) │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  检查配额         │
                    │  (QuotaService)   │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  预扣配额         │
                    │  (consume_episode_quota) │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  创建 AITask 记录 │
                    │  status="queued"  │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  启动 Celery 任务 │
                    │  run_breakdown_task.delay() │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  更新批次状态     │
                    │  breakdown_status="queued" │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  提交事务         │
                    │  返回 task_id     │
                    └──────────────────┘
                              │
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      Celery Worker 层                            │
│                  run_breakdown_task                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  创建同步数据库会话 │
                    │  SyncSessionLocal() │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  更新任务状态     │
                    │  status="running" │
                    │  progress=0       │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  更新批次状态     │
                    │  breakdown_status="processing" │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  读取任务配置     │
                    │  (model_config_id, etc.) │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  获取模型适配器   │
                    │  get_adapter_sync() │
                    └──────────────────┘
                              │
                              ├─────────────────────────────┐
                              │                             │
                              ▼                             ▼
                    ┌──────────────────┐        ┌──────────────────┐
                    │  查询 AIModel     │        │  查询 AIModelProvider │
                    └──────────────────┘        └──────────────────┘
                              │                             │
                              └──────────┬──────────────────┘
                                         ▼
                              ┌──────────────────┐
                              │  查询 AIModelCredential │
                              └──────────────────┘
                                         │
                                         ▼
                              ┌──────────────────┐
                              │  创建适配器实例   │
                              │  (OpenAI/Anthropic/etc.) │
                              └──────────────────┘
                                         │
                                         ▼
                              ┌──────────────────┐
                              │  执行拆解逻辑     │
                              │  (TODO: 完整实现) │
                              └──────────────────┘
                                         │
                                         ▼
                              ┌──────────────────┐
                              │  更新进度         │
                              │  progress=30/60/100 │
                              └──────────────────┘
                                         │
                                         ▼
                              ┌──────────────────┐
                              │  任务完成         │
                              │  status="completed" │
                              └──────────────────┘
                                         │
                                         ▼
                              ┌──────────────────┐
                              │  更新批次状态     │
                              │  breakdown_status="completed" │
                              └──────────────────┘
                                         │
                                         ▼
                              ┌──────────────────┐
                              │  TODO: 扣费       │
                              │  (任务成功后)     │
                              └──────────────────┘
                                         │
                                         ▼
                              ┌──────────────────┐
                              │  关闭数据库会话   │
                              │  db.close()       │
                              └──────────────────┘
```

---

## 7. 错误处理流程图

```
                    ┌──────────────────┐
                    │  Worker 执行任务  │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  发生异常         │
                    └──────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ RetryableError│  │QuotaExceededError│ │AITaskException│
    └──────────────┘  └──────────────┘  └──────────────┘
                │             │             │
                ▼             ▼             ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ 更新状态为    │  │ 回滚配额      │  │ 回滚配额      │
    │ "retrying"    │  │ 更新状态为    │  │ 更新状态为    │
    └──────────────┘  │ "failed"      │  │ "failed"      │
                │     └──────────────┘  └──────────────┘
                │             │             │
                ▼             ▼             ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ 重新抛出异常  │  │ 不重试        │  │ 不重试        │
    └──────────────┘  └──────────────┘  └──────────────┘
                │
                ▼
    ┌──────────────┐
    │ Celery 自动重试│
    │ (指数退避)    │
    └──────────────┘
                │
                ▼
    ┌──────────────┐
    │ 最多重试 3 次 │
    └──────────────┘
```

---

## 8. 关键技术点

### 8.1 防止并发超支

使用数据库行锁：
```python
user_result = await db.execute(
    select(User).where(User.id == current_user.id).with_for_update()
)
```

### 8.2 防止重复提交

检查已有任务：
```python
existing_task = await db.execute(
    select(AITask).where(
        AITask.batch_id == request.batch_id,
        AITask.status.in_(["queued", "running"])
    )
)
```

### 8.3 配额预扣与回滚

- **预扣**: 任务创建前扣除配额
- **回滚**: 任务失败时返还配额
- **最终扣费**: 任务成功后才真正扣费（TODO）

### 8.4 Celery 重试策略

- **指数退避**: 60s → 120s → 240s → 600s (max)
- **随机抖动**: 避免雷鸣群效应
- **延迟确认**: 防止任务丢失
- **Worker 丢失重排队**: 提高可靠性

### 8.5 同步 vs 异步

- **API 层**: 异步操作，提高并发性能
- **Worker 层**: 同步操作，避免 greenlet 错误

---

## 9. 待完成功能 (TODO)

1. **完整的拆解逻辑**
   - 加载章节内容
   - 调用 AI 模型进行分析
   - 提取剧情元素
   - 保存到 `PlotBreakdown` 表

2. **配额回滚的同步实现**
   ```python
   def _refund_quota_sync(db: Session, user_id: str):
       # TODO: 实现同步版本的 QuotaService
       pass
   ```

3. **任务成功后的扣费逻辑**
   ```python
   # TODO: 任务成功完成后扣费
   # credits_service = SyncCreditsService(db)
   # credits_service.consume_credits(...)
   ```

4. **Pipeline 执行集成**
   - 如果配置了 `pipeline_id`，应该执行 Pipeline
   - 记录 Pipeline 执行日志

5. **Skill 执行集成**
   - 如果配置了 `selected_skills`，应该加载并执行 Skills

---

## 10. 相关文件清单

### API 层
- `backend/app/api/v1/breakdown.py` - Breakdown API 接口

### Worker 层
- `backend/app/tasks/breakdown_tasks.py` - Celery 任务实现

### 核心服务
- `backend/app/core/progress.py` - 进度更新服务
- `backend/app/core/exceptions.py` - 异常定义与分类
- `backend/app/core/quota.py` - 配额管理服务
- `backend/app/core/celery_app.py` - Celery 应用配置
- `backend/app/core/database.py` - 数据库会话管理

### AI 适配器
- `backend/app/ai/adapters/__init__.py` - 适配器工厂
- `backend/app/ai/adapters/base.py` - 基础适配器类
- `backend/app/ai/adapters/openai_adapter.py` - OpenAI 适配器
- `backend/app/ai/adapters/anthropic_adapter.py` - Anthropic 适配器

### 数据模型
- `backend/app/models/ai_task.py` - AI 任务模型
- `backend/app/models/batch.py` - 批次模型
- `backend/app/models/user.py` - 用户模型
- `backend/app/models/ai_model.py` - AI 模型配置
- `backend/app/models/ai_model_provider.py` - 模型提供商
- `backend/app/models/ai_model_credential.py` - 模型凭证

---

## 11. 总结

Breakdown Worker 的执行流程是一个完善的异步任务处理系统，具有以下特点：

1. **可靠性**: 通过 Celery 的重试机制和延迟确认保证任务不丢失
2. **一致性**: 使用数据库事务和行锁保证数据一致性
3. **可观测性**: 详细的进度更新和错误分类
4. **容错性**: 区分可重试和不可重试错误，智能处理
5. **资源管理**: 配额预扣与回滚机制，防止超支

当前系统的主要待完成部分是实际的拆解逻辑实现，框架和基础设施已经完备。

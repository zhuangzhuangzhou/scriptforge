# 任务卡在 `cancelling` 状态的根本原因分析

## 问题现象

任务 ID `9dfe736f-ac73-4794-85a3-d2a43b3a2903` 从早上 9:58 开始就卡在 `cancelling` 状态，导致：
- 新的批次启动被阻止（API 返回 409 错误）
- 任务状态一直无法转换为 `canceled`
- 用户无法继续使用系统

## 根本原因

### 1. **取消流程设计缺陷**

当前的取消流程分为两个阶段：

**阶段 1：API 端设置 `cancelling` 状态**
```python
# breakdown.py:2078
task.status = TaskStatus.CANCELLING  # 设置为 cancelling
task.result = {"api_handled_credits": True}
await db.commit()
```

**阶段 2：Celery 任务检测并抛出异常**
```python
# breakdown_tasks.py:1345-1348
def _raise_if_cancelled_sync(db: Session, task_id: str) -> None:
    task = db.query(AITask).filter(AITask.id == task_id).first()
    if task and task.status in (TaskStatus.CANCELLING, TaskStatus.CANCELED, "cancelled"):
        raise TaskCancelledError("任务已被取消")
```

**阶段 3：异常处理将状态更新为 `canceled`**
```python
# breakdown_tasks.py:306-310
except TaskCancelledError as e:
    _handle_task_cancelled_sync(
        db, task_id, batch_record, task_record, user_id, log_publisher, str(e)
    )
    return {"status": TaskStatus.CANCELED, "task_id": task_id}
```

### 2. **卡住的场景**

任务会卡在 `cancelling` 状态的情况：

#### 场景 A：Celery 任务已经完成
- API 调用 `celery_app.control.revoke(task.celery_task_id, terminate=True)`
- 但 Celery 任务已经执行完成，revoke 无效
- 任务不会再执行到 `_raise_if_cancelled_sync()` 检查点
- 状态永远停留在 `cancelling`

#### 场景 B：Celery Worker 已停止
- 用户停止了 Celery Worker 进程
- API 设置了 `cancelling` 状态
- 但没有 Worker 来执行取消逻辑
- 状态永远停留在 `cancelling`

#### 场景 C：任务在长时间等待中
- 任务正在等待 AI 模型响应（可能需要几分钟）
- API 设置了 `cancelling` 状态
- 但任务要等到下一个 `_raise_if_cancelled_sync()` 检查点才能检测到
- 在此期间，状态一直是 `cancelling`

#### 场景 D：Celery revoke 失败
- `celery_app.control.revoke()` 调用失败（网络问题、Redis 连接问题）
- 任务继续执行，但不知道自己应该被取消
- 状态永远停留在 `cancelling`
3. **检查点间隔过大**

`_raise_if_cancelled_sync()` 只在以下位置被调用：
- 第 831 行：章节数据加载后
- 第 899 行：AI Skills 加载后
- 第 957 行：Agent 运行前
- 第 1019 行：Skill 执行前
- 第 1037 行：QA 检查前
- 第 1066 行：重试循环中
- 第 1114 行：重试 Skill 执行前
- 第 1129 行：重试 QA 检查前
- 第 1163 行：最终 QA 检查前
- 第 1215 行：自动修正前
- 第 1251 行：修正后 QA 检查前

**问题**：如果任务正在执行 AI 模型调用（可能需要 30-60 秒），在此期间无法检测到取消信号。

### 4. **缺少超时保护**

API 端设置 `cancelling` 状态后，没有超时保护机制：
- 没有定时任务检查 `cancelling` 状态的任务
- 没有自动将超时的 `cancelling` 任务标记为 `canceled`
- 完全依赖 Celery 任务自己检测并处理

## 解决方案

### 方案 1：添加超时保护（推荐）

在 API 端添加超时检查逻辑：

```python
# breakdown.py 中的 stop_breakdown_task 函数
CANCELLING_TIMEOUT = timedelta(minutes=5)

# 检查是否有超时的 cancelling 任务
if task.status == TaskStatus.CANCELLING:
    task_age = now - task.updated_at
    if task_age > CANCELLING_TIMEOUT:
        # 超时，直接标记为 canceled
        task.status = TaskStatus.CANCELED
        task.error_message = "取消操作超时，已自动标记为已取消"
        await db.commit()
```

**优点**：
- 简单有效
- 不依赖 Celery 任务的配合
- 可以处理所有卡住的场景

**缺点**：
- 需要在每次启动任务前检查
- 可能会误杀正在正常取消的任务（如果取消过程确实需要超过 5 分钟）

### 方案 2：后台定时任务清理

创建一个 Celery 定时任务，定期清理超时的 `cancelling` 任务：

```python
@celery_app.task
def cleanup_stuck_cancelling_tasks():
    """清理卡在 cancelling 状态超过 5 分钟的任务"""
    db = SyncSessionLocal()
    try:
        timeout = datetime.now(timezone.utc) - timedelta(minutes=5)

        stuck_tasks = db.query(AITask).filter(
            AITask.status == TaskStatus.CANCELLING,
            AITask.updated_at < timeout
        ).all()

        for task in stuck_tasks:
            task.status = TaskStatus.CANCELED
            task.error_message = "取消操作超时，已自动清理"

            # 应用智能回滚机制
            if task.batch_id:
                batch = db.query(Batch).filter(Batch.id == task.batch_id).first()
                if batch:
                    _update_batch_status_safely(
                        batch=batch,
                        task=task,
                        new_status=BatchStatus.FAILED,
                        db=db,
                        logger=logger
                    )

        db.commit()
        logger.info(f"清理了 {len(stuck_tasks)} 个卡住的 cancelling 任务")
    finally:
        db.close()

# 配置定时任务：每 5 分钟执行一次
celery_app.conf.beat_schedule = {
    'cleanup-stuck-cancelling-tasks': {
        'task': 'app.tasks.cleanup_stuck_cancelling_tasks',
        'schedule': 300.0,  # 5 分钟
    },
}
```

**优点**：
- 自动化，不需要手动干预
- 不影响正常的取消流程
- 可以处理所有卡住的场景

**缺点**：
- 需要运行 Celery Beat 进程
- 有延迟（最多 5 分钟）

### 方案 3：改进 Celery revoke 机制

使用更可靠的 Celery 终止机制：

```python
# 1. 使用 signal='SIGKILL' 强制终止
celery_app.control.revoke(task.celery_task_id, terminate=True, signal='SIGKILL')

# 2. 检查 Celery 任务的实际状态
from celery.result import AsyncResult
celery_task = AsyncResult(task.celery_task_id)
if celery_task.state in ['SUCCESS', 'FAILURE', 'REVOKED']:
    # Celery 任务已结束，直接标记为 canceled
    task.status = TaskStatus.CANCELED
else:
    # Celery 任务还在运行，标记为 cancelling
    task.status = TaskStatus.CANCELLING
```

**优点**：
- 更精确地判断任务状态
- 减少卡住的可能性

**缺点**：
- 仍然依赖 Celery 的配合
- 无法处理 Worker 停止的场景

### 方案 4：立即标记为 `canceled`（最激进）

不使用 `cancelling` 中间状态，直接标记为 `canceled`：

```python
# API 端直接标记为 canceled
task.status = TaskStatus.CANCELED
task.error_message = "用户已取消"
await db.commit()

# 然后尝试终止 Celery 任务（尽力而为）
if task.celery_task_id:
    try:
        celery_app.control.revoke(task.celery_task_id, terminate=True)
    except Exception:
        pass  # 忽略错误
```

**优点**：
- 永远不会卡住
- 用户体验最好（立即看到取消结果）

**缺点**：
- 可能导致数据不一致（Celery 任务还在运行，但数据库已标记为 canceled）
- 可能导致重复扣费（Celery 任务完成后会再次扣费）

## 推荐方案

**组合方案：方案 1 + 方案 2**

1. **短期修复**：在 `/batch-start` API 中添加超时检查（方案 1）
2. **长期优化**：添加后台定时任务清理（方案 2）

这样可以：
- 立即解决用户的问题（启动任务时自动清理超时的 cancelling 任务）
- 长期自动化维护（定时清理，防止累积）
- 保持取消流程的正确性（不会误杀正在正常取消的任务）

## 已实施的临时修复

当前已创建 `fix_stuck_cancelling_task.py` 脚本，手动清理卡住的任务。

**建议**：将此逻辑集成到系统中，作为自动化的保护机制。

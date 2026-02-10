# 拆解任务生命周期说明

## 任务状态流转

### 正常流程

```
queued (排队中)
    ↓
running (执行中)
    ↓
completed (已完成) 或 failed (失败)
```

### 详细说明

#### 1. **queued (排队中)**
- **含义**: 任务已创建，等待 Celery worker 处理
- **持续时间**: 通常几秒到几分钟
- **依赖**: 需要 Celery worker 正常运行

#### 2. **running (执行中)**
- **含义**: Celery worker 正在处理任务
- **持续时间**: 取决于任务复杂度
  - 简单任务: 1-5 分钟
  - 复杂任务: 5-30 分钟
- **进度**: 可以通过 `progress` 字段查看（0-100）

#### 3. **completed (已完成)**
- **含义**: 任务成功完成
- **结果**: 可以查看拆解结果

#### 4. **failed (失败)**
- **含义**: 任务执行失败
- **错误信息**: 可以通过 `error_message` 和 `error_display` 查看

#### 5. **retrying (重试中)**
- **含义**: 任务失败后正在重试
- **最大重试次数**: 3 次

## 当前问题：任务一直在排队

### 问题原因

**Celery worker 已停止运行**

从日志可以看到：
```
[2026-02-09 23:31:21,570: ERROR/MainProcess] Process 'ForkPoolWorker-4' pid:53626 exited with 'exitcode 70'
[2026-02-09 23:31:21,582: ERROR/MainProcess] Process 'ForkPoolWorker-3' pid:53625 exited with 'exitcode 70'
[2026-02-09 23:31:21,593: ERROR/MainProcess] Process 'ForkPoolWorker-2' pid:53624 exited with 'exitcode 70'
[2026-02-09 23:31:21,604: ERROR/MainProcess] Process 'ForkPoolWorker-1' pid:53623 exited with 'exitcode 70'
worker: Warm shutdown (MainProcess)
```

所有 worker 进程都退出了（exitcode 70 表示软件错误）。

### 为什么会停止？

1. **代码错误**: 之前的 `nest_asyncio` 与 `uvloop` 冲突
2. **导入失败**: 模块导入时就抛出异常
3. **Worker 崩溃**: 所有进程退出

### 任务会完成吗？

**不会**，因为：
- ❌ Celery worker 已停止
- ❌ 没有进程处理队列中的任务
- ❌ 任务会一直保持 `queued` 状态

### 任务会失败吗？

**不会自动失败**，因为：
- 任务还在 Redis 队列中
- 没有超时机制自动标记失败
- 需要手动处理或重启 worker

## 解决方案

### 方案 1：重启 Celery Worker（推荐）

```bash
# 1. 停止旧的 worker（如果还在运行）
pkill -9 -f "celery.*worker"

# 2. 启动新的 worker
cd backend
nohup ./venv/bin/celery -A app.core.celery_app worker --loglevel=info > celery.log 2>&1 &

# 3. 检查 worker 状态
tail -f celery.log
```

**预期结果**:
- Worker 启动成功
- 自动处理队列中的任务
- 任务状态从 `queued` 变为 `running`

### 方案 2：清理队列并重新提交

如果任务已经在队列中太久：

```bash
# 1. 清空 Redis 队列
redis-cli -p 6380 FLUSHDB

# 2. 更新数据库中的任务状态为 failed
# 使用 SQL 或 Python 脚本
```

```python
# backend/cleanup_stuck_tasks.py
import asyncio
from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.models.ai_task import AITask
from datetime import datetime, timedelta

async def cleanup():
    async with AsyncSessionLocal() as db:
        # 查找超过 1 小时还在 queued 的任务
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        result = await db.execute(
            update(AITask)
            .where(
                AITask.status == "queued",
                AITask.created_at < one_hour_ago
            )
            .values(
                status="failed",
                error_message='{"code": "TIMEOUT", "message": "任务超时：Celery worker 未响应"}'
            )
        )
        
        await db.commit()
        print(f"已清理 {result.rowcount} 个超时任务")

asyncio.run(cleanup())
```

### 方案 3：使用完整的启动脚本

```bash
# 使用项目的启动脚本
./stop-dev.sh   # 停止所有服务
./start-dev.sh  # 启动所有服务
```

## 任务执行时间估算

### 影响因素

1. **章节数量**: 更多章节 = 更长时间
2. **技能数量**: 更多技能 = 更长时间
3. **模型速度**: 不同模型响应速度不同
4. **网络延迟**: API 调用延迟

### 典型时间

| 场景 | 章节数 | 技能数 | 预计时间 |
|------|--------|--------|----------|
| 小批次 | 1-5 | 3-5 | 2-5 分钟 |
| 中批次 | 5-10 | 3-5 | 5-15 分钟 |
| 大批次 | 10-20 | 3-5 | 15-30 分钟 |

### 超时设置

当前配置：
- **任务超时**: 120 秒（2 分钟）per API call
- **重试次数**: 3 次
- **总超时**: 无硬性限制

## 监控任务状态

### 方法 1：通过 API

```bash
curl -X GET "http://localhost:8000/api/v1/breakdown/tasks/{task_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 方法 2：查看数据库

```python
# backend/check_task_status.py
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.ai_task import AITask

async def check_task(task_id):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AITask).where(AITask.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if task:
            print(f"状态: {task.status}")
            print(f"进度: {task.progress}%")
            print(f"当前步骤: {task.current_step}")
            print(f"重试次数: {task.retry_count}")

asyncio.run(check_task("your-task-id"))
```

### 方法 3：查看 Celery 日志

```bash
tail -f backend/celery.log
```

## 常见问题

### Q1: 任务一直在 queued，怎么办？

**A**: 检查 Celery worker 是否运行：
```bash
ps aux | grep "celery.*worker"
```

如果没有输出，说明 worker 未运行，需要启动。

### Q2: 任务执行很慢，正常吗？

**A**: 取决于：
- 章节数量和长度
- 选择的技能数量
- AI 模型响应速度

如果超过 30 分钟，可能有问题。

### Q3: 如何取消正在执行的任务？

**A**: 当前不支持取消，但可以：
1. 停止 Celery worker
2. 清理 Redis 队列
3. 更新数据库状态

### Q4: 任务失败后会自动重试吗？

**A**: 是的，对于可重试的错误（网络错误、超时等），会自动重试最多 3 次。

### Q5: 如何查看任务失败原因？

**A**: 通过 API 获取任务状态，查看 `error_display` 字段：
```json
{
  "error_display": {
    "title": "系统配置问题",
    "description": "后台任务执行环境配置异常",
    "suggestion": "请联系技术支持或稍后重试",
    "icon": "⚙️"
  }
}
```

## 最佳实践

### 1. 定期检查 Worker 状态

```bash
# 添加到 crontab
*/5 * * * * pgrep -f "celery.*worker" || /path/to/start-celery.sh
```

### 2. 设置任务超时告警

监控超过 30 分钟还在 running 的任务。

### 3. 定期清理失败任务

清理超过 7 天的失败任务记录。

### 4. 使用批量操作

一次提交多个批次，而不是逐个提交。

## 总结

**当前状态**:
- ❌ Celery worker 已停止
- ❌ 任务无法被处理
- ⏳ 任务会一直保持 `queued` 状态

**解决方法**:
1. 重启 Celery worker
2. 任务会自动开始处理
3. 正常情况下 2-30 分钟完成

**下一步**:
```bash
cd backend
pkill -9 -f "celery.*worker"
nohup ./venv/bin/celery -A app.core.celery_app worker --loglevel=info > celery.log 2>&1 &
```

---

**创建时间**: 2026-02-10
**作者**: AI Assistant

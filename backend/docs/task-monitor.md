# 任务监控和自动终止机制

## 概述

为了防止任务长时间卡住占用系统资源，系统实现了自动任务监控和终止机制。

## 功能特性

### 1. 自动监控（Celery Beat）

系统每 5 分钟自动检查一次卡住的任务，并自动终止。

**检查条件：**
- 任务状态为 `running`、`processing` 或 `queued`
- **超时条件**：创建时间超过 1 小时（3600 秒）
- **停滞条件**：更新时间超过 30 分钟（1800 秒）

**终止操作：**
1. 更新任务状态为 `failed`
2. 设置错误信息为"系统自动终止: [原因]"
3. 更新关联批次状态为 `failed`
4. 发送 Celery 终止信号
5. 发布 Redis 通知

### 2. 手动触发

#### 方式 1：命令行脚本

```bash
cd backend
python scripts/check_stuck_tasks.py
```

#### 方式 2：API 接口

```bash
POST /api/v1/admin/tasks/check-stuck
Authorization: Bearer <admin_token>
```

响应：
```json
{
  "success": true,
  "message": "任务检查完成，已终止卡住的任务"
}
```

## 配置参数

在 `backend/app/tasks/task_monitor.py` 中可以调整：

```python
# 任务超时阈值（秒）
TASK_TIMEOUT_THRESHOLD = 3600  # 1小时
TASK_STALE_THRESHOLD = 1800    # 30分钟无更新视为停滞
```

## 启动 Celery Beat

要启用自动监控，需要启动 Celery Beat：

```bash
# 启动 Celery Worker
celery -A app.core.celery_app worker --loglevel=info

# 启动 Celery Beat（定时任务调度器）
celery -A app.core.celery_app beat --loglevel=info
```

或者使用 Docker Compose：

```yaml
services:
  celery-worker:
    command: celery -A app.core.celery_app worker --loglevel=info

  celery-beat:
    command: celery -A app.core.celery_app beat --loglevel=info
```

## 日志

监控日志会输出到标准日志：

```
[WARNING] 发现 2 个卡住的任务，准备终止
[WARNING] 终止卡住的任务: task_id=xxx, status=running, progress=20, running_time=65min, idle_time=35min, reason=任务停滞无响应（停滞时间: 35 分钟）
[INFO] 更新批次 xxx 状态为 failed
[INFO] 已发送 Celery 终止信号: celery_task_id=xxx
[INFO] 成功终止 2 个卡住的任务
```

## 注意事项

1. **Celery Beat 必须运行**：自动监控依赖 Celery Beat，确保它在生产环境中运行
2. **时区设置**：确保数据库和应用时区一致（UTC）
3. **阈值调整**：根据实际业务需求调整超时阈值
4. **监控频率**：默认 5 分钟检查一次，可在 `celery_app.py` 中调整

## 故障排查

### 问题：自动监控不工作

**检查清单：**
1. Celery Beat 是否运行？
   ```bash
   ps aux | grep "celery.*beat"
   ```

2. 检查 Celery Beat 日志：
   ```bash
   celery -A app.core.celery_app inspect scheduled
   ```

3. 检查定时任务配置：
   ```python
   from app.core.celery_app import celery_app
   print(celery_app.conf.beat_schedule)
   ```

### 问题：任务被误终止

如果任务正常运行但被误终止，可能需要：
1. 增加 `TASK_TIMEOUT_THRESHOLD` 阈值
2. 确保任务定期更新 `updated_at` 字段
3. 检查任务进度更新逻辑

## 相关文件

- `backend/app/tasks/task_monitor.py` - 监控逻辑
- `backend/app/core/celery_app.py` - Celery 配置
- `backend/scripts/check_stuck_tasks.py` - 手动检查脚本
- `backend/app/api/v1/admin_core.py` - 管理 API

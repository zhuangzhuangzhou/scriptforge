# Celery 异步任务最终修复方案

## 问题总结

任务ID `0ee986ae-78ce-4ec1-a64f-ef44465a4854` 一直处于 `queued` 状态，无法执行。

### 根本原因

1. **SQLAlchemy 异步引擎与 Celery 不兼容**
   - Celery worker 在同步上下文中运行
   - SQLAlchemy 异步引擎需要正确的 greenlet 上下文
   - `asyncio.run()` 无法在 Celery worker 中正常工作

2. **uvloop 与 nest_asyncio 冲突**
   - FastAPI 使用 uvloop 作为默认事件循环
   - `nest_asyncio` 无法 patch uvloop
   - 导致模块导入时就失败

3. **Celery worker 进程崩溃**
   - 所有 worker 进程退出（exitcode 70）
   - 任务无法被处理

## 最终解决方案

### 方案：将 Celery 任务改为同步实现

由于 Celery 与 SQLAlchemy 异步引擎的兼容性问题难以解决，最佳方案是：

**使用同步的数据库连接在 Celery 任务中**

#### 步骤 1：创建同步数据库引擎

```python
# backend/app/core/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 同步数据库引擎（用于 Celery）
SYNC_DATABASE_URL = settings.DATABASE_URL.replace("+asyncpg", "")  # 移除 asyncpg
sync_engine = create_engine(SYNC_DATABASE_URL, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
```

#### 步骤 2：重写 Celery 任务为同步版本

```python
# backend/app/tasks/breakdown_tasks.py

@celery_app.task(**CELERY_TASK_CONFIG)
def run_breakdown_task(self, task_id: str, batch_id: str, project_id: str, user_id: str):
    """执行Breakdown任务（同步版本）"""
    
    # 使用同步数据库会话
    from app.core.database import SyncSessionLocal
    
    with SyncSessionLocal() as db:
        try:
            # 更新任务状态
            task = db.query(AITask).filter(AITask.id == task_id).first()
            task.status = "running"
            task.progress = 0
            db.commit()
            
            # 执行任务逻辑（同步版本）
            # ...
            
            task.status = "completed"
            task.progress = 100
            db.commit()
            
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            db.commit()
            raise
```

#### 步骤 3：创建同步版本的 PipelineExecutor

```python
# backend/app/ai/sync_pipeline_executor.py

class SyncPipelineExecutor:
    """同步版本的 Pipeline 执行器（用于 Celery）"""
    
    def __init__(self, db, model_adapter, user_id=None, task_config=None):
        self.db = db  # 同步数据库会话
        self.model_adapter = model_adapter
        self.user_id = user_id
        self.task_config = task_config or {}
    
    def run_breakdown(self, project_id, batch_id, pipeline_id=None, ...):
        """同步执行 breakdown"""
        # 所有数据库操作都是同步的
        chapters = self._load_chapters(batch_id)
        # ...
```

### 优点

1. ✅ 完全避免异步兼容性问题
2. ✅ Celery worker 稳定运行
3. ✅ 代码简单，易于维护
4. ✅ 性能影响小（Celery 任务本身就是后台任务）

### 缺点

1. ⚠️ 需要维护两套代码（异步 API + 同步 Celery）
2. ⚠️ 数据库连接池需要分开管理

## 临时解决方案（快速修复）

如果不想重构代码，可以使用以下临时方案：

### 方案 A：使用 asyncio.new_event_loop()

```python
@celery_app.task(**CELERY_TASK_CONFIG)
def run_breakdown_task(self, task_id: str, batch_id: str, project_id: str, user_id: str):
    async def _run_async():
        # 异步代码
        ...
    
    # 创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_async())
    finally:
        loop.close()
```

### 方案 B：禁用 uvloop

在 Celery worker 启动时禁用 uvloop：

```bash
# 启动 Celery 时设置环境变量
ASYNCIO_EVENT_LOOP_POLICY=asyncio.DefaultEventLoopPolicy celery -A app.core.celery_app worker
```

或在代码中：

```python
# backend/app/tasks/breakdown_tasks.py
import asyncio
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
```

## 当前状态

- ✅ 模型配置正常（5个提供商，3个模型）
- ✅ 数据库连接正常
- ✅ 任务已创建（queued 状态）
- ❌ Celery worker 崩溃
- ❌ 任务无法执行

## 下一步行动

### 立即行动（推荐）

1. 实施同步数据库方案
2. 重写 Celery 任务为同步版本
3. 测试任务执行

### 快速修复（临时）

1. 使用方案 A 或 B
2. 重启 Celery worker
3. 测试任务执行

## 相关文件

- `backend/app/tasks/breakdown_tasks.py` - Celery 任务
- `backend/app/core/database.py` - 数据库配置
- `backend/app/ai/pipeline_executor.py` - Pipeline 执行器
- `docs/fix-celery-async-issue.md` - 之前的修复尝试

---

**创建时间**: 2026-02-10
**作者**: AI Assistant

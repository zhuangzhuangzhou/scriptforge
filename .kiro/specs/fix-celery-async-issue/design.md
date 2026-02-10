# 修复 Celery 异步任务执行问题 - 设计文档

## 1. 架构概述

### 1.1 当前架构问题

```
FastAPI (异步)
    ↓
AsyncSessionLocal (asyncpg)
    ↓
Celery Task (同步上下文)
    ↓
asyncio.new_event_loop() ❌
    ↓
AsyncSessionLocal (asyncpg) ❌ greenlet 错误
```

### 1.2 新架构设计

```
FastAPI (异步)                    Celery Task (同步)
    ↓                                  ↓
AsyncSessionLocal (asyncpg)       SyncSessionLocal (psycopg2)
    ↓                                  ↓
异步数据库操作                      同步数据库操作
```

**关键设计决策**:
- 维护两套独立的数据库会话
- FastAPI 继续使用异步
- Celery 任务使用同步
- 共享相同的数据库模型定义

## 2. 组件设计

### 2.1 同步数据库引擎

**文件**: `backend/app/core/database.py`

```python
# 现有的异步引擎（保持不变）
async_engine = create_async_engine(
    settings.DATABASE_URL,
    ...
)
AsyncSessionLocal = async_sessionmaker(...)

# 新增：同步引擎（用于 Celery）
SYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://",
    "postgresql+psycopg2://"
)

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False
)

SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)
```

**设计要点**:
- 使用 `psycopg2` 驱动（同步）
- 独立的连接池配置
- 与异步引擎共存

### 2.2 同步任务进度更新

**文件**: `backend/app/core/progress.py`

```python
# 现有的异步版本（保持不变）
async def update_task_progress(...):
    ...

# 新增：同步版本
def update_task_progress_sync(
    db: Session,  # 同步会话
    task_id: str,
    status: str = None,
    progress: int = None,
    current_step: str = None,
    error_message: str = None
):
    """同步更新任务进度（用于 Celery）"""
    task = db.query(AITask).filter(AITask.id == task_id).first()
    
    if not task:
        return
    
    if status is not None:
        task.status = status
    if progress is not None:
        task.progress = progress
    if current_step is not None:
        task.current_step = current_step
    if error_message is not None:
        task.error_message = error_message
    
    if status == "running" and not task.started_at:
        task.started_at = datetime.utcnow()
    elif status in ["completed", "failed"]:
        task.completed_at = datetime.utcnow()
    
    db.commit()
```

### 2.3 同步模型适配器获取

**文件**: `backend/app/ai/adapters/__init__.py`

```python
# 现有的异步版本（保持不变）
async def get_adapter(...):
    ...

# 新增：同步版本
def get_adapter_sync(
    db: Session,  # 同步会话
    model_id: str = None,
    user_id: str = None
) -> BaseAdapter:
    """同步获取模型适配器（用于 Celery）"""
    # 查询模型配置
    if model_id:
        model = db.query(AIModel).filter(
            AIModel.id == model_id,
            AIModel.is_enabled == True
        ).first()
    else:
        # 获取默认模型
        model = db.query(AIModel).filter(
            AIModel.is_enabled == True
        ).first()
    
    if not model:
        raise ValueError("No available model found")
    
    # 获取提供商
    provider = db.query(AIModelProvider).filter(
        AIModelProvider.id == model.provider_id,
        AIModelProvider.is_enabled == True
    ).first()
    
    if not provider:
        raise ValueError(f"Provider {model.provider_id} not found or disabled")
    
    # 获取凭证
    credential = db.query(AICredential).filter(
        AICredential.provider_id == provider.id,
        AICredential.is_active == True
    ).first()
    
    if not credential:
        raise ValueError(f"No active credential for provider {provider.name}")
    
    # 创建适配器
    adapter_class = ADAPTER_REGISTRY.get(provider.provider_type)
    if not adapter_class:
        raise ValueError(f"Unknown provider type: {provider.provider_type}")
    
    return adapter_class(
        api_key=credential.api_key,
        model_name=model.model_name,
        **credential.config
    )
```

### 2.4 重写 Celery 任务

**文件**: `backend/app/tasks/breakdown_tasks.py`

```python
from app.core.database import SyncSessionLocal
from app.core.progress import update_task_progress_sync
from app.ai.adapters import get_adapter_sync

@celery_app.task(**CELERY_TASK_CONFIG)
def run_breakdown_task(self, task_id: str, batch_id: str, project_id: str, user_id: str):
    """执行Breakdown任务（同步版本）"""
    
    # 使用同步数据库会话
    db = SyncSessionLocal()
    
    try:
        # 更新任务状态为 running
        update_task_progress_sync(
            db, task_id,
            status="running",
            progress=0,
            current_step="初始化任务"
        )
        
        # 更新批次状态
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if batch:
            batch.breakdown_status = "processing"
            db.commit()
        
        # 读取任务配置
        task = db.query(AITask).filter(AITask.id == task_id).first()
        task_config = task.config if task else {}
        
        # 获取模型适配器（同步）
        model_id = task_config.get("model_id")
        model_adapter = get_adapter_sync(
            db=db,
            model_id=model_id,
            user_id=user_id
        )
        
        # 定义进度回调
        def progress_callback(step: str, progress: int):
            update_task_progress_sync(
                db, task_id,
                progress=progress,
                current_step=step
            )
        
        # 执行拆解逻辑
        progress_callback("加载章节", 10)
        
        # 使用同步版本的 Pipeline 执行器
        executor = SyncPipelineExecutor(
            db=db,
            model_adapter=model_adapter,
            user_id=user_id,
            task_config=task_config
        )
        
        executor.run_breakdown(
            project_id=project_id,
            batch_id=batch_id,
            pipeline_id=task_config.get("pipeline_id"),
            selected_skills=task_config.get("selected_skills"),
            progress_callback=progress_callback
        )
        
        # 任务完成
        update_task_progress_sync(
            db, task_id,
            status="completed",
            progress=100,
            current_step="任务完成"
        )
        
        if batch:
            batch.breakdown_status = "completed"
            db.commit()
        
        # 扣费
        credits_service = SyncCreditsService(db)
        credits_service.consume_credits(
            user_id=user_id,
            amount=BREAKDOWN_BASE_CREDITS,
            description=f"剧情拆解 - 批次 {batch_id}",
            reference_id=task_id
        )
        db.commit()
        
        return {"status": "completed", "task_id": task_id}
        
    except RetryableError as e:
        _handle_retryable_error_sync(db, task_id, batch, task, e)
        raise
        
    except QuotaExceededError as e:
        _handle_quota_exceeded_sync(db, task_id, batch, task, user_id, e)
        raise
        
    except Exception as e:
        classified_error = classify_exception(e)
        if isinstance(classified_error, RetryableError):
            _handle_retryable_error_sync(db, task_id, batch, task, classified_error)
            raise
        else:
            _handle_task_failure_sync(db, task_id, batch, task, user_id, classified_error)
            raise
            
    finally:
        db.close()
```

### 2.5 同步 Pipeline 执行器

**文件**: `backend/app/ai/sync_pipeline_executor.py`

```python
class SyncPipelineExecutor:
    """同步版本的 Pipeline 执行器（用于 Celery）"""
    
    def __init__(self, db, model_adapter, user_id=None, task_config=None):
        self.db = db  # 同步数据库会话
        self.model_adapter = model_adapter
        self.user_id = user_id
        self.task_config = task_config or {}
    
    def run_breakdown(
        self,
        project_id: str,
        batch_id: str,
        pipeline_id: str = None,
        selected_skills: list = None,
        progress_callback=None
    ):
        """同步执行 breakdown"""
        
        # 加载章节（同步）
        chapters = self._load_chapters(batch_id)
        
        if progress_callback:
            progress_callback("处理章节", 30)
        
        # 加载技能（同步）
        skills = self._load_skills(selected_skills)
        
        if progress_callback:
            progress_callback("执行拆解", 50)
        
        # 执行拆解（同步调用 AI）
        results = []
        for i, chapter in enumerate(chapters):
            result = self._process_chapter(chapter, skills)
            results.append(result)
            
            # 更新进度
            progress = 50 + int((i + 1) / len(chapters) * 40)
            if progress_callback:
                progress_callback(f"处理章节 {i+1}/{len(chapters)}", progress)
        
        # 保存结果（同步）
        self._save_results(batch_id, results)
        
        if progress_callback:
            progress_callback("保存结果", 95)
    
    def _load_chapters(self, batch_id: str):
        """加载章节（同步）"""
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        chapters = self.db.query(Chapter).filter(
            Chapter.project_id == batch.project_id,
            Chapter.chapter_number >= batch.start_chapter,
            Chapter.chapter_number <= batch.end_chapter
        ).order_by(Chapter.chapter_number).all()
        
        return chapters
    
    def _load_skills(self, selected_skills: list):
        """加载技能（同步）"""
        if not selected_skills:
            return []
        
        skills = self.db.query(Skill).filter(
            Skill.id.in_(selected_skills)
        ).all()
        
        return skills
    
    def _process_chapter(self, chapter, skills):
        """处理单个章节（同步调用 AI）"""
        # 构建提示词
        prompt = self._build_prompt(chapter, skills)
        
        # 调用 AI（同步）
        # 注意：model_adapter 的方法可能是异步的，需要处理
        response = self._call_ai_sync(prompt)
        
        return {
            "chapter_id": chapter.id,
            "result": response
        }
    
    def _call_ai_sync(self, prompt: str):
        """同步调用 AI（处理异步适配器）"""
        # 如果适配器是异步的，需要在这里处理
        # 方案 1: 使用 asyncio.run()
        # 方案 2: 创建同步版本的适配器
        
        # 这里假设我们创建了同步版本的适配器
        return self.model_adapter.generate(prompt)
    
    def _save_results(self, batch_id: str, results: list):
        """保存结果（同步）"""
        for result in results:
            # 保存到数据库
            breakdown = BreakdownResult(
                batch_id=batch_id,
                chapter_id=result["chapter_id"],
                result=result["result"]
            )
            self.db.add(breakdown)
        
        self.db.commit()
```

## 3. 数据流设计

### 3.1 任务提交流程（异步）

```
用户请求 → FastAPI 端点 (异步)
    ↓
AsyncSessionLocal
    ↓
创建 AITask 记录 (status="queued")
    ↓
提交到 Celery: run_breakdown_task.delay()
    ↓
返回任务 ID 给用户
```

### 3.2 任务执行流程（同步）

```
Celery Worker 接收任务
    ↓
run_breakdown_task (同步函数)
    ↓
SyncSessionLocal
    ↓
更新任务状态 (status="running")
    ↓
获取模型适配器 (同步)
    ↓
执行 Pipeline (同步)
    ↓
更新任务状态 (status="completed")
    ↓
扣费
```

### 3.3 任务查询流程（异步）

```
用户请求 → FastAPI 端点 (异步)
    ↓
AsyncSessionLocal
    ↓
查询 AITask 记录
    ↓
返回任务状态给用户
```

## 4. 错误处理设计

### 4.1 可重试错误

```python
def _handle_retryable_error_sync(db, task_id, batch, task, error):
    """处理可重试错误（同步）"""
    error_info = {
        "code": error.code,
        "message": error.message,
        "retry_count": task.retry_count if task else 0,
        "retrying_at": datetime.utcnow().isoformat()
    }
    
    update_task_progress_sync(
        db, task_id,
        status="retrying",
        error_message=json.dumps(error_info)
    )
    
    if batch:
        batch.breakdown_status = "pending"
        db.commit()
```

### 4.2 配额不足错误

```python
def _handle_quota_exceeded_sync(db, task_id, batch, task, user_id, error):
    """处理配额不足错误（同步）"""
    # 回滚配额
    _refund_quota_sync(db, user_id)
    
    # 更新任务状态
    error_info = error.to_dict()
    error_info["failed_at"] = datetime.utcnow().isoformat()
    
    update_task_progress_sync(
        db, task_id,
        status="failed",
        error_message=json.dumps(error_info)
    )
    
    if batch:
        batch.breakdown_status = "failed"
        db.commit()
```

### 4.3 任务失败错误

```python
def _handle_task_failure_sync(db, task_id, batch, task, user_id, error):
    """处理任务失败（同步）"""
    # 回滚配额
    _refund_quota_sync(db, user_id)
    
    # 更新任务状态
    error_info = error.to_dict()
    error_info["failed_at"] = datetime.utcnow().isoformat()
    error_info["retry_count"] = task.retry_count if task else 0
    
    update_task_progress_sync(
        db, task_id,
        status="failed",
        error_message=json.dumps(error_info)
    )
    
    if batch:
        batch.breakdown_status = "failed"
        db.commit()
```

## 5. 配置管理

### 5.1 数据库 URL 配置

**文件**: `backend/app/core/config.py`

```python
class Settings(BaseSettings):
    # 现有配置
    DATABASE_URL: str
    
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """同步数据库 URL（用于 Celery）"""
        return self.DATABASE_URL.replace(
            "postgresql+asyncpg://",
            "postgresql+psycopg2://"
        )
```

### 5.2 连接池配置

```python
# 异步引擎配置
ASYNC_POOL_SIZE = 20
ASYNC_MAX_OVERFLOW = 40

# 同步引擎配置（Celery）
SYNC_POOL_SIZE = 5
SYNC_MAX_OVERFLOW = 10
```

## 6. 测试策略

### 6.1 单元测试

```python
def test_sync_database_connection():
    """测试同步数据库连接"""
    db = SyncSessionLocal()
    try:
        user = db.query(User).first()
        assert user is not None
    finally:
        db.close()

def test_update_task_progress_sync():
    """测试同步更新任务进度"""
    db = SyncSessionLocal()
    try:
        task_id = "test-task-id"
        update_task_progress_sync(
            db, task_id,
            status="running",
            progress=50
        )
        
        task = db.query(AITask).filter(AITask.id == task_id).first()
        assert task.status == "running"
        assert task.progress == 50
    finally:
        db.close()
```

### 6.2 集成测试

```python
def test_celery_task_execution():
    """测试 Celery 任务执行"""
    # 创建测试任务
    task_id = create_test_task()
    
    # 提交到 Celery
    celery_task = run_breakdown_task.delay(
        task_id=task_id,
        batch_id="test-batch",
        project_id="test-project",
        user_id="test-user"
    )
    
    # 等待任务完成
    result = celery_task.get(timeout=60)
    
    # 验证结果
    assert result["status"] == "completed"
    
    # 验证数据库状态
    db = SyncSessionLocal()
    try:
        task = db.query(AITask).filter(AITask.id == task_id).first()
        assert task.status == "completed"
        assert task.progress == 100
    finally:
        db.close()
```

## 7. 部署计划

### 7.1 准备阶段
1. 安装 `psycopg2-binary`
2. 创建同步数据库引擎
3. 编写同步辅助函数

### 7.2 实施阶段
1. 重写 `run_breakdown_task`
2. 创建 `SyncPipelineExecutor`
3. 更新导入和配置

### 7.3 测试阶段
1. 单元测试
2. 集成测试
3. 手动测试

### 7.4 上线阶段
1. 停止 Celery worker
2. 部署新代码
3. 启动 Celery worker
4. 监控任务执行

## 8. 监控和日志

### 8.1 日志记录

```python
import logging

logger = logging.getLogger(__name__)

@celery_app.task(**CELERY_TASK_CONFIG)
def run_breakdown_task(self, task_id: str, ...):
    logger.info(f"开始执行任务: {task_id}")
    
    try:
        # 任务逻辑
        logger.info(f"任务 {task_id} 执行成功")
    except Exception as e:
        logger.error(f"任务 {task_id} 执行失败: {e}", exc_info=True)
        raise
```

### 8.2 性能监控

```python
import time

@celery_app.task(**CELERY_TASK_CONFIG)
def run_breakdown_task(self, task_id: str, ...):
    start_time = time.time()
    
    try:
        # 任务逻辑
        pass
    finally:
        duration = time.time() - start_time
        logger.info(f"任务 {task_id} 执行时间: {duration:.2f}秒")
```

## 9. 未来优化

### 9.1 短期优化
- 优化数据库查询性能
- 添加更多的错误处理
- 改进日志记录

### 9.2 长期优化
- 考虑统一为同步或异步
- 实现任务优先级
- 添加任务取消功能

## 10. 参考文档

- SQLAlchemy 同步文档
- Celery 最佳实践
- PostgreSQL 连接池配置

---

**创建时间**: 2026-02-10
**版本**: 1.0
**状态**: 设计中

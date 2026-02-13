# Breakdown Start 接口流程详解

本文档详细描述 `/breakdown/start` 接口从请求到完成的完整执行流程。

## 接口概览

| 项目 | 说明 |
|------|------|
| **端点** | `POST /api/v1/breakdown/start` |
| **认证** | 需要 Bearer Token |
| **请求体** | `BreakdownStartRequest` |

## 整体流程图

```
┌─────────────────────────────────────────────────────────────┐
│                      前端调用 /breakdown/start               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  API 层 (FastAPI)                                            │
│  - 验证权限、积分、配置                                      │
│  - 创建 AITask 记录                                         │
│  - 触发 Celery 任务                                          │
│  - 立即返回 task_id                                          │
└─────────────────────────┬───────────────────────────────────┘
                          │ Celery Queue (Redis)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Worker 进程                                                 │
│  - 接收任务                                                  │
│  - 加载章节 + 资源                                           │
│  - 调用 LLM 执行拆解                                        │
│  - 保存 PlotBreakdown                                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  前端轮询 /breakdown/tasks/{task_id} 获取状态               │
│  或 WebSocket 实时推送                                       │
└─────────────────────────────────────────────────────────────┘
```

## 1. API 层详细流程

**文件**: `backend/app/api/v1/breakdown.py:68-235`

### 1.1 请求验证

```python
# 1. 验证批次归属
result = await db.execute(
    select(Batch).join(Project).where(
        Batch.id == request.batch_id,
        Project.user_id == current_user.id
    )
)
batch = result.scalar_one_or_none()

# 2. 获取项目配置
project_result = await db.execute(
    select(Project).where(Project.id == batch.project_id)
)
project = project_result.scalar_one_or_none()

# 3. 检查拆解模型配置
if not project.breakdown_model_id:
    raise HTTPException(
        status_code=400,
        detail="项目未配置剧情拆解模型，请先在项目设置中选择模型"
    )
```

### 1.2 防重复提交检查

```python
# 检查是否已有任务在执行
existing_task_result = await db.execute(
    select(AITask).where(
        AITask.batch_id == request.batch_id,
        AITask.status.in_(["queued", "running"])
    )
)
existing_task = existing_task_result.scalar_one_or_none()

if existing_task:
    raise HTTPException(
        status_code=409,
        detail=f"该批次已有任务在执行中，任务ID: {existing_task.id}"
    )
```

### 1.3 积分检查与预扣

```python
# 锁定用户记录（防止并发超支）
user_result = await db.execute(
    select(User).where(User.id == current_user.id).with_for_update()
)
locked_user = user_result.scalar_one()

# 检查积分
quota_service = QuotaService(db)
credits_check = await quota_service.check_credits(locked_user, "breakdown")
if not credits_check["allowed"]:
    raise HTTPException(
        status_code=403,
        detail=f"积分不足: 需要 {credits_check['cost']}，余额 {credits_check['balance']}"
    )

# 预扣积分
await quota_service.consume_credits(locked_user, "breakdown", "剧情拆解")
```

### 1.4 任务创建与 Celery 触发

```python
# 构建任务配置
task_config = {
    "model_config_id": str(project.breakdown_model_id),
    "selected_skills": request.selected_skills or [],
    "pipeline_id": request.pipeline_id,
    "novel_type": request.novel_type or project.novel_type,
    "resource_ids": request.resource_ids or [],
}

# 创建 AITask 记录
task = AITask(
    project_id=batch.project_id,
    batch_id=batch.id,
    task_type="breakdown",
    status="queued",
    depends_on=[],
    config=task_config
)
db.add(task)
await db.flush()

# 触发 Celery 异步任务
celery_task = run_breakdown_task.delay(
    str(task.id),
    str(batch.id),
    str(batch.project_id),
    str(current_user.id)
)
task.celery_task_id = celery_task.id

# 更新批次状态
batch.breakdown_status = "queued"

# 提交事务
await db.commit()

# 返回结果
return {"task_id": str(task.id), "status": "queued"}
```

### 1.5 API 层返回

```json
{
  "task_id": "uuid-string",
  "status": "queued"
}
```

## 2. Celery Worker 执行流程

**文件**: `backend/app/tasks/breakdown_tasks.py:44-167`

### 2.1 任务接收与初始化

```python
@celery_app.task(**CELERY_TASK_CONFIG)
def run_breakdown_task(self, task_id, batch_id, project_id, user_id):
    """
    Celery 任务配置:
    - bind: True (绑定 self 参数)
    - autoretry_for: (RetryableError, TimeoutError, ConnectionError)
    - retry_kwargs: {max_retries: 3, countdown: 60}
    - retry_backoff: True
    """
    db = SyncSessionLocal()
    log_publisher = None

    try:
        # 初始化 Redis 日志发布器
        from app.core.redis_log_publisher import RedisLogPublisher
        log_publisher = RedisLogPublisher()

        # 更新任务状态：queued → running
        update_task_progress_sync(
            db, task_id,
            status="running",
            progress=0,
            current_step="初始化任务中... (0%)"
        )

        # 更新批次状态：queued → processing
        batch_record = db.query(Batch).filter(Batch.id == batch_id).first()
        if batch_record:
            batch_record.breakdown_status = "processing"
            db.commit()
```

### 2.2 模型适配器获取

```python
# 读取任务配置
task_record = db.query(AITask).filter(AITask.id == task_id).first()
task_config = task_record.config or {}

# 获取模型配置 ID
model_id = task_config.get("model_config_id")
if not model_id:
    raise ValueError("任务配置中缺少 model_config_id")

# 获取模型适配器
from app.ai.adapters import get_adapter_sync
model_adapter = get_adapter_sync(
    db=db,
    model_id=model_id,
    user_id=user_id
)
```

## 3. 拆解执行逻辑详解

**文件**: `backend/app/tasks/breakdown_tasks.py:288-477`

### 3.1 加载章节数据 (5%-10%)

```python
# 1. 加载章节数据
update_task_progress_sync(db, task_id, progress=5, current_step="加载章节数据中... (5%)")

batch = db.query(Batch).filter(Batch.id == batch_id).first()
chapters = db.query(Chapter).filter(
    Chapter.batch_id == batch_id
).order_by(Chapter.chapter_number).all()

chapters_text = _format_chapters_sync(chapters)
update_task_progress_sync(db, task_id, progress=10, current_step="章节数据加载完成 (10%)")
```

### 3.2 加载 AI 资源文档 (12%-15%)

```python
# 2. 加载 AI 资源文档
update_task_progress_sync(db, task_id, progress=12, current_step="加载 AI 资源文档中... (12%)")

novel_type = task_config.get("novel_type")
resource_ids = task_config.get("resource_ids", [])

# 优先使用 resource_ids 加载资源
if resource_ids:
    grouped_resources = _load_resources_by_ids_sync(db, resource_ids)
else:
    # 回退到分层资源加载
    layered_resources = load_layered_resources_sync(db, stage="breakdown", novel_type=novel_type)

update_task_progress_sync(db, task_id, progress=15, current_step="AI 资源文档加载完成 (15%)")
```

### 3.3 执行拆解 (20%-90%)

```python
# 3. 执行拆解
update_task_progress_sync(db, task_id, progress=20, current_step="执行剧情拆解中... (20%)")

# 构建 Agent 上下文
agent_context = {
    "chapters_text": chapters_text,
    "adapt_method": adapt_method or "",
    "output_style": output_style or "",
    "template": template or "",
    "example": example or "",
    "start_chapter": str(batch.start_chapter),
    "end_chapter": str(batch.end_chapter),
}

# 优先使用 Agent 模式
try:
    agent_executor = SimpleAgentExecutor(db, model_adapter, log_publisher)
    results = agent_executor.execute_agent(
        agent_name="breakdown_agent",
        context=agent_context,
        task_id=task_id
    )
    plot_points = results.get("plot_points", [])
    qa_status = results.get("qa_result", {}).get("status", "pending")
except Exception as e:
    # 回退到 Skill 模式
    skill_executor = SimpleSkillExecutor(db, model_adapter, log_publisher)
    plot_points = skill_executor.execute_skill(
        skill_name="webtoon_breakdown",
        inputs=agent_context,
        task_id=task_id
    )

update_task_progress_sync(db, task_id, progress=90, current_step=f"拆解完成，生成 {len(plot_points)} 个剧情点 (90%)")
```

### 3.4 保存结果 (90%-100%)

```python
# 4. 保存结果
breakdown = PlotBreakdown(
    batch_id=batch_id,
    project_id=project_id,
    plot_points=plot_points,
    format_version=2,
    qa_status=qa_status.lower() if isinstance(qa_status, str) else "pending",
    used_adapt_method_id=task_config.get("adapt_method_id"),
)
db.add(breakdown)
db.commit()
db.refresh(breakdown)

update_task_progress_sync(db, task_id, progress=100, current_step="任务完成 (100%)")
```

## 4. 任务状态流转

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    queued    │ ──► │   running    │ ──► │  completed   │
│   (排队中)   │     │   (执行中)   │     │   (已完成)   │
└──────────────┘     └──────────────┘     └──────────────┘
                           │
                           ▼
                     ┌──────────────┐
                     │    failed    │
                     │    (失败)    │
                     └──────────────┘
                           │
                           ▼
                     ┌──────────────┐
                     │   retrying   │
                     │   (重试中)   │
                     └──────────────┘
                           │
                           ▼
                     ┌──────────────┐
                     │    queued    │ ──► 重新执行
                     │   (重试队列) │
                     └──────────────┘
```

## 5. 错误处理

### 5.1 可重试错误

以下错误会自动重试最多 3 次：

- `RetryableError` - 网络连接问题
- `TimeoutError` - API 调用超时
- `ConnectionError` - 连接断开

```python
# Celery 配置自动重试
CELERY_TASK_CONFIG = {
    "autoretry_for": (RetryableError, TimeoutError, ConnectionError),
    "retry_kwargs": {
        "max_retries": 3,
        "countdown": 60,  # 基础等待时间（秒）
    },
    "retry_backoff": True,  # 启用指数退避
    "retry_backoff_max": 600,  # 最大等待时间（10分钟）
    "retry_jitter": True,  # 添加随机抖动
}
```

### 5.2 不可重试错误

以下错误会直接标记为失败：

- `AITaskException` - AI 任务执行错误
- `ValueError` - 配置错误（如缺少 model_config_id）
- `QuotaExceededError` - 配额不足

### 5.3 错误处理函数

```python
def _handle_task_failure_sync(db, task_id, batch_record, task_record, error):
    """处理任务失败"""
    error_info = error.to_dict()
    error_info["failed_at"] = datetime.utcnow().isoformat()
    error_info["retry_count"] = task_record.retry_count if task_record else 0

    update_task_progress_sync(
        db, task_id,
        status="failed",
        error_message=json.dumps(error_info)
    )

    if batch_record:
        batch_record.breakdown_status = "failed"
        db.commit()
```

## 6. 进度追踪

### 6.1 进度百分比

| 阶段 | 进度 | 说明 |
|------|------|------|
| 初始化 | 0% | 任务开始 |
| 加载章节 | 5%-10% | 从数据库读取章节数据 |
| 加载资源 | 12%-15% | 加载 AI 资源文档 |
| 执行拆解 | 20%-90% | 调用 LLM 执行拆解 |
| 保存结果 | 90%-100% | 保存拆解结果 |

### 6.2 查询任务状态

```bash
curl -X GET "http://localhost:8000/api/v1/breakdown/tasks/{task_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

响应示例：
```json
{
  "task_id": "uuid-string",
  "status": "running",
  "progress": 45,
  "current_step": "执行剧情拆解中... (45%)",
  "error_message": null,
  "retry_count": 0
}
```

## 7. 积分扣费时机

### 当前实现：预扣模式

1. **API 层**：调用 `/breakdown/start` 时预扣积分
2. **Worker 层**：任务成功或失败都不再处理积分
3. **积分返还**：仅在 API 层失败时通过事务回滚

### 流程

```
API 层                    Worker 层
   │                        │
   ├─► 检查积分 ◄───────────┤
   ├─► 预扣积分              │
   │                        │
   ├─► 创建任务              │
   │                        │
   │         ───────────────┼─► 执行任务
   │                        │
   │                        ├─► 完成/失败
   │                        │
   ◄─┴──────────────────────┘
```

## 8. 相关文件索引

| 文件路径 | 说明 |
|----------|------|
| `backend/app/api/v1/breakdown.py` | API 端点实现 |
| `backend/app/tasks/breakdown_tasks.py` | Celery 任务实现 |
| `backend/app/models/ai_task.py` | AITask 模型 |
| `backend/app/models/plot_breakdown.py` | PlotBreakdown 模型 |
| `backend/app/core/quota.py` | 积分服务 |
| `docs/05-features/ai-workflow/task-lifecycle-explanation.md` | 任务生命周期 |

---

**创建时间**: 2026-02-13
**最后更新**: 2026-02-13

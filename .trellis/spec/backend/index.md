# 后端开发规范

## 1. 技术栈规范 (Tech Stack)

| 核心组件 | 版本 | 选型说明 |
|-----------|-------------|-------------|
| **Web Framework** | **FastAPI** `0.109.0` | 全异步 Python Web 框架 |
| **Language** | **Python** `3.9+` | 强制使用 Type Hints |
| **ORM** | **SQLAlchemy** `2.0.25` | 异步模式 (AsyncSession) |
| **Database** | **PostgreSQL** `15+` | 驱动：`asyncpg` (异步) + `psycopg2` (同步/迁移) |
| **Migration** | **Alembic** `1.13.1` | 数据库版本控制 |
| **Validation** | **Pydantic** `2.5.3` | 数据模型校验与序列化 |
| **AI Framework** | **LangChain** `0.1.0` + **LangGraph** | AI 编排与 Agent 流程 |
| **Task Queue** | **Celery** `5.3.4` + **Redis** | 异步任务与缓存 |

## 2. 代码风格与规范 (Code Standards)

### 2.1 格式化与检查
- **Formatter**: `black` (行宽默认 88 字符)
- **Linter**: `flake8`
- **Typing**: 强制使用类型注解 (`List`, `Dict`, `Optional`, `UUID` 等)。
- **Docstrings**: 类与公共方法必须包含中文文档注释。

### 2.2 命名规范
- **目录/文件**: `snake_case` (e.g., `user_service.py`)
- **类名**: `PascalCase` (e.g., `UserResponse`)
- **变量/函数**: `snake_case` (e.g., `get_user_by_id`)
- **常量**: `UPPER_CASE` (e.g., `DEFAULT_PAGE_SIZE`)

## 3. 核心架构模式 (Architecture Patterns)

### 3.1 目录结构
```text
backend/
├── alembic/              # 数据库迁移脚本
├── app/
│   ├── ai/               # AI 核心逻辑 (Agents, Skills, LangGraph)
│   ├── api/              # API 接口层
│   │   └── v1/           # 路由定义 (RESTful)
│   ├── core/             # 核心配置 (Config, DB Connection, Security)
│   ├── models/           # SQLAlchemy 数据库模型定义
│   ├── schemas/          # Pydantic 数据传输模型 (DTO)
│   ├── tasks/            # Celery 异步任务定义
│   └── utils/            # 通用工具函数
├── requirements.txt      # 依赖清单
└── main.py               # 应用入口
```

### 3.2 数据库模式 (Database Pattern)
- **异步优先**: 所有业务逻辑默认使用 `AsyncSession`。
- **连接管理**:
    - `core/database.py` 提供 `get_db` 依赖。
    - 使用 `Depends(get_db)` 注入 API 控制器。
- **模型规范**:
    - 所有模型继承自 `Base`。
    - 主键使用 `UUID` 类型。
    - 必须包含 `created_at` 和 `updated_at` (带时区)。

### 3.3 配置管理 (Configuration)
- **实现**: 基于 `pydantic-settings` 的 `Settings` 类。
- **来源**: 优先读取环境变量 (`.env`)，提供默认回退值。
- **访问**: 通过 `app.core.config.settings` 单例访问。
- **共享**: 建议提供 `/api/v1/config` 或 `/quota` 端点，将非敏感的业务规则（如会员配额）共享给前端。

## 4. API 开发指南

### 4.1 路由定义
- 使用 `APIRouter` 分模块组织路由。
- 在 `app/api/v1/router.py` 中统一注册。
- URL 路径使用连字符格式 (e.g., `/users/me/change-password`)。
- **类型同步**: 确保 API 定义能正确生成 OpenAPI Schema，以便前端通过工具自动生成 TypeScript 类型定义。
- **路由顺序**: 具体路由必须在参数路由之前定义 (详见 8.11)

### 4.2 依赖注入
- 获取当前用户: `current_user: User = Depends(get_current_active_user)`
- 获取数据库: `db: AsyncSession = Depends(get_db)`

### 4.3 错误处理
- 使用 `HTTPException` 抛出标准 HTTP 错误。
- 业务逻辑异常应尽早在 Service 层捕获并转化为 HTTP 状态码。

## 5. AI 模块规范
详见 [ai-skills.md](ai-skills.md)
- **位置**: `app/ai/`
- **架构**: 复杂的 AI 流程应封装为 **Skill** 或 **LangGraph 工作流**。
- **调用**: API 层通过异步方式调用 AI 服务，长耗时操作应放入 Celery 任务队列。
- **Skill 开发**: 文件名必须以 `_skill.py` 结尾才能被自动加载
- **命名规范**: 类名使用 `PascalCase` + `Skill` 后缀
- **错误处理**: 必须实现 JSON 解析容错逻辑
- **温度参数**: 质检类使用 0.3，创作类使用 0.7

## 6. API 测试规范 (CRITICAL)

### 6.1 每次修改后必须测试
**重要**: 任何 API 修改后，**必须**用 curl 或 Python 脚本验证后才能认为完成。

```bash
# 验证 API 工作的正确方式
python3 debug_api.py   # 调用实际接口，检查状态码和响应
```

### 6.2 测试要点
- 检查 HTTP 状态码 (201, 400, 401, 500)
- 检查响应 JSON 结构是否符合预期
- 检查数据库是否正确写入/读取

### 6.3 常见错误
| 错误 | 原因 | 避免方法 |
|------|------|---------|
| 500 Internal Error | 模型字段与数据库不匹配 | 先测试 API，不要假设代码正确 |
| 400 Bad Request | 请求体字段名错误 | 对照前端 payload 检查 |
| 401 Unauthorized | Token 未注入 | 检查拦截器逻辑 |

---

## 6.4 任务/批次状态规范 (Task & Batch Status)

**单一来源**: `app/core/status.py`

### 任务状态 (AITask.status)
- `pending`, `queued`, `running`, `retrying`, `in_progress`, `cancelling`, `completed`, `failed`, `canceled`

### 批次状态 (Batch.breakdown_status)
- `pending`, `queued`, `in_progress`, `completed`, `failed`

### 关联规则（必须遵守）
- `running/retrying/in_progress/cancelling` → `in_progress`
- `completed` → `completed`
- `failed` → `failed`
- `canceled` → `pending`

### 实现要求
- 写入任务状态必须走 `normalize_task_status()`
- 批次状态必须通过 `map_task_status_to_batch()` 同步

> **Warning**: 状态常量必须统一！`TaskStatus.IN_PROGRESS` 和 `BatchStatus.IN_PROGRESS` 都使用 `"in_progress"` 值，不能混用 `processing` 和 `in_progress`。

## 7. 专题规范文档

### 7.1 安全规范
详见 [security.md](security.md)
- 应用层加密 vs 数据库级加密的决策指南
- API Key 脱敏显示模式
- 数据库迁移中的敏感数据处理
- 安全检查清单

### 7.2 数据库规范
详见 [database.md](database.md)
- 破坏性变更的多阶段迁移策略
- 字段类型变更的安全做法
- 加密字段迁移的常见错误和正确做法
- 迁移文件命名和注释规范
- 数据迁移脚本模式

### 7.3 WebSocket 消息推送模式
详见 [websocket-patterns.md](websocket-patterns.md)
- 双频道架构设计 (progress vs logs)
- 添加新消息类型的标准流程
- 降级设计模式 (WebSocket + 轮询)
- 消息发送时机和顺序
- 常见陷阱: 频道命名、消息丢失、时序问题

---

## 8. 常见错误与陷阱 (Common Mistakes)

### 8.1 API 分页与字段选择优化

**问题**: 返回不需要的字段导致数据传输量大，数据库查询效率低

**场景**: 列表 API 返回所有字段，大项目可能有大量数据

**优化方案**:

```python
# ❌ 错误：返回所有字段，无分页
@router.get("/project-breakdowns")
async def get_project_breakdowns(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(PlotBreakdown)  # 查询所有字段
        .join(Batch)
        .join(Project)
        .where(Project.id == project_id, Project.user_id == current_user.id)
    )
    breakdowns = result.scalars().all()

    # 返回 6 个字段，但前端只需要 2 个
    return [
        {
            "id": str(bd.id),
            "batch_id": str(bd.batch_id),
            "plot_points": bd.plot_points,
            "qa_status": bd.qa_status,
            "qa_score": bd.qa_score,
            "created_at": bd.created_at.isoformat()
        }
        for bd in breakdowns
    ]

# ✅ 正确：分页 + 指定字段
@router.get("/project-breakdowns")
async def get_project_breakdowns(
    project_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import func

    # 1. 先查询总数
    count_result = await db.execute(
        select(func.count(PlotBreakdown.id))
        .join(Batch).join(Project)
        .where(Project.id == project_id, Project.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    # 2. 分页查询，只返回需要的字段
    result = await db.execute(
        select(
            PlotBreakdown.id,
            PlotBreakdown.batch_id,
            PlotBreakdown.plot_points  # 只返回这 3 个字段
        )
        .join(Batch).join(Project)
        .where(Project.id == project_id, Project.user_id == current_user.id)
        .order_by(PlotBreakdown.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = result.all()

    return {
        "items": [
            {"id": str(row.id), "batch_id": str(row.batch_id), "plot_points": row.plot_points}
            for row in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }
```

**优化效果**:

| 优化点 | 效果 |
|--------|------|
| 减少返回字段 | 6 → 3 字段，减少约 50% 数据传输 |
| 添加分页 | 支持大项目分页加载 |
| 使用 select() 指定字段 | 只查询需要的字段，减少 DB IO |

### 8.2 SQLAlchemy AsyncSession 方法

**问题**: `expire_all()` 是同步方法，不能使用 `await`

```python
# ❌ 错误：会抛出 "object NoneType can't be used in 'await' expression"
await db.expire_all()

# ✅ 正确：直接调用，不使用 await
db.expire_all()
```

**其他同步方法**（不要用 await）:
- `db.expire_all()`
- `db.expunge(obj)`
- `db.expunge_all()`
- `db.add(obj)`
- `db.delete(obj)`

**异步方法**（必须用 await）:
- `await db.execute()`
- `await db.commit()`
- `await db.rollback()`
- `await db.refresh(obj)`
- `await db.flush()`

### 8.3 SQLAlchemy 布尔比较

**问题**: 直接使用 `== True` 或 `== False` 会触发 flake8 警告，且不符合 SQLAlchemy 最佳实践

**错误示例**:

```python
# ❌ 错误：触发 E712 警告
stmt = select(Announcement).where(Announcement.is_published == True)
stmt = select(Announcement).where(Announcement.is_deleted == False)
```

**正确做法**:

```python
# ✅ 正确：使用 .is_() 方法
stmt = select(Announcement).where(Announcement.is_published.is_(True))
stmt = select(Announcement).where(Announcement.is_deleted.is_(False))

# ✅ 更简洁：对于 True 可以省略
stmt = select(Announcement).where(Announcement.is_published)

# ✅ 更简洁：对于 False 使用 not_
from sqlalchemy import not_
stmt = select(Announcement).where(not_(Announcement.is_deleted))
```

**为什么这样做**:
1. **符合 PEP 8**: 避免 `== True` 和 `== False` 的反模式
2. **SQLAlchemy 推荐**: `.is_()` 是 SQLAlchemy 提供的专用方法
3. **代码检查**: 通过 flake8 的 E712 检查
4. **可读性**: 更符合 Python 的惯用写法

**批量修复**:
```bash
# 使用 sed 批量修复（macOS）
sed -i '' 's/== False/.is_(False)/g' app/api/v1/your_file.py
sed -i '' 's/== True/.is_(True)/g' app/api/v1/your_file.py
```

### 8.4 WebSocket 双通道同步

**问题**: 任务完成消息只发送到一个 Redis 频道，导致另一个 WebSocket 连接无法收到完成通知

**场景**: 系统有两个 WebSocket 端点：
- `/ws/breakdown/{task_id}` - 订阅 `breakdown:progress:{task_id}` 频道
- `/ws/breakdown-logs/{task_id}` - 订阅 `breakdown:logs:{task_id}` 频道

**解决方案**: 任务完成时，必须向两个频道都发送消息

```python
# ✅ 正确：向两个频道都发送完成消息
async def on_task_complete(task_id: str, status: str):
    # 1. 发送到 progress 频道
    await publish_progress(task_id, {"status": status, "progress": 100})

    # 2. 发送到 logs 频道
    log_publisher.publish_task_complete(task_id, status)
```

### 8.3 状态字符串规范化

**问题**: 前后端状态字符串大小写不一致，导致判断失败

```python
# ❌ 错误：直接比较，可能因大小写不匹配而失败
if qa_status == "FAIL":
    retry_qa()

# ✅ 正确：规范化后再比较
normalized_status = qa_status.upper() if isinstance(qa_status, str) else "PENDING"
if normalized_status == "FAIL":
    retry_qa()

# ✅ 正确：保存到数据库时也要规范化
task.qa_status = qa_status.upper() if qa_status else "PENDING"
```

**规范**: 状态字符串统一使用大写存储（`PASS`, `FAIL`, `PENDING`）

### 8.4 WebSocket 消息处理优先级

**问题**: WebSocket 循环中同时检查 Redis 消息和数据库状态，导致任务完成消息还没处理完就被数据库状态触发关闭

```python
# ❌ 错误：每次循环都检查数据库，可能提前关闭连接
while True:
    message = await pubsub.get_message(timeout=1.0)
    if message:
        await websocket.send_json(json.loads(message['data']))

    # 问题：Redis 消息还没处理完，数据库状态已经是 completed
    task = await db.get(task_id)
    if task.status == "completed":
        break  # 提前关闭，丢失最后的消息

# ✅ 正确：处理完 Redis 消息后跳过数据库检查
while True:
    message = await pubsub.get_message(timeout=1.0)
    if message:
        await websocket.send_json(json.loads(message['data']))
        continue  # 关键：跳过本次循环的数据库检查

    # 只有没有 Redis 消息时才检查数据库（兜底）
    task = await db.get(task_id)
    if task.status == "completed":
        break
```

### 8.5 外键引用表不匹配

**问题**: 模型字段的外键指向错误的表，导致插入时外键约束违反

**场景**:
- 项目配置中 `breakdown_model_id` 存储的是 `ai_models` 表的 ID
- 但 `plot_breakdowns.model_config_id` 外键指向 `model_configs` 表
- 插入时报错：`ForeignKeyViolation: Key (model_config_id)=(...) is not present in table "model_configs"`

**症状**:
- Celery 任务卡在某个进度（如 90%）不动
- 日志显示大量 `ROLLBACK`
- 任务状态一直是 `running`，不会变成 `completed` 或 `failed`

**解决方案**:

```python
# ❌ 错误：外键指向错误的表
class PlotBreakdown(Base):
    model_config_id = Column(UUID, ForeignKey("model_configs.id"))  # 错误！

# ✅ 正确：外键指向实际存储 ID 的表
class PlotBreakdown(Base):
    ai_model_id = Column(UUID, ForeignKey("ai_models.id"))  # 正确
```

**预防措施**:
1. 新增外键字段前，确认 ID 来源于哪个表
2. 字段命名应反映实际引用的表（如 `ai_model_id` 而非 `model_config_id`）
3. 数据库迁移前先验证外键关系

### 8.6 SQLAlchemy 事务回滚错误 (PendingRollbackError)

**问题**: 在异常处理中访问 ORM 对象的属性时触发 `PendingRollbackError`

**场景**: 批量操作中某个批次失败后，在 `except` 块中访问 `batch.id` 触发隐式数据库查询

**错误信息**:
```
sqlalchemy.exc.PendingRollbackError: This Session's transaction has been rolled back
due to a previous exception during flush. To begin a new transaction with this Session,
first issue Session.rollback().
```

**根本原因**:
1. SQLAlchemy 在 `flush()` 失败后，session 进入"待回滚"状态
2. 此时任何数据库操作（包括访问 lazy-loaded 属性）都会触发此错误
3. 如果 ORM 对象的属性已过期（expired），访问它会触发隐式查询

**解决方案**:

```python
# ❌ 错误：在异常处理中访问可能已过期的属性
for batch in batches:
    try:
        db.add(task)
        await db.flush()
    except Exception:
        failed_batches.append(str(batch.id))  # 错误！可能触发隐式查询
        continue

# ✅ 正确：提前提取需要的属性
for batch in batches:
    batch_id_str = str(batch.id)  # 在 try 之前提取
    try:
        db.add(task)
        await db.flush()
    except Exception:
        await db.rollback()  # 先回滚
        failed_batches.append(batch_id_str)  # 使用预先提取的值
        continue
```

**预防措施**:
1. 在可能导致事务失败的操作前，提前提取所有需要的 ORM 属性
2. 在异常处理块中，先执行 `await db.rollback()` 再进行其他操作
3. 避免在异常处理中访问 ORM 对象的任何属性

### 8.7 MissingGreenlet 错误（对象过期访问）

**问题**: 在异步代码中访问已过期的 ORM 对象属性时触发 `MissingGreenlet` 错误

**场景**: 执行 `with_for_update()` 锁定查询后，之前查询的对象属性自动过期，访问时触发同步查询

**错误信息**:
```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call
await_only() here. Was IO attempted in an unexpected place?
```

**根本原因**:
1. SQLAlchemy 在执行新查询时会自动 expire 之前查询的对象
2. 特别是使用 `with_for_update()` 这种锁定查询时
3. 访问已过期的属性会触发隐式的同步数据库查询
4. 在异步环境中，同步查询无法执行，导致 `MissingGreenlet` 错误

**解决方案**:

```python
# ❌ 错误：在锁定查询后访问之前查询的对象
batches = await db.execute(select(Batch).where(...)).scalars().all()

# 锁定用户记录（会导致 batches 对象过期）
locked_user = await db.execute(
    select(User).where(User.id == user_id).with_for_update()
).scalar_one()

for batch in batches:
    batch_id = str(batch.id)  # 错误！batch 已过期，触发同步查询

# ✅ 正确：在可能导致对象过期的操作前提取所有属性
batches = await db.execute(select(Batch).where(...)).scalars().all()

# 提前提取所有需要的属性
batch_data = [
    {
        "batch": batch,
        "batch_id": batch.id,
        "project_id": batch.project_id
    }
    for batch in batches
]

# 锁定用户记录
locked_user = await db.execute(
    select(User).where(User.id == user_id).with_for_update()
).scalar_one()

# 使用预先提取的数据
for data in batch_data:
    batch_id_str = str(data["batch_id"])  # 正确！使用普通 Python 数据
```

**预防措施**:
1. 在 `with_for_update()` 等锁定查询前，提取所有需要的 ORM 属性
2. 将 ORM 对象的属性转换为普通 Python 数据结构（dict/list）
3. 避免在锁定查询后访问之前查询的 ORM 对象

### 8.8 状态常量不一致问题

**问题**: `TaskStatus.IN_PROGRESS` 和 `BatchStatus.PROCESSING` 值不同，导致 API 报错

**症状**:
```
AttributeError: type object 'TaskStatus' has no attribute 'PROCESSING'
```

**根本原因**:
- `TaskStatus` 使用 `IN_PROGRESS = "in_progress"`
- `BatchStatus` 使用 `PROCESSING = "processing"`
- 代码中混用了这两个常量

**解决方案**: 统一使用 `"in_progress"` 值

```python
# ❌ 错误：值不一致
class TaskStatus:
    IN_PROGRESS = "in_progress"

class BatchStatus:
    PROCESSING = "processing"  # 不一致！

# ✅ 正确：统一值
class TaskStatus:
    IN_PROGRESS = "in_progress"

class BatchStatus:
    IN_PROGRESS = "in_progress"  # 统一
```

**规范**:
1. 所有状态常量值必须统一使用 `"in_progress"`
2. 不要混用 `PROCESSING` 和 `IN_PROGRESS`
3. 如果需要兼容旧代码，可以在 `TaskStatus` 中添加别名

### 8.9 事务中止后的 Session 恢复 (InFailedSqlTransaction)

**问题**: 事务被 abort 后，即使执行 `rollback()`，后续数据库查询仍然报错 "current transaction is aborted"

**场景**: Celery 任务执行过程中遇到数据库错误，进入失败处理函数后尝试查询数据库

**错误信息**:
```
psycopg2.errors.InFailedSqlTransaction: current transaction is aborted,
commands ignored until end of transaction block
```

**根本原因**:
1. 任务执行过程中某个数据库操作失败（外键约束、并发冲突等）
2. PostgreSQL 事务进入 abort 状态
3. 简单的 `db.rollback()` 不足以完全恢复 session 状态
4. 后续任何数据库操作都会失败

**错误的修复方式**:

```python
# ❌ 错误：rollback 后立即查询，session 仍处于异常状态
def _handle_task_failure_sync(db, task_id, ...):
    try:
        db.rollback()
    except Exception:
        pass

    # 立即查询，可能报错 "transaction is aborted"
    task = db.query(AITask).filter(AITask.id == task_id).first()
```

**正确的修复方式**:

```python
# ✅ 正确：关闭旧 session，创建新 session
def _handle_task_failure_sync(db, task_id, batch_record, ...):
    # 1. 预先提取需要的属性（在关闭 session 前）
    batch_id_str = str(batch_record.id) if batch_record else None

    try:
        # 2. 尝试回滚
        try:
            db.rollback()
        except Exception:
            pass

        # 3. 关闭当前 session
        db.close()

        # 4. 创建新 session，确保事务状态干净
        db = SyncSessionLocal()

        # 5. 重新查询 ORM 对象
        task_record = db.query(AITask).filter(AITask.id == task_id).first()
        batch_record = db.query(Batch).filter(Batch.id == task_record.batch_id).first()

        # 6. 继续后续操作...
```

**关键步骤**:
1. **提前提取属性**: 在关闭 session 前提取所有需要的 ORM 属性
2. **关闭 session**: `db.close()` 完全释放连接
3. **创建新 session**: `db = SyncSessionLocal()` 获取干净的事务状态
4. **重新查询**: 使用新 session 查询所有需要的对象

**适用场景**:
- Celery 任务的失败处理函数
- 任何需要在事务失败后继续操作的场景
- 特别是需要查询 `llm_call_logs` 等表计算 Token 使用量时

**预防措施**:
1. 所有失败处理函数都应该使用这个模式
2. 不要假设 `rollback()` 能完全恢复 session 状态
3. 在异常处理中访问数据库前，先创建新 session

**相关错误**:
- `PendingRollbackError` (8.6)
- `MissingGreenlet` (8.7)

### 8.10 任务卡在 cancelling 状态

**问题**: 任务卡在 `cancelling` 状态，无法转换为 `canceled`，导致新任务无法启动

**根本原因**: 系统使用两阶段取消机制：
1. API 端设置 `task.status = TaskStatus.CANCELLING`
2. Celery 任务在检查点检测到状态变化，抛出 `TaskCancelledError`
3. 异常处理器将状态更新为 `canceled`

**卡住的场景**:
- Celery 任务已完成，但状态还是 `cancelling`
- Celery Worker 已停止
- 任务在长时间 AI 调用中（检查点间隔过大）
- `celery_app.control.revoke()` 调用失败

**解决方案 1**: 在 `/batch-start` API 中添加超时清理逻辑

```python
# 在检查现有任务之前，清理超时的 cancelling 任务
CANCELLING_TIMEOUT = timedelta(minutes=5)
now = datetime.now(timezone.utc)

stuck_tasks = await db.execute(
    select(AITask).where(AITask.status == TaskStatus.CANCELLING)
)

for stuck_task in stuck_tasks:
    task_age = now - (stuck_task.updated_at or stuck_task.created_at)
    if task_age > CANCELLING_TIMEOUT:
        # 超时，清理任务状态
        stuck_task.status = TaskStatus.CANCELED
        stuck_task.completed_at = datetime.now(timezone.utc)

        # 恢复批次状态
        if stuck_task.batch_id:
            batch.breakdown_status = BatchStatus.PENDING

await db.commit()
```

**解决方案 2**（推荐）: 添加后台定时任务清理

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
                        new_status=BatchStatus.PENDING,
                        db=db,
                        logger=logger
                    )

        db.commit()
    finally:
        db.close()
```

**配置定时任务（Celery Beat）**:
```python
celery_app.conf.beat_schedule = {
    'cleanup-stuck-cancelling-tasks': {
        'task': 'app.tasks.cleanup_stuck_cancelling_tasks',
        'schedule': 300.0,  # 5 分钟
    },
}
```

---

## 9. 任务队列与顺序执行 (Task Queue & Sequential Execution)

### 9.1 Celery 任务依赖链

**场景**: 需要按顺序执行多个批次的拆解任务，确保批次 N+1 在批次 N 完成后才开始

**实现模式**:

```python
# API 层：创建任务链
previous_task_id = None

for idx, batch in enumerate(batches):
    task = AITask(
        batch_id=batch.id,
        depends_on=[previous_task_id] if previous_task_id else [],  # 依赖前一个任务
        status=TaskStatus.QUEUED,
        ...
    )
    db.add(task)
    await db.flush()

    # 只启动第一个任务
    if idx == 0:
        celery_task = run_breakdown_task.delay(
            str(task.id), str(batch.id), str(project_id), str(user_id)
        )
        task.celery_task_id = celery_task.id

    previous_task_id = str(task.id)

await db.commit()
```

```python
# Celery 任务层：任务完成后触发下一个
def _trigger_next_task_sync(db: Session, completed_task_id: str, project_id: str, user_id: str):
    """触发下一个依赖任务（顺序执行）"""
    # 查找依赖当前任务的下一个任务
    next_task = db.query(AITask).filter(
        AITask.project_id == project_id,
        AITask.status == TaskStatus.QUEUED,
        AITask.depends_on.contains([completed_task_id])  # JSONB 数组包含查询
    ).first()

    if next_task:
        # 启动 Celery 任务
        celery_task = run_breakdown_task.delay(
            str(next_task.id),
            str(next_task.batch_id),
            str(project_id),
            str(user_id)
        )
        next_task.celery_task_id = celery_task.id
        db.commit()

# 在任务完成时调用
@celery_app.task
def run_breakdown_task(self, task_id, batch_id, project_id, user_id):
    try:
        # ... 执行任务逻辑 ...

        # 任务完成后触发下一个
        _trigger_next_task_sync(db, task_id, project_id, user_id)

        return {"status": TaskStatus.COMPLETED, "task_id": task_id}
    except Exception as e:
        # 错误处理...
        raise
```

**关键点**:
1. **依赖关系**: 使用 `depends_on` JSONB 字段存储依赖的任务 ID 列表
2. **延迟启动**: 只启动第一个任务，后续任务由前一个任务完成时触发
3. **JSONB 查询**: 使用 PostgreSQL 的 `contains()` 方法查询依赖关系
4. **失败隔离**: 某个任务失败不会自动启动后续任务（需要手动重试）

**优势**:
- 严格保证执行顺序
- 资源节约（同一时间只有一个任务在执行）
- 失败隔离（某个批次失败不影响已完成的批次）

**注意事项**:
- 如果中间某个任务失败，后续任务不会自动启动
- 前端轮询进度时会看到任务逐个完成，而不是同时进行

### 9.2 智能状态回滚机制

**场景**: 批次拆解失败时，如果之前有成功的拆解结果，应该恢复批次状态而不是标记为失败

**问题**:
- 用户第一次拆解成功，生成了有效数据
- 用户第二次重试拆解失败（网络超时、配额不足等）
- 批次状态被标记为 `failed`，但实际上有有效的历史数据
- 用户看到"拆解失败"，但数据库中有可用的结果

**解决方案**: 智能回滚机制

```python
def _check_previous_breakdown_success(db: Session, batch_id: str, current_task_id: str) -> bool:
    """检查批次是否有之前成功的拆解结果

    Args:
        db: 数据库会话
        batch_id: 批次 ID
        current_task_id: 当前失败的任务 ID

    Returns:
        bool: 如果有之前成功的拆解结果返回 True
    """
    # 1. 查找该批次下所有成功完成的任务（排除当前失败的任务）
    successful_tasks = db.query(AITask).filter(
        AITask.batch_id == batch_id,
        AITask.id != current_task_id,
        AITask.status == TaskStatus.COMPLETED
    ).all()

    if not successful_tasks:
        return False

    # 2. 检查是否有对应的有效拆解结果
    for task in successful_tasks:
        breakdown = db.query(PlotBreakdown).filter(
            PlotBreakdown.batch_id == batch_id,
            PlotBreakdown.task_id == task.id,
            PlotBreakdown.plot_points.isnot(None)
        ).first()

        # 3. 验证剧情点数据的有效性
        if breakdown and isinstance(breakdown.plot_points, list) and len(breakdown.plot_points) > 0:
            logger.info(f"批次 {batch_id} 找到之前的成功结果")
            return True

    return False


def _handle_task_failure_sync(db, task_id, batch_record, ...):
    """处理任务失败（带智能回滚）"""
    # ... 更新任务状态 ...

    # 更新批次状态（智能回滚机制）
    if batch_record:
        has_previous_success = _check_previous_breakdown_success(db, batch_record.id, task_id)

        if has_previous_success:
            # 有之前的成功结果，恢复为 completed 状态
            batch_record.breakdown_status = BatchStatus.COMPLETED
            logger.info(f"批次 {batch_record.id} 有之前的成功结果，状态回滚为 completed")

            if log_publisher:
                log_publisher.publish_warning(
                    task_id,
                    "当前任务失败，但批次已恢复到之前的成功状态"
                )
        else:
            # 没有之前的成功结果，标记为 failed
            batch_record.breakdown_status = BatchStatus.FAILED
            logger.info(f"批次 {batch_record.id} 无之前的成功结果，状态更新为 failed")

        db.commit()
```

**应用场景**:
1. **普通任务失败** (`_handle_task_failure_sync`)
2. **任务超时** (`_handle_timeout_failure_sync`)
3. **配额不足** (`_handle_quota_exceeded_sync`)
4. **管理员手动停止** (`admin_core.py:stop_task`)
5. **系统自动终止** (`task_monitor.py:_terminate_stuck_task`)
6. **Celery 提交失败** (`breakdown.py:start_all_breakdowns`)

**统一状态更新函数** (2026-02-23 新增):

为确保所有场景都正确应用智能回滚，新增了统一的状态更新函数：

```python
def _update_batch_status_safely(
    batch,
    task,
    new_status: str,
    db,
    logger
) -> None:
    """
    安全地更新批次状态，应用智能回滚机制

    核心逻辑：
    1. 根据任务类型确定要更新的状态字段（breakdown_status 或 script_status）
    2. 如果要设置为 failed，检查是否有之前的成功结果
    3. 有成功结果则恢复为 completed，保护用户已有成果
    """
    # 1. 根据任务类型确定要更新的字段
    if task.task_type == "breakdown":
        status_field = "breakdown_status"
    elif task.task_type in ("script", "episode_script"):
        status_field = "script_status"

    # 2. 如果要设置为 failed，检查是否有之前的成功结果（仅对 breakdown 任务）
    if new_status == BatchStatus.FAILED and task.task_type == "breakdown":
        has_success = _check_previous_breakdown_success(db, batch.id, task.id)
        if has_success:
            new_status = BatchStatus.COMPLETED
            logger.info(f"批次 {batch.id} 有之前的成功结果，恢复为 completed")

    # 3. 更新状态
    setattr(batch, status_field, new_status)
```

**状态字段隔离原则**:

| 任务类型 | 影响的状态字段 | 不应影响的字段 |
|---------|--------------|---------------|
| `breakdown` | `breakdown_status` | `script_status` |
| `script` / `episode_script` | `script_status` | `breakdown_status` |

**实现要点**:
1. **排除当前任务**: 检查时必须排除当前失败的任务，只查找之前的成功任务
2. **验证数据有效性**: 不仅检查任务状态，还要验证拆解结果真实存在且有效
3. **用户通知**: 通过 WebSocket 实时通知用户状态变化
4. **日志记录**: 详细记录回滚原因，便于问题追踪

**使用示例**:

```python
# 场景1：用户重试拆解
第一次拆解: 成功 → 15个剧情点
第二次拆解: 失败（网络超时）
结果: 批次状态自动恢复为 completed ✅

# 场景2：配额不足
第一次拆解: 成功 → 20个剧情点
第二次拆解: 失败（API配额不足）
结果: 批次状态自动恢复为 completed ✅

# 场景3：真正的失败
第一次拆解: 失败（数据格式错误）
第二次拆解: 失败（模型错误）
结果: 批次状态保持为 failed ❌（因为没有有效的历史数据）
```

**优势**:
- **数据保护**: 避免因后续任务失败而丢失之前的有效数据
- **用户体验**: 避免"明明有数据却显示失败"的困惑
- **智能判断**: 不仅检查任务状态，还验证数据的真实有效性
- **全面覆盖**: 在所有失败场景中都实现了智能回滚

**注意事项**:
- 智能回滚只恢复批次状态，失败的任务状态仍然保持为 `failed`
- 前端应该根据批次状态显示结果，而不是最新任务的状态
- 如果需要查看失败原因，可以通过任务历史查询

---

### 8.11 FastAPI 路由顺序错误

**问题**: 具体路由被参数路由拦截，导致 UUID 解析错误

**场景**: 定义了 `/announcements/{announcement_id}` 和 `/announcements/unread-count` 两个路由

**错误信息**:
```json
{
  "detail": [{
    "type": "uuid_parsing",
    "msg": "Input should be a valid UUID, invalid character: expected an optional prefix of `urn:uuid:` followed by [0-9a-fA-F-], found `u` at 1",
    "input": "unread-count"
  }]
}
```

**根本原因**:
- FastAPI 按照路由定义的顺序进行匹配
- 如果 `/announcements/{announcement_id}` 在前，`unread-count` 会被当作 UUID 参数解析
- 导致 Pydantic 验证失败

**错误示例**:

```python
# ❌ 错误：参数路由在前，拦截了具体路由
@router.get("/announcements/{announcement_id}")
async def get_announcement(announcement_id: UUID):
    ...

@router.get("/announcements/unread-count")  # 永远不会被匹配到！
async def get_unread_count():
    ...
```

**正确做法**:

```python
# ✅ 正确：具体路由在前，参数路由在后
@router.get("/announcements/unread-count")
async def get_unread_count():
    ...

@router.get("/announcements/{announcement_id}")
async def get_announcement(announcement_id: UUID):
    ...
```

**路由顺序规则**:

1. **最具体的路由放在最前面**
   ```python
   /users/me/profile          # 最具体
   /users/me                  # 较具体
   /users/{user_id}           # 通用参数路由
   ```

2. **固定路径优先于参数路径**
   ```python
   /items/search              # 固定路径
   /items/{item_id}           # 参数路径
   ```

3. **多段路径的具体性判断**
   ```python
   /api/v1/users/admin        # 更具体
   /api/v1/users/{role}       # 较通用
   /api/v1/{resource}/{id}    # 最通用
   ```

**预防措施**:
1. 在添加新路由时，检查是否有类似的参数路由
2. 将所有固定路径的路由放在文件前面
3. 使用更明确的路径名称，避免歧义（如 `/stats/unread` 而非 `/unread-count`）
4. 测试时检查路由是否被正确匹配

**相关错误**:
- 类似的问题也会出现在 `/users/me` vs `/users/{user_id}` 等场景

---

**最后更新**: 2026-02-26

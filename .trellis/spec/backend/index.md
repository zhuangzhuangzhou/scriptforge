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

---

## 8. 常见错误与陷阱 (Common Mistakes)

### 8.1 SQLAlchemy AsyncSession 方法

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

### 8.2 WebSocket 双通道同步

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

---

**最后更新**: 2026-02-15

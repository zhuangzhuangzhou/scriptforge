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
- **位置**: `app/ai/`
- **架构**: 复杂的 AI 流程应封装为 **Skill** 或 **LangGraph 工作流**。
- **调用**: API 层通过异步方式调用 AI 服务，长耗时操作应放入 Celery 任务队列。

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

# ScriptForge 架构文档

## 系统架构

### 整体架构图

```mermaid
graph TB
    subgraph "前端层 (Frontend)"
        UI[React UI]
        WS_CLIENT[WebSocket Client]
    end

    subgraph "后端层 (Backend)"
        API[FastAPI REST API]
        WS_SERVER[WebSocket Server]
        WORKERS[Celery Workers]
        BEAT[Celery Beat]
    end

    subgraph "AI 引擎层 (AI Engine)"
        ORCHESTRATOR[Orchestrator]
        SKILLS[Skills Library]
        ALIGNERS[QA Aligners]
        ADAPTERS[Model Adapters]
    end

    subgraph "数据层 (Data Layer)"
        POSTGRES[(PostgreSQL)]
        REDIS[(Redis)]
        MINIO[(MinIO/S3)]
    end

    subgraph "外部服务 (External)"
        OPENAI[OpenAI API]
        ANTHROPIC[Anthropic API]
    end

    UI --> API
    UI --> WS_CLIENT
    WS_CLIENT --> WS_SERVER
    API --> WORKERS
    API --> POSTGRES
    API --> REDIS
    WORKERS --> ORCHESTRATOR
    ORCHESTRATOR --> SKILLS
    ORCHESTRATOR --> ALIGNERS
    ORCHESTRATOR --> ADAPTERS
    ADAPTERS --> OPENAI
    ADAPTERS --> ANTHROPIC
    BEAT --> WORKERS
    WORKERS --> POSTGRES
    WORKERS --> REDIS
    WORKERS --> MINIO
    WS_SERVER --> REDIS
```

### AI 工作流架构

```mermaid
graph LR
    subgraph "两阶段处理流程"
        A[小说文本] --> B[阶段1: 剧情拆解]
        B --> C[Breakdown Aligner<br/>质检]
        C -->|未通过| D[自动修正]
        D --> C
        C -->|通过| E[阶段2: 剧本生成]
        E --> F[Webtoon Aligner<br/>质检]
        F -->|未通过| G[自动修订]
        G --> F
        F -->|通过| H[最终剧本]
    end
```

---

## 核心流程

### 业务流程图

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as 前端
    participant API as FastAPI
    participant Worker as Celery Worker
    participant AI as AI Engine
    participant DB as PostgreSQL
    participant Storage as MinIO

    User->>Frontend: 上传小说文件
    Frontend->>API: 创建项目
    API->>DB: 保存项目信息
    API->>Storage: 存储小说文件

    User->>Frontend: 启动剧情拆解
    Frontend->>API: 请求拆解任务
    API->>Worker: 创建异步任务
    API-->>Frontend: 返回任务 ID

    loop 批次处理
        Worker->>AI: 执行 Breakdown Skill
        AI->>AI: Breakdown Aligner 质检

        alt 质检未通过
            AI->>AI: 自动修正
            AI->>AI: 重新质检
        end

        Worker->>DB: 保存拆解结果
        Worker->>Frontend: WebSocket 推送进度
    end

    User->>Frontend: 启动剧本生成
    Frontend->>API: 请求生成任务
    API->>Worker: 创建异步任务

    loop 批次处理
        Worker->>AI: 执行 Script Skill
        AI->>AI: Webtoon Aligner 质检

        alt 质检未通过
            AI->>AI: 自动修订
            AI->>AI: 重新质检
        end

        Worker->>DB: 保存剧本内容
        Worker->>Storage: 存储 Markdown 文件
        Worker->>Frontend: WebSocket 推送进度
    end

    User->>Frontend: 导出剧本
    Frontend->>API: 请求导出
    API->>Storage: 读取剧本文件
    API->>API: 生成 PDF
    API-->>Frontend: 返回下载链接
```

---

## 质检系统详解

### 自动质检闭环流程

```mermaid
graph TD
    A[AI 生成内容] --> B[调用 Aligner 质检]
    B --> C{质检结果}

    C -->|PASS| D[保存结果]
    C -->|FAIL| E[提取问题列表]

    E --> F{重试次数 < 3?}
    F -->|是| G[根据反馈修正内容]
    G --> B

    F -->|否| H[标记为失败]
    H --> I[通知用户处理]

    D --> J[继续下一步]

    style B fill:#4CAF50
    style C fill:#2196F3
    style F fill:#FF9800
    style D fill:#4CAF50
    style H fill:#F44336
```

### 质检维度

| 质检器 | 检查维度 | 说明 |
|--------|---------|------|
| **Breakdown Aligner** | 剧情还原度 | 确保拆解结果忠实于原著 |
| | 剧情钩子 | 检查是否识别了所有剧情钩子 |
| | 冲突点提取 | 验证冲突点的完整性和准确性 |
| | 人物关系 | 检查人物关系的一致性 |
| | 场景识别 | 验证场景划分的合理性 |
| **Webtoon Aligner** | 剧情使用率 | 确保有效使用拆解的剧情点 |
| | 跨集连贯性 | 检查剧集之间的连贯性 |
| | 节奏控制 | 验证每集的节奏和张力 |
| | 视觉化风格 | 检查是否符合漫剧视觉化要求 |
| | 格式规范 | 验证剧本格式是否标准 |
| | 悬念设置 | 检查悬念和钩子的设置 |

---

## 配置驱动系统

### 动态配置架构

```mermaid
graph TB
    subgraph "数据库配置层"
        CONFIG[配置表]
        SKILLS_DB[Skills 配置]
        AGENTS_DB[Agents 配置]
        PIPELINES_DB[Pipelines 配置]
    end

    subgraph "运行时加载层"
        LOADER[配置加载器]
        REGISTRY[注册表]
    end

    subgraph "执行引擎层"
        EXECUTOR[执行器]
        SKILL_INST[Skill 实例]
        AGENT_INST[Agent 实例]
    end

    CONFIG --> LOADER
    SKILLS_DB --> LOADER
    AGENTS_DB --> LOADER
    PIPELINES_DB --> LOADER

    LOADER --> REGISTRY
    REGISTRY --> EXECUTOR

    EXECUTOR --> SKILL_INST
    EXECUTOR --> AGENT_INST

    SKILL_INST --> |动态创建| OUTPUT[输出结果]
    AGENT_INST --> |动态创建| OUTPUT
```

### 配置热更新流程

```mermaid
sequenceDiagram
    participant Admin as 管理员
    participant Frontend as 前端管理界面
    participant API as REST API
    participant DB as 数据库
    participant Cache as Redis 缓存
    participant Worker as Celery Worker

    Admin->>Frontend: 修改 Skill 配置
    Frontend->>API: POST /api/v1/admin/skills/:id
    API->>DB: 更新配置
    API->>Cache: 清除缓存

    Note over Worker: 下次任务执行时
    Worker->>Cache: 检查缓存
    Cache-->>Worker: 缓存未命中
    Worker->>DB: 加载最新配置
    Worker->>Cache: 缓存配置
    Worker->>Worker: 使用新配置执行
```

---

## 数据流向

### 文件与数据库双向同步

```mermaid
graph LR
    subgraph "输入"
        NOVEL[小说文件<br/>.txt/.docx/.pdf]
    end

    subgraph "处理"
        PARSE[解析器]
        AI[AI 处理]
    end

    subgraph "存储"
        DB[(PostgreSQL<br/>结构化数据)]
        FILES[(MinIO<br/>文件存储)]
    end

    subgraph "输出"
        MARKDOWN[Markdown 剧本<br/>.md]
        PDF[PDF 剧本<br/>.pdf]
    end

    NOVEL --> PARSE
    PARSE --> DB
    PARSE --> AI

    AI --> DB
    AI --> FILES

    FILES --> MARKDOWN
    MARKDOWN --> PDF

    DB -.索引.-> FILES
    FILES -.内容.-> DB
```

---

## 部署架构

### Docker Compose 部署

```mermaid
graph TB
    subgraph "Docker Network"
        FE[frontend<br/>Nginx]
        BE[backend<br/>FastAPI]
        WORKER[worker<br/>Celery]
        BEAT[worker_beat<br/>Celery Beat]
        POSTGRES[postgres<br/>PostgreSQL]
        REDIS[redis<br/>Redis]
        MINIO[minio<br/>MinIO]
    end

    USER((用户)) --> FE
    FE --> BE
    BE --> POSTGRES
    BE --> REDIS
    BE --> MINIO
    WORKER --> POSTGRES
    WORKER --> REDIS
    WORKER --> MINIO
    BEAT --> REDIS
```

---

## 关键技术点

### 1. 异步任务处理

- **Celery**: 处理长时间运行的 AI 任务
- **WebSocket**: 实时推送任务进度
- **Redis**: 任务队列和消息代理

### 2. AI 模型适配

- **多模型支持**: OpenAI GPT-4、Anthropic Claude
- **适配器模式**: 统一的模型调用接口
- **温度参数**: 质检任务使用低温度 (0.3)，创作任务使用高温度 (0.7)

### 3. 质检闭环

- **最大重试次数**: 3 次
- **自动修正**: 根据质检反馈自动调整内容
- **降级策略**: 质检超时时保留已有结果

### 4. 批次处理

- **章节识别**: 自动识别小说章节
- **批次划分**: 每 6 章一个批次
- **顺序执行**: 批次间按顺序处理，确保连贯性

---

## 性能优化

### 数据库优化

- **索引**: 用户 ID、项目 ID、任务状态
- **连接池**: 异步连接池，大小 20
- **批量查询**: 减少数据库访问次数

### 缓存策略

- **配置缓存**: Redis 缓存 Skills/Agents 配置
- **进度缓存**: 任务进度实时缓存
- **TTL**: 配置缓存 5 分钟过期

### 并发控制

- **Worker 并发**: 每个 Worker 4 个并发任务
- **预取限制**: 预取 1 个任务，避免任务堆积
- **任务超时**: 硬超时 30 分钟，软超时 25 分钟

---

## 安全机制

### 认证与授权

- **JWT Token**: 基于 JWT 的用户认证
- **Token 过期**: Access Token 2 小时，Refresh Token 7 天
- **密码加密**: bcrypt 哈希存储

### API 安全

- **CORS**: 白名单域名访问控制
- **Rate Limiting**: API 请求频率限制
- **输入验证**: Pydantic 模型验证

### 数据安全

- **环境变量**: 敏感配置通过 .env 管理
- **SQL 注入防护**: SQLAlchemy ORM
- **XSS 防护**: 前端输入转义
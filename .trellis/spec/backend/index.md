# 后端开发规范

## 技术栈

- **框架**: FastAPI 0.109.0
- **ORM**: SQLAlchemy 2.0.25
- **数据库**: PostgreSQL 15+
- **缓存**: Redis 7
- **异步任务**: Celery 5.3.4

## 目录结构

```
backend/app/
├── api/v1/          # API 路由
├── models/          # 数据库模型
├── core/            # 核心配置
├── ai/              # AI 工作流
├── tasks/           # Celery 任务
└── utils/           # 工具函数
```

## 代码规范

### API 端点
- 使用 APIRouter 组织路由
- 使用 Pydantic 模型验证请求/响应
- 使用依赖注入获取数据库会话和当前用户

### 数据库模型
- 使用 UUID 作为主键
- 添加 created_at/updated_at 时间戳
- 使用 relationship 定义关联

### 异步处理
- 长时间任务使用 Celery
- 使用 async/await 处理 I/O 操作

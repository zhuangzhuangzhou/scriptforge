# 小说改编剧本系统 (Novel-to-Script System)

一款 Web 端应用，让用户能够将上传的小说文件，通过批次处理和两阶段 AI 工作流（剧情拆解 → 剧本生成），自动改编成符合影视剧本标准的剧集。

## 技术栈

### 后端
- Python 3.11+
- FastAPI (Web框架)
- SQLAlchemy (ORM)
- PostgreSQL 15+ (数据库)
- Redis (缓存和任务队列)
- Celery (异步任务)
- LangChain + LangGraph (AI工作流)

### 前端
- React 18
- TypeScript
- Vite
- Ant Design / Material-UI

### 基础设施
- Docker & Docker Compose
- MinIO (对象存储)
- Alembic (数据库迁移)

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd novel-to-script
```

### 2. 启动开发环境

```bash
# 启动 Docker 服务（PostgreSQL, Redis, MinIO）
docker-compose up -d

# 等待服务启动完成
docker-compose ps
```

### 3. 配置后端

```bash
cd backend

# 复制环境变量配置
cp .env.example .env

# 编辑 .env 文件，填入必要的配置（如 OpenAI API Key）
# vim .env

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端服务将在 http://localhost:8000 启动
API 文档：http://localhost:8000/docs

### 4. 配置前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务将在 http://localhost:5173 启动

### 5. 启动 Celery Worker

```bash
cd backend

# 启动 Celery Worker
celery -A app.core.celery_app worker --loglevel=info
```

## 核心功能

### 用户端功能
1. **项目管理**
   - 创建项目并上传小说文件
   - 自动章节识别和批次划分
   - 项目统计信息展示

2. **剧情拆解（Breakdown）**
   - 提取冲突点
   - 识别剧情钩子
   - 分析人物关系
   - 识别场景
   - 提取情绪点

3. **剧本生成（Script）**
   - 规划剧集结构
   - 生成场景描述
   - 编写对话
   - 格式化剧本

4. **导出功能**
   - 单集导出（PDF）
   - 批量打包导出

### 管理端功能
1. 用户管理
2. 系统统计
3. 模型配置管理

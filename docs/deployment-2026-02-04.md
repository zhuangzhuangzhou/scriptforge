# 项目部署步骤文档

本文档记录 2026-02-04 的后端部署与调试过程。

## 目录
- [1. 环境准备](#1-环境准备)
- [2. SSH 隧道配置](#2-ssh-隧道配置)
- [3. Alembic 迁移问题修复](#3-alembic-迁移问题修复)
- [4. 后端服务启动](#4-后端服务启动)
- [5. 已知问题与修复](#5-已知问题与修复)

---

## 1. 环境准备

### 1.1 激活虚拟环境
```powershell
cd D:\DATA\Documents\jim\jim\backend
.\venv\Scripts\activate
```

### 1.2 检查依赖
```powershell
pip list | grep -E "fastapi|sqlalchemy|celery|alembic"
```

---

## 2. SSH 隧道配置

数据库和 MinIO 部署在远程服务器，需要通过 SSH 隧道本地连接。

### 2.1 启动隧道
```powershell
ssh -o ServerAliveInterval=60 -L 5433:127.0.0.1:35432 -L 6380:127.0.0.1:6379 -L 9000:127.0.0.1:19000 root@REMOVED_IP
```

### 2.2 本地端口映射
| 服务 | 远程端口 | 本地端口 |
|------|---------|---------|
| PostgreSQL | 35432 | 5433 |
| Redis | 6379 | 6380 |
| MinIO API | 19000 | 9000 |
| MinIO Console | - | 9001 |

### 2.3 .env 配置
确保 `jim/backend/.env` 中配置正确：
```properties
DATABASE_URL=postgresql+asyncpg://postgres:REMOVED_PASSWORD@127.0.0.1:5433/novel_script
REDIS_URL=redis://127.0.0.1:6380/0
CELERY_BROKER_URL=redis://127.0.0.1:6380/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6380/0
MINIO_ENDPOINT=127.0.0.1:9000
```

---

## 3. Alembic 迁移问题修复

### 3.1 问题描述
运行 `alembic upgrade head` 时报错：
```
Multiple head revisions are present for given argument 'head'
```

### 3.2 原因分析
迁移历史中存在多个并行分支：
- `208695f1899f_init_all_with_skills` (根)
- `add_pipeline_tables` (独立根，down_revision=None)
- `add_skill_visibility` -> `add_agent_system` -> `add_user_tier_system` -> `add_billing_tables`
- `add_skill_template_fields` (从 add_skill_visibility 分叉)

### 3.3 修复步骤

#### 步骤 1: 线性化迁移文件

**文件 1**: `jim/backend/alembic/versions/add_pipeline_tables.py`
```python
# 修改前
down_revision = None

# 修改后
down_revision = '208695f1899f'
```

**文件 2**: `jim/backend/alembic/versions/add_skill_template_fields.py`
```python
# 修改前
down_revision = 'add_skill_visibility'

# 修改后
down_revision = 'add_billing_tables'
```

#### 步骤 2: 标记初始迁移
```powershell
alembic stamp 208695f1899f
```

#### 步骤 3: 执行迁移
```powershell
alembic upgrade head
```

### 3.4 后续迁移错误处理

#### 问题 2: NOT NULL 约束冲突
```
column "owner_id" of relation "skills" contains null values
```

**修复**: 修改 `jim/backend/alembic/versions/add_skill_visibility.py`

```python
def upgrade():
    # 分步添加列，避免 NOT NULL 冲突
    op.add_column('skills', sa.Column('visibility', sa.String(20), default='public'))
    op.add_column('skills', sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE skills SET owner_id = '00000000-0000-0000-0000-000000000001' WHERE owner_id IS NULL")
    op.alter_column('skills', 'owner_id', nullable=False)
    op.add_column('skills', sa.Column('allowed_users', postgresql.JSON))
    # ... skill_versions 表同理
```

---

## 4. 后端服务启动

### 4.1 启动 FastAPI
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4.2 启动 Celery Worker
```powershell
celery -A app.core.celery_app worker --loglevel=info -P solo
```

**注意**: Windows 环境需要添加 `-P solo` 参数，使用单进程模式避免多进程兼容性问题。

### 4.3 验证服务
```powershell
# 健康检查
curl http://localhost:8000/health

# 预期输出
{"status":"healthy"}
```

---

## 5. 已知问题与修复

### 5.1 密码哈希库兼容性问题

#### 问题描述
使用 `passlib` + `bcrypt` 时报错：
```
ValueError: password cannot be longer than 72 bytes
```

#### 解决过程

**尝试 1**: argon2 方案
```python
from argon2 import PasswordHash
ph = PasswordHash(memory_cost=32768, time_cost=3, parallelism=4)
# 问题: argon2 计算太慢，导致注册接口超时
```

**尝试 2**: 直接使用 bcrypt 库
```python
import bcrypt

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt(rounds=10)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )
```

**最终方案**: 修改 `jim/backend/app/core/security.py`

### 5.2 Pydantic UUID 序列化问题

#### 问题描述
注册接口返回时 UUID 类型无法序列化为字符串：
```
ResponseValidationError: Input should be a valid string
```

#### 修复方案
修改 `jim/backend/app/api/v1/auth.py` 中的 `UserResponse` 模型：

```python
from pydantic import field_validator
from uuid import UUID

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    role: str
    balance: float
    is_active: bool
    
    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v
```

### 5.3 Alembic 迁移与数据库状态不一致

#### 问题描述
远程数据库中已存在 `skills` 表，但 `alembic_version` 表中没有迁移记录。

#### 解决方案
使用 `alembic stamp` 标记迁移状态：
```powershell
alembic stamp 208695f1899f
alembic upgrade head
```

---

## 6. 接口测试

### 6.1 基础接口测试
```powershell
# 根路径
curl http://localhost:8000/
# {"name":"Novel to Script (Local Dev)","version":"0.1.0","status":"running"}

# 健康检查
curl http://localhost:8000/health
# {"status":"healthy"}

# 订阅等级
curl http://localhost:8000/api/v1/user/quota/tiers
```

### 6.2 认证接口测试

**注册**
```powershell
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"testpass123","full_name":"Test User"}'
```

**登录** (使用表单格式)
```powershell
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass123"
# {"access_token":"...","token_type":"bearer"}
```

### 6.3 认证接口测试
```powershell
TOKEN="your-jwt-token"

# 获取配额
curl http://localhost:8000/api/v1/user/quota \
  -H "Authorization: Bearer $TOKEN"

# 获取技能
curl http://localhost:8000/api/v1/skills/available \
  -H "Authorization: Bearer $TOKEN"

# 获取项目
curl http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN"

# 获取 Pipelines
curl "http://localhost:8000/api/v1/pipelines/pipelines?include_default=true" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 7. 常见问题排查

### 7.1 数据库连接失败
- 检查 SSH 隧道是否正常运行
- 验证 `.env` 中的 `DATABASE_URL` 配置
- 确认远程数据库端口已开放

### 7.2 MinIO 连接失败
- 检查 MinIO 凭据是否正确
- 确认隧道映射了 9000 端口

### 7.3 Celery Worker 启动失败
- 检查 Redis 连接 (`redis://127.0.0.1:6380/0`)
- Windows 环境必须使用 `-P solo` 参数

### 7.4 API 返回 500 错误
- 查看 uvicorn 控制台日志
- 检查数据库模型与迁移是否一致

---

## 8. 部署检查清单

- [ ] SSH 隧道已建立
- [ ] 数据库迁移已完成 (`alembic upgrade head`)
- [ ] FastAPI 服务运行中 (端口 8000)
- [ ] Celery Worker 运行中 (使用 solo 模式)
- [ ] 健康检查通过 (`/health`)
- [ ] 用户注册/登录功能正常

---

## 9. 参考链接

- FastAPI: https://fastapi.tiangolo.com
- Celery: https://docs.celeryproject.org
- Alembic: https://alembic.sqlalchemy.org
- bcrypt: https://pypi.org/project/bcrypt/

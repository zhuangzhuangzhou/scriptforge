# AI ScriptFlow 开发记录 - 2026年2月3日

## 一、本次开发目标

**对接前端登录接口，打通前后端认证链路，并解决本地开发环境连接远程服务器的各种问题。**

---

## 二、已完成的功能模块

### 1. 前端认证系统 (Frontend)

| 文件路径 | 功能描述 |
|---------|---------|
| `src/services/api.ts` | Axios 封装，自动注入 Bearer Token，401 自动跳转登录页 |
| `src/context/AuthContext.tsx` | 全局认证状态管理，提供 `login`、`logout`、`user` 等 |
| `src/components/ProtectedRoute.tsx` | 路由守卫，未登录用户无法访问受保护页面 |
| `src/pages/auth/Login.tsx` | 对接后端 `/api/v1/auth/login`，支持 OAuth2 表单格式 |
| `src/pages/auth/Register.tsx` | 对接后端 `/api/v1/auth/register`，JSON 格式提交 |
| `src/components/MainLayout.tsx` | 使用 `useAuth()` 显示真实用户名，支持退出登录 |
| `src/App.tsx` | 集成 `AuthProvider` 和 `ProtectedRoute` |

### 2. 后端稳定性优化 (Backend)

| 文件路径 | 修改内容 |
|---------|---------|
| `app/core/storage.py` | MinIO 客户端改为**懒加载**，避免启动时因无法连接而崩溃 |
| `app/models/__init__.py` | 添加 `Skill` 模型导入，修复 Alembic 无法检测到 skills 表的问题 |
| `alembic/script.py.mako` | 补全缺失的 Alembic 模板文件 |

### 3. 环境配置 (`.env`)

```env
# 数据库 (通过 SSH 隧道)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/novel_script

# Redis (通过 SSH 隧道)
REDIS_URL=redis://127.0.0.1:6380/0
CELERY_BROKER_URL=redis://127.0.0.1:6380/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6380/0

# MinIO (通过 SSH 隧道)
MINIO_ENDPOINT=127.0.0.1:9000
MINIO_ACCESS_KEY=minio_access_key
MINIO_SECRET_KEY=REMOVED_SECRET
MINIO_SECURE=False

# 跨域
CORS_ORIGINS=["http://localhost:5173"]
```

---

## 三、服务器端口映射关系

| 服务 | 本地端口 | 远程端口 | 备注 |
|-----|---------|---------|------|
| PostgreSQL | 5433 | 35432 | Docker 容器 `postgresql_trjs-postgresql_TRjS-1` |
| Redis | 6380 | 6379 | |
| MinIO API | 9000 | 19000 | |

**SSH 隧道命令：**
```bash
ssh -o ServerAliveInterval=60 -L 5433:127.0.0.1:35432 -L 6380:127.0.0.1:6379 -L 9000:127.0.0.1:19000 root@REMOVED_IP
```

---

## 四、数据库初始化流程

由于本次是全新环境，需要执行以下步骤：

```bash
# 1. 在服务器上创建数据库
docker exec -it postgresql_trjs-postgresql_TRjS-1 psql -U postgres -c "CREATE DATABASE novel_script;"

# 2. 重置密码（如需要）
docker exec -it postgresql_trjs-postgresql_TRjS-1 psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';"

# 3. 清理 Alembic 版本记录（如遇到版本冲突）
docker exec -it postgresql_trjs-postgresql_TRjS-1 psql -U postgres -d novel_script -c "DROP TABLE IF EXISTS alembic_version;"
```

**本地迁移命令：**
```powershell
cd D:\DATA\Documents\jim\jim\backend
.\venv\Scripts\activate

# 删除旧迁移脚本
rm alembic\versions\*.py

# 生成全量迁移
alembic revision --autogenerate -m "init_all_with_skills"

# 执行迁移
alembic upgrade head
```

---

## 五、本地开发启动流程

```powershell
# 1. 开启 SSH 隧道（新窗口，保持运行）
ssh -o ServerAliveInterval=60 -L 5433:127.0.0.1:35432 -L 6380:127.0.0.1:6379 -L 9000:127.0.0.1:19000 root@REMOVED_IP

# 2. 启动后端
cd D:\DATA\Documents\jim\jim\backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. 启动前端
cd D:\DATA\Documents\jim\jim\frontend
npm run dev
```

---

## 六、遇到的问题及解决方案

| 问题 | 原因 | 解决方案 |
|-----|------|---------|
| `WinError 10054` 连接重置 | Windows IPv6 优先级干扰 SSH 隧道 | `.env` 中 `localhost` 改为 `127.0.0.1`，SSH 添加 `-o ServerAliveInterval=60` |
| MinIO 连接失败导致后端崩溃 | `storage.py` 在模块导入时立即连接 | 改为懒加载，仅在实际上传时连接 |
| `relation "skills" does not exist` | `Skill` 模型未在 `__init__.py` 中导入 | 添加 `from app.models.skill import Skill` |
| Alembic 生成空迁移脚本 | 模型未被正确导入到 metadata | 修复 `__init__.py` 后重新生成 |
| `Can't locate revision` | 迁移脚本被删除但数据库记录还在 | 执行 `DROP TABLE alembic_version` |
| `FileNotFoundError: script.py.mako` | Alembic 模板文件缺失 | 手动创建 `alembic/script.py.mako` |
| `InvalidPasswordError` | 数据库密码不匹配 | 在服务器执行 `ALTER USER postgres WITH PASSWORD 'xxx'` |

---

## 七、后续开发建议

1. **WebSocket 实时进度**：在 `PlotBreakdown` 页面实现真正的拆解进度监听。
2. **文件上传测试**：验证 MinIO 隧道是否正常工作。
3. **个人设置页面**：目前仅有入口，需实现具体功能。
4. **Pydantic 警告修复**：`model_config_id` 字段与 Pydantic 保留命名空间冲突，可通过设置 `model_config['protected_namespaces'] = ()` 解决。

---

## 八、关键文件清单

```
jim/
├── frontend/
│   └── src/
│       ├── services/api.ts          # API 客户端
│       ├── context/AuthContext.tsx  # 认证状态管理
│       ├── components/
│       │   ├── MainLayout.tsx       # 主布局
│       │   └── ProtectedRoute.tsx   # 路由守卫
│       ├── pages/auth/
│       │   ├── Login.tsx            # 登录页
│       │   └── Register.tsx         # 注册页
│       └── App.tsx                  # 应用入口
│
└── backend/
    ├── .env                         # 环境配置
    ├── app/
    │   ├── core/storage.py          # MinIO 懒加载
    │   └── models/__init__.py       # 模型导入（含 Skill）
    └── alembic/
        ├── script.py.mako           # 迁移模板
        └── versions/                # 迁移脚本
```

---

## 九、认证流程说明

### 登录流程
1. 用户在 `Login.tsx` 输入用户名和密码
2. 前端调用 `AuthContext.login()` 方法
3. 发送 POST 请求到 `/api/v1/auth/login`（OAuth2 表单格式）
4. 后端验证成功后返回 JWT Token
5. 前端将 Token 存入 `localStorage`
6. 调用 `/api/v1/auth/me` 获取用户信息
7. 跳转到 Dashboard

### 请求鉴权流程
1. `api.ts` 拦截器自动从 `localStorage` 读取 Token
2. 在请求头添加 `Authorization: Bearer <token>`
3. 如果后端返回 401，自动清除 Token 并跳转登录页

### 路由保护流程
1. `ProtectedRoute` 组件检查 `AuthContext` 中的 Token
2. 如果 Token 不存在，重定向到 `/login`
3. 如果 Token 存在，渲染子路由

---

*记录时间：2026-02-03 20:30*

# WebSocket 直连后端方案

## 🎯 问题

Vite 代理无法正确转发 WebSocket 连接，即使添加了 `configure` 和 `upgrade` 监听。

## ✅ 解决方案

**绕过 Vite 代理，直接连接到后端**

### 已修改文件

#### 1. 环境变量配置

**文件**: `frontend/.env.development`

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

#### 2. WebSocket Hook

**文件**: `frontend/src/hooks/useWebSocket.ts`

**修改内容**:
```typescript
// 优先使用环境变量配置的 WebSocket URL（直接连接后端）
const wsBaseUrl = import.meta.env.VITE_WS_URL;

let wsUrl: string;
if (wsBaseUrl) {
  // 直接连接到后端（不通过 Vite 代理）
  wsUrl = url.startsWith('ws') ? url : `${wsBaseUrl}${url}`;
} else {
  // 通过 Vite 代理连接（降级方案）
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  wsUrl = url.startsWith('ws') ? url : `${protocol}//${host}${url}`;
}
```

## 🧪 验证步骤

### 步骤 1: 重启前端服务

**必须重启才能加载环境变量！**

```bash
cd frontend
# 完全停止（Ctrl+C）
npm run dev
```

### 步骤 2: 测试连接

1. **打开浏览器开发者工具**（F12）
2. **Console 标签**
3. **点击"开始拆解"**

**预期日志**:
```
[WebSocket] 连接到: ws://localhost:8000/api/v1/ws/breakdown/xxx-xxx-xxx
[WebSocket] 连接成功
[WebSocket] 连接到: ws://localhost:8000/api/v1/ws/breakdown-logs/xxx-xxx-xxx
[BreakdownLogs] WebSocket 打开
[BreakdownLogs] 已连接到日志流
```

**注意**: URL 现在是 `ws://localhost:8000`，不再是 `ws://localhost:5173`

### 步骤 3: 检查 Network

**Network → WS**:
- 应该看到两个连接到 `localhost:8000` 的 WebSocket
- 状态应该是 101 Switching Protocols（绿色）

## 🔍 对比

### 之前（通过 Vite 代理）

```
❌ ws://localhost:5173/api/v1/ws/breakdown/xxx
   ↓ (Vite 代理失败)
   ❌ 无法连接
```

### 现在（直接连接后端）

```
✅ ws://localhost:8000/api/v1/ws/breakdown/xxx
   ↓ (直接连接)
   ✅ 连接成功
```

## ⚠️ CORS 配置

直接连接后端需要确保后端允许跨域 WebSocket 连接。

**检查**: `backend/app/main.py`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # 前端地址
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**注意**: FastAPI 的 CORS 中间件会自动处理 WebSocket 的跨域请求。

## 🚀 优势

### 直接连接的好处

1. ✅ **更可靠** - 不依赖 Vite 代理
2. ✅ **更快** - 减少一层代理转发
3. ✅ **更简单** - 不需要复杂的代理配置
4. ✅ **更容易调试** - 直接看到后端地址

### 适用场景

- ✅ 开发环境（localhost）
- ✅ 测试环境
- ⚠️ 生产环境需要使用 Nginx 反向代理

## 📝 生产环境配置

生产环境应该使用 Nginx 反向代理：

**nginx.conf**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /var/www/frontend;
        try_files $uri $uri/ /index.html;
    }

    # API 和 WebSocket
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**生产环境变量** (`frontend/.env.production`):
```env
# 生产环境使用相对路径（通过 Nginx 代理）
VITE_API_URL=/api
VITE_WS_URL=
```

## 🔄 切换回 Vite 代理

如果将来想切换回 Vite 代理，只需：

1. 删除或注释 `.env.development` 中的 `VITE_WS_URL`
2. 重启前端服务

```env
# VITE_WS_URL=ws://localhost:8000  ← 注释掉
```

## ✅ 验证清单

- [ ] 前端服务已重启
- [ ] Console 显示连接到 `ws://localhost:8000`
- [ ] Console 显示 `[WebSocket] 连接成功`
- [ ] Network → WS 显示两个绿色连接
- [ ] 可以看到实时的任务进度
- [ ] 可以看到流式日志（如果后端发布）

## 🎉 预期效果

修复后，您应该看到：

1. **任务状态连接**:
   ```
   [WebSocket] 连接到: ws://localhost:8000/api/v1/ws/breakdown/xxx
   [WebSocket] 连接成功
   ```

2. **流式日志连接**:
   ```
   [WebSocket] 连接到: ws://localhost:8000/api/v1/ws/breakdown-logs/xxx
   [BreakdownLogs] WebSocket 打开
   [BreakdownLogs] 收到消息: connected
   ```

3. **Console 面板实时更新**:
   ```
   [12:00:00] 🚀 提取冲突
   [12:00:01] ▸ 正在分析第1章...
   [12:00:02] ▸ 发现冲突点1...
   [12:00:03] ✅ 提取冲突 完成
   ```

---

**方案**: 直接连接后端，绕过 Vite 代理
**修改**: `.env.development` + `useWebSocket.ts`
**状态**: ✅ 已实现，需要重启前端验证
**下一步**: 重启前端，测试 WebSocket 连接

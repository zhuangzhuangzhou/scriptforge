# WebSocket 问题诊断结果

## 🔍 问题诊断

### 测试结果

✅ **后端 WebSocket 端点正常**
- `/api/v1/ws/breakdown/{task_id}` - 连接成功
- `/api/v1/ws/breakdown-logs/{task_id}` - 连接成功

❌ **前端通过 Vite 代理连接失败**
- 错误: `[WebSocket] 连接错误: Event {type: 'error'}`
- 原因: Vite 代理配置不完整

## ✅ 解决方案

### 已修复内容

**文件**: `frontend/vite.config.ts`

**修改前**:
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    ws: true,
  },
}
```

**修改后**:
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    ws: true,
    configure: (proxy, _options) => {
      // 添加详细的代理日志
      proxy.on('error', (err, _req, _res) => {
        console.log('[Proxy] 错误:', err);
      });
      proxy.on('proxyReq', (proxyReq, req, _res) => {
        console.log('[Proxy] 发送请求:', req.method, req.url);
      });
      proxy.on('proxyRes', (proxyRes, req, _res) => {
        console.log('[Proxy] 收到响应:', proxyRes.statusCode, req.url);
      });
      proxy.on('upgrade', (req, socket, head) => {
        console.log('[Proxy] WebSocket 升级:', req.url);
      });
    },
  },
}
```

### 修改说明

添加了 `configure` 函数来：
1. 监听代理错误
2. 记录请求和响应
3. **监听 WebSocket 升级事件**（关键！）

## 🧪 验证步骤

### 步骤 1: 重启前端服务

**必须完全重启！**

```bash
cd frontend
# 完全停止（Ctrl+C）
# 清除缓存
rm -rf node_modules/.vite
# 重新启动
npm run dev
```

### 步骤 2: 测试 WebSocket 连接

1. **打开浏览器开发者工具**（F12）
2. **切换到 Console 标签**
3. **点击"开始拆解"**

**预期日志**:
```
[Proxy] 发送请求: GET /api/v1/breakdown/start
[Proxy] 收到响应: 200 /api/v1/breakdown/start
[Proxy] WebSocket 升级: /api/v1/ws/breakdown/xxx-xxx-xxx  ← 关键！
[WebSocket] 连接到: ws://localhost:5173/api/v1/ws/breakdown/xxx-xxx-xxx
[WebSocket] 连接成功
[Proxy] WebSocket 升级: /api/v1/ws/breakdown-logs/xxx-xxx-xxx  ← 关键！
[BreakdownLogs] WebSocket 打开
[BreakdownLogs] 已连接到日志流
```

4. **切换到 Network → WS 标签**

应该看到两个绿色的 WebSocket 连接：
- `/ws/breakdown/{task_id}` - 状态 101
- `/ws/breakdown-logs/{task_id}` - 状态 101

## 🔧 如果仍然失败

### 方案 1: 检查 Vite 版本

```bash
cd frontend
npm list vite
```

如果 Vite 版本过旧（< 4.0），可能不支持 WebSocket 代理。

**升级 Vite**:
```bash
npm install vite@latest --save-dev
```

### 方案 2: 使用环境变量配置

在 `frontend/.env.development` 中添加：
```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

然后修改前端代码，直接连接到后端（不通过代理）：

**修改 `useWebSocket.ts`**:
```typescript
const connect = useCallback(() => {
    if (!url) return;

    try {
      // 直接连接到后端（不通过 Vite 代理）
      const wsBaseUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
      const wsUrl = url.startsWith('ws') ? url : `${wsBaseUrl}${url}`;

      console.log(`[WebSocket] 连接到: ${wsUrl}`);
      const ws = new WebSocket(wsUrl);
      // ...
    }
}, [url, ...]);
```

### 方案 3: 使用 Nginx 反向代理

如果 Vite 代理始终有问题，可以使用 Nginx：

**nginx.conf**:
```nginx
server {
    listen 5173;

    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location / {
        proxy_pass http://localhost:5174;  # Vite 改到 5174
    }
}
```

## 📊 测试结果对比

### 直接连接后端（测试脚本）

```
✅ ws://localhost:8000/api/v1/ws/breakdown/xxx
✅ ws://localhost:8000/api/v1/ws/breakdown-logs/xxx
```

### 通过 Vite 代理（前端）

**修复前**:
```
❌ ws://localhost:5173/api/v1/ws/breakdown/xxx
❌ ws://localhost:5173/api/v1/ws/breakdown-logs/xxx
```

**修复后**（预期）:
```
✅ ws://localhost:5173/api/v1/ws/breakdown/xxx
✅ ws://localhost:5173/api/v1/ws/breakdown-logs/xxx
```

## 🎯 根本原因

Vite 的 WebSocket 代理需要正确处理 HTTP 升级（Upgrade）请求。虽然 `ws: true` 启用了 WebSocket 支持，但没有正确配置升级处理逻辑。

添加 `configure` 函数和 `upgrade` 事件监听器后，Vite 可以正确地：
1. 识别 WebSocket 升级请求
2. 将升级请求转发到后端
3. 维持 WebSocket 连接

## 📝 总结

### 问题
- 后端 WebSocket 端点正常
- Vite 代理配置不完整，无法正确转发 WebSocket 连接

### 解决方案
- 添加 `configure` 函数
- 监听 `upgrade` 事件
- 添加详细日志以便调试

### 验证
- 重启前端服务
- 查看 Console 日志中的 `[Proxy] WebSocket 升级` 消息
- 查看 Network → WS 中的连接状态

---

**诊断日期**: 2026-02-10
**问题**: Vite WebSocket 代理配置不完整
**解决**: 添加 configure 函数和 upgrade 事件监听
**状态**: 等待验证

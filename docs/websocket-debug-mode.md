# WebSocket 调试模式指南

## 🔧 已启用调试模式

为了方便调试 WebSocket 连接，已经**暂时禁用了降级轮询机制**。

### 修改内容

**文件**: `frontend/src/pages/user/Workspace/index.tsx`

#### 1. 禁用 useBreakdownWebSocket 的降级
```typescript
fallbackToPolling: false  // 🔧 调试模式：禁用降级轮询
```

#### 2. 注释掉轮询启动代码
```typescript
// 🔧 调试模式：暂时禁用降级轮询，以便调试 WebSocket
/*
useEffect(() => {
    if (usePolling && breakdownTaskId && selectedBatch) {
        console.log('[Polling] WebSocket 不可用，启动优化轮询机制');
        startOptimizedPolling(breakdownTaskId, selectedBatch.id);
    }
    ...
}, [usePolling, breakdownTaskId, selectedBatch]);
*/
```

## 🧪 调试步骤

### 步骤 1: 重启前端服务

**必须重启才能生效！**

```bash
cd frontend
# 停止当前服务（Ctrl+C）
npm run dev
```

### 步骤 2: 打开浏览器开发者工具

1. 按 `F12` 打开开发者工具
2. 切换到 **Console** 标签
3. 清空之前的日志（点击 🚫 图标）

### 步骤 3: 启动拆解任务

1. 点击"开始拆解"按钮
2. 选择配置
3. 点击"开始拆解"

### 步骤 4: 观察 WebSocket 连接

#### Console 标签

**成功的日志**:
```
[WebSocket] 连接到: ws://localhost:5173/api/v1/ws/breakdown/xxx-xxx-xxx
[WebSocket] 连接成功
[WebSocket] 连接到: ws://localhost:5173/api/v1/ws/breakdown-logs/xxx-xxx-xxx
[BreakdownLogs] WebSocket 打开
[BreakdownLogs] 已连接到日志流
```

**失败的日志**:
```
[WebSocket] 连接到: ws://localhost:5173/api/v1/ws/breakdown/xxx-xxx-xxx
[WebSocket] 连接错误: ...
[WebSocket] 连接失败，降级到轮询模式  ← 现在不会出现（已禁用）
```

#### Network 标签

1. 切换到 **Network** 标签
2. 筛选 **WS**（WebSocket）
3. 应该看到两个 WebSocket 连接：

| Name | Status | Type |
|------|--------|------|
| `breakdown/{task_id}` | 101 Switching Protocols | websocket |
| `breakdown-logs/{task_id}` | 101 Switching Protocols | websocket |

**如果状态不是 101**:
- 400 Bad Request - 请求格式错误
- 404 Not Found - 端点不存在
- 500 Internal Server Error - 后端错误
- 502 Bad Gateway - 代理配置错误

### 步骤 5: 查看 WebSocket 消息

1. 在 **Network → WS** 中点击某个 WebSocket 连接
2. 切换到 **Messages** 子标签
3. 查看实时消息流

**任务状态连接** (`/ws/breakdown/{task_id}`):
```json
{
  "task_id": "xxx-xxx-xxx",
  "status": "running",
  "progress": 10,
  "current_step": "正在分析章节内容..."
}
```

**流式日志连接** (`/ws/breakdown-logs/{task_id}`):
```json
{
  "type": "connected",
  "task_id": "xxx-xxx-xxx",
  "message": "已连接到任务日志流: xxx-xxx-xxx"
}
```

```json
{
  "type": "step_start",
  "task_id": "xxx-xxx-xxx",
  "step_name": "提取冲突",
  "content": "开始执行: 提取冲突"
}
```

```json
{
  "type": "stream_chunk",
  "task_id": "xxx-xxx-xxx",
  "step_name": "提取冲突",
  "content": "正在分析第1章的冲突点..."
}
```

## 🔍 常见问题诊断

### 问题 1: WebSocket 连接失败（状态 404）

**症状**:
```
[WebSocket] 连接错误: Error: Unexpected server response: 404
```

**原因**: 后端端点不存在或路由未注册

**检查**:
```bash
# 检查后端路由
curl http://localhost:8000/docs
# 查找 /ws/breakdown/{task_id} 和 /ws/breakdown-logs/{task_id}
```

**解决方案**:
确保后端 `app/api/v1/websocket.py` 已在 `app/main.py` 中注册：
```python
from app.api.v1 import websocket
app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])
```

### 问题 2: WebSocket 连接失败（状态 502）

**症状**:
```
[WebSocket] 连接错误: Error: Unexpected server response: 502
```

**原因**: Vite 代理配置问题或后端未运行

**检查**:
```bash
# 1. 检查后端是否运行
curl http://localhost:8000/api/v1/health

# 2. 检查 Vite 配置
cat frontend/vite.config.ts | grep -A 5 "proxy"
```

**解决方案**:
确保 `vite.config.ts` 包含 `ws: true`:
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    ws: true,  // ← 必须有
  },
}
```

### 问题 3: WebSocket 连接成功但无消息

**症状**:
- Console 显示 `[WebSocket] 连接成功`
- 但 Network → WS → Messages 中没有消息

**原因**: 后端未发送消息或任务未启动

**检查**:
```bash
# 查看后端日志
# 应该看到类似的日志：
# [WebSocket] 客户端连接: xxx-xxx-xxx
# [WebSocket] 发送消息: {...}
```

**解决方案**:
1. 检查任务是否真的在运行（查看 Celery Worker 日志）
2. 检查后端 WebSocket 端点是否正确发送消息

### 问题 4: 流式日志连接失败（Redis 不可用）

**症状**:
```json
{
  "type": "error",
  "content": "Redis 服务不可用，无法提供实时日志",
  "code": "REDIS_UNAVAILABLE"
}
```

**原因**: Redis 未运行

**解决方案**:
```bash
# 启动 Redis
redis-server

# 检查 Redis
redis-cli ping
# 应该返回 PONG
```

### 问题 5: 任务状态连接成功，但流式日志连接失败

**症状**:
- `/ws/breakdown/{task_id}` 连接成功
- `/ws/breakdown-logs/{task_id}` 连接失败或无消息

**原因**:
1. Redis 未运行
2. 后端未发布流式日志到 Redis

**检查**:
```bash
# 1. 检查 Redis
redis-cli ping

# 2. 监听 Redis 频道（调试用）
redis-cli
> PSUBSCRIBE breakdown:logs:*
# 然后启动任务，看是否有消息发布
```

**解决方案**:
确保后端在 Celery Worker 中调用了 `RedisLogPublisher`:
```python
from app.core.redis_log_publisher import RedisLogPublisher

publisher = RedisLogPublisher()
publisher.publish_stream_chunk(task_id, step_name, chunk)
```

## 📊 调试检查清单

### 前端检查

- [ ] 前端服务已重启
- [ ] `vite.config.ts` 包含 `ws: true`
- [ ] 浏览器控制台无 JavaScript 错误
- [ ] Network → WS 显示两个 WebSocket 连接
- [ ] WebSocket 状态为 101 Switching Protocols

### 后端检查

- [ ] 后端服务运行中（`http://localhost:8000`）
- [ ] WebSocket 路由已注册（查看 `/docs`）
- [ ] Redis 服务运行中（`redis-cli ping`）
- [ ] Celery Worker 运行中
- [ ] 后端日志无错误

### 连接检查

- [ ] 任务状态连接成功（`/ws/breakdown/{task_id}`）
- [ ] 流式日志连接成功（`/ws/breakdown-logs/{task_id}`）
- [ ] 任务状态连接有消息流
- [ ] 流式日志连接有消息流

## 🔄 恢复降级模式

调试完成后，记得恢复降级轮询功能：

### 1. 恢复 fallbackToPolling
```typescript
fallbackToPolling: true  // 恢复降级功能
```

### 2. 取消注释轮询代码
```typescript
// 恢复降级轮询
useEffect(() => {
    if (usePolling && breakdownTaskId && selectedBatch) {
        console.log('[Polling] WebSocket 不可用，启动优化轮询机制');
        startOptimizedPolling(breakdownTaskId, selectedBatch.id);
    }
    ...
}, [usePolling, breakdownTaskId, selectedBatch]);
```

### 3. 重启前端
```bash
cd frontend
npm run dev
```

## 💡 调试技巧

### 1. 使用 Chrome DevTools

**WebSocket 帧查看器**:
- Network → WS → 选择连接 → Frames 标签
- 可以看到每一帧的发送和接收时间

**WebSocket 状态**:
- 绿色 ↑ - 发送的消息
- 绿色 ↓ - 接收的消息
- 红色 - 错误

### 2. 添加详细日志

在 `useBreakdownLogs.ts` 中添加更多日志：
```typescript
onMessage: (data) => {
    console.log('[BreakdownLogs] 原始消息:', data);
    // ...
}
```

### 3. 使用 WebSocket 测试工具

**在线工具**: https://www.websocket.org/echo.html

**测试 URL**:
```
ws://localhost:8000/api/v1/ws/breakdown-logs/test-task-id
```

### 4. 监听 Redis 频道

```bash
redis-cli
> PSUBSCRIBE breakdown:logs:*
# 查看是否有消息发布
```

## 📝 调试日志模板

记录调试信息时使用以下模板：

```
### 环境信息
- 前端: http://localhost:5173
- 后端: http://localhost:8000
- Redis: 运行中 / 未运行
- Celery Worker: 运行中 / 未运行

### WebSocket 连接状态
- 任务状态连接: 成功 / 失败 (状态码: ___)
- 流式日志连接: 成功 / 失败 (状态码: ___)

### 错误信息
- Console 错误: ___
- Network 错误: ___
- 后端日志: ___

### 已尝试的解决方案
1. ___
2. ___
3. ___
```

---

**调试模式启用日期**: 2026-02-10
**修改文件**: `frontend/src/pages/user/Workspace/index.tsx`
**恢复方法**: 见上文"恢复降级模式"部分

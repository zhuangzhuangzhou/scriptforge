# WebSocket 连接修复验证指南

## 🎯 问题已修复

**问题**: Vite 配置缺少 `ws: true`，导致 WebSocket 连接无法通过代理

**修复**: 在 `frontend/vite.config.ts` 中添加了 `ws: true` 配置

## 📝 修复内容

### 修改文件
`frontend/vite.config.ts`

### 修改前
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
}
```

### 修改后
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    ws: true, // ✅ 启用 WebSocket 代理
  },
}
```

## 🧪 验证步骤

### 步骤 1: 重启前端开发服务器

**重要**: 修改 Vite 配置后必须重启开发服务器

```bash
# 停止当前运行的前端服务（Ctrl+C）
# 然后重新启动
cd frontend
npm run dev
```

### 步骤 2: 确保后端服务运行

```bash
# 在另一个终端窗口
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 步骤 3: 浏览器测试

1. **打开浏览器开发者工具**
   - 按 `F12` 或右键 → 检查

2. **切换到 Console 标签**
   - 清空之前的日志（点击 🚫 图标）

3. **打开剧集拆解页面**
   - 导航到项目详情页
   - 点击"剧情拆解"标签

4. **点击"开始拆解"按钮**
   - 选择配置
   - 点击"开始拆解"

5. **查看 Console 日志**

   **✅ 成功的日志应该包含**:
   ```
   [WebSocket] 连接到: ws://localhost:5173/api/v1/ws/breakdown/xxx-xxx-xxx
   [WebSocket] 连接成功
   ```

   **❌ 如果失败，可能看到**:
   ```
   [WebSocket] 连接错误: ...
   [WebSocket] 连接失败，降级到轮询模式
   [Polling] WebSocket 不可用，启动优化轮询机制
   ```

6. **切换到 Network 标签**
   - 筛选 **WS**（WebSocket）
   - 应该看到一个 WebSocket 连接
   - 状态应该是 **101 Switching Protocols**（绿色）

7. **观察实时进度**
   - Console 面板应该自动弹出
   - 应该看到实时的步骤日志
   - 进度条应该实时更新

### 步骤 4: 验证 WebSocket 消息

在 **Network → WS** 标签中：

1. 点击 WebSocket 连接
2. 切换到 **Messages** 子标签
3. 应该看到实时的消息流：

```json
{
  "task_id": "xxx-xxx-xxx",
  "status": "running",
  "progress": 10,
  "current_step": "正在分析章节内容..."
}
```

```json
{
  "task_id": "xxx-xxx-xxx",
  "status": "running",
  "progress": 50,
  "current_step": "正在提取冲突点..."
}
```

```json
{
  "task_id": "xxx-xxx-xxx",
  "status": "done",
  "final_status": "completed",
  "message": "任务已完成"
}
```

## 🔍 故障排查

### 问题 1: 仍然没有 WebSocket 连接

**可能原因**:
- 前端服务未重启
- 后端服务未启动
- 端口冲突

**解决方案**:
```bash
# 1. 完全停止前端服务
# 按 Ctrl+C

# 2. 清除缓存并重启
cd frontend
rm -rf node_modules/.vite
npm run dev

# 3. 检查后端服务
curl http://localhost:8000/api/v1/health
```

### 问题 2: WebSocket 连接后立即断开

**可能原因**:
- 任务不存在
- 后端 WebSocket 端点错误

**解决方案**:
```bash
# 检查后端日志
# 查看是否有错误信息

# 检查任务是否创建成功
# 在 Network 标签中查看 /api/v1/breakdown/start 的响应
```

### 问题 3: 降级到轮询模式

**症状**: 看到 `[Polling] WebSocket 不可用，启动优化轮询机制`

**说明**: 这是正常的降级机制，功能仍然可用，只是不是实时的

**如果想强制使用 WebSocket**:
1. 检查浏览器控制台的错误信息
2. 检查后端日志
3. 确认 WebSocket 端点可访问

### 问题 4: CORS 错误

**症状**: 控制台显示 CORS 相关错误

**解决方案**:
检查后端 CORS 配置（`backend/app/main.py`）:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## ✅ 成功标志

当一切正常时，您应该看到：

1. ✅ Console 中有 `[WebSocket] 连接成功` 日志
2. ✅ Network → WS 中有绿色的 WebSocket 连接
3. ✅ Console 面板自动弹出并显示实时日志
4. ✅ 进度条实时更新
5. ✅ 任务完成后自动刷新结果

## 📊 性能对比

### WebSocket 模式（推荐）
- ✅ 实时推送，延迟 < 100ms
- ✅ 服务器主动推送，无需轮询
- ✅ 资源占用低
- ✅ 用户体验好

### 轮询模式（降级方案）
- ⚠️ 延迟 1-3 秒
- ⚠️ 客户端主动请求
- ⚠️ 资源占用较高
- ⚠️ 用户体验一般

## 🎉 总结

修复后，剧集拆解功能应该：
1. 点击"开始拆解"后立即建立 WebSocket 连接
2. 实时显示拆解进度和步骤
3. 任务完成后自动刷新结果
4. 如果 WebSocket 失败，自动降级到轮询模式

如果仍有问题，请查看：
- 浏览器控制台的完整错误信息
- 后端服务的日志输出
- Network 标签中的请求详情

---

**修复日期**: 2026-02-10
**修复内容**: 添加 `ws: true` 到 Vite 代理配置
**影响范围**: 所有 WebSocket 连接（剧集拆解、剧本生成等）

# 剧集拆解 WebSocket 连接问题诊断报告

## 问题描述

用户反馈：点击"开始拆解"按钮后，没有建立 WebSocket 连接。

## 问题分析

### 1. 代码流程检查

经过详细的代码审查，发现 WebSocket 连接逻辑是**完整且正确**的：

#### 流程图
```
用户点击"开始拆解"
    ↓
handleStartBreakdownClick(batchId)
    ↓
打开配置弹窗 (setIsBreakdownModalOpen(true))
    ↓
用户选择配置并点击"开始拆解"
    ↓
handleConfirmBreakdown()
    ↓
调用 API: breakdownApi.startBreakdown()
    ↓
获取 task_id
    ↓
setBreakdownTaskId(res.data.task_id)  ← 关键步骤
    ↓
useBreakdownWebSocket 检测到 breakdownTaskId 变化
    ↓
useWebSocket 自动连接到 /api/v1/ws/breakdown/{taskId}
    ↓
开始接收实时进度
```

#### 关键代码位置

**1. 按钮点击处理** (`frontend/src/pages/user/Workspace/index.tsx:656-660`)
```tsx
const handleStartBreakdownClick = (batchId: string) => {
    setTargetBatchId(batchId);
    setIsBreakdownModalOpen(true);
};
```

**2. 确认启动拆解** (`frontend/src/pages/user/Workspace/index.tsx:663-689`)
```tsx
const handleConfirmBreakdown = async () => {
    if (!targetBatchId) return;
    setIsBreakdownModalOpen(false);

    try {
        setShowConsole(true);
        clearLogs();
        lastStepRef.current = '';
        addLog('info', `配置已应用，开始拆解批次 ${selectedBatch?.batch_number || ''}...`);

        const res = await breakdownApi.startBreakdown(targetBatchId, {
            selectedSkills: selectedBreakdownSkills,
            adaptMethodKey: breakdownConfig.adaptMethodKey,
            qualityRuleKey: breakdownConfig.qualityRuleKey,
            outputStyleKey: breakdownConfig.outputStyleKey
        });
        setBreakdownTaskId(res.data.task_id);  // ← 设置 task_id
        message.info('拆解任务已启动');

        // WebSocket 会自动连接，如果失败会降级到轮询
    } catch (err: any) {
        const errorMsg = err.response?.data?.detail || '启动拆解失败';
        message.error(errorMsg);
        showError({ code: 'START_FAILED', message: errorMsg });
    }
};
```

**3. WebSocket Hook** (`frontend/src/pages/user/Workspace/index.tsx:212-239`)
```tsx
const { isConnected: wsConnected, progress: wsProgress, currentStep: wsCurrentStep, usePolling } = useBreakdownWebSocket(
    breakdownTaskId,  // ← 依赖这个状态
    {
        onProgress: (data) => {
            setBreakdownProgress(data.progress || 0);
            if (data.current_step && data.current_step !== lastStepRef.current) {
                addLog('thinking', data.current_step);
                lastStepRef.current = data.current_step;
            }
        },
        onComplete: () => {
            setBreakdownTaskId(null);
            message.success('拆解完成');
            if (selectedBatch) {
                fetchBreakdownResults(selectedBatch.id);
            }
            fetchBatches();
        },
        onError: (error) => {
            setBreakdownTaskId(null);
            const parsedError = parseErrorMessage(error);
            showError(parsedError);
        },
        fallbackToPolling: true
    }
);
```

**4. WebSocket URL 构建** (`frontend/src/hooks/useBreakdownWebSocket.ts:51`)
```tsx
const wsUrl = taskId ? `/api/v1/ws/breakdown/${taskId}` : null;
```

**5. 自动连接逻辑** (`frontend/src/hooks/useWebSocket.ts:121-129`)
```tsx
useEffect(() => {
    if (url) {
        connect();  // ← 当 url 变化时自动连接
    }

    return () => {
        disconnect();
    };
}, [url, connect, disconnect]);
```

### 2. 可能的问题原因

虽然代码逻辑正确，但可能存在以下问题：

#### 问题 1: API 调用失败
**症状**: `breakdownApi.startBreakdown()` 调用失败，没有返回 `task_id`

**原因**:
- 后端服务未启动
- API 端点错误
- 请求参数错误
- 权限问题

**验证方法**:
```javascript
// 在浏览器控制台查看
// 1. 打开 Network 标签
// 2. 点击"开始拆解"
// 3. 查看 /api/v1/breakdown/start 请求
// 4. 检查响应状态码和响应体
```

#### 问题 2: task_id 未正确设置
**症状**: API 调用成功，但 `breakdownTaskId` 状态未更新

**原因**:
- 响应数据结构不匹配（`res.data.task_id` 不存在）
- React 状态更新异步问题

**验证方法**:
```javascript
// 在 handleConfirmBreakdown 中添加日志
console.log('API 响应:', res);
console.log('task_id:', res.data.task_id);
```

#### 问题 3: WebSocket 连接失败
**症状**: `breakdownTaskId` 已设置，但 WebSocket 连接失败

**原因**:
- WebSocket 端点不可用
- CORS 问题
- 代理配置问题
- 任务不存在（task_id 无效）

**验证方法**:
```javascript
// 在浏览器控制台查看
// 1. 打开 Console 标签
// 2. 查找 "[WebSocket] 连接到:" 日志
// 3. 查看是否有连接错误
```

#### 问题 4: 降级到轮询但未生效
**症状**: WebSocket 连接失败，但轮询也没有启动

**原因**:
- `usePolling` 状态未正确设置
- `startOptimizedPolling` 未被调用

**验证方法**:
```javascript
// 在浏览器控制台查看
// 查找 "[Polling] WebSocket 不可用，启动优化轮询机制" 日志
```

### 3. 前端代理配置检查

WebSocket 连接需要正确的代理配置。让我检查 Vite 配置：

**需要检查的文件**: `frontend/vite.config.ts`

**正确的配置应该包含**:
```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,  // ← 关键：启用 WebSocket 代理
      }
    }
  }
})
```

## 诊断步骤

### 步骤 1: 检查后端服务
```bash
# 检查后端是否运行
curl http://localhost:8000/api/v1/health

# 检查 WebSocket 端点是否注册
curl http://localhost:8000/docs
# 查找 /ws/breakdown/{task_id} 端点
```

### 步骤 2: 检查前端代理配置
```bash
# 查看 vite.config.ts
cat frontend/vite.config.ts | grep -A 10 "proxy"
```

### 步骤 3: 浏览器控制台诊断
1. 打开浏览器开发者工具（F12）
2. 切换到 **Console** 标签
3. 点击"开始拆解"按钮
4. 查看日志输出：
   - `[WebSocket] 连接到: ws://...` - 应该出现
   - `[WebSocket] 连接成功` - 应该出现
   - 如果没有出现，查看错误信息

5. 切换到 **Network** 标签
6. 筛选 **WS**（WebSocket）
7. 查看是否有 WebSocket 连接请求
8. 检查连接状态（101 Switching Protocols = 成功）

### 步骤 4: 检查 API 响应
1. 在 **Network** 标签中
2. 筛选 **XHR**
3. 找到 `/api/v1/breakdown/start` 请求
4. 查看响应：
   ```json
   {
     "task_id": "uuid-here",
     "status": "queued"
   }
   ```
5. 确认 `task_id` 存在

## 修复方案

### 方案 1: 添加详细日志（推荐先做）

在 `handleConfirmBreakdown` 中添加日志：

```tsx
const handleConfirmBreakdown = async () => {
    if (!targetBatchId) return;
    setIsBreakdownModalOpen(false);

    try {
        setShowConsole(true);
        clearLogs();
        lastStepRef.current = '';
        addLog('info', `配置已应用，开始拆解批次 ${selectedBatch?.batch_number || ''}...`);

        console.log('[DEBUG] 开始调用 API，batchId:', targetBatchId);
        const res = await breakdownApi.startBreakdown(targetBatchId, {
            selectedSkills: selectedBreakdownSkills,
            adaptMethodKey: breakdownConfig.adaptMethodKey,
            qualityRuleKey: breakdownConfig.qualityRuleKey,
            outputStyleKey: breakdownConfig.outputStyleKey
        });

        console.log('[DEBUG] API 响应:', res);
        console.log('[DEBUG] task_id:', res.data.task_id);

        setBreakdownTaskId(res.data.task_id);
        console.log('[DEBUG] breakdownTaskId 已设置:', res.data.task_id);

        message.info('拆解任务已启动');

        // WebSocket 会自动连接，如果失败会降级到轮询
    } catch (err: any) {
        console.error('[DEBUG] API 调用失败:', err);
        const errorMsg = err.response?.data?.detail || '启动拆解失败';
        message.error(errorMsg);
        showError({ code: 'START_FAILED', message: errorMsg });
    }
};
```

### 方案 2: 检查并修复 Vite 配置

确保 `frontend/vite.config.ts` 包含 WebSocket 代理配置：

```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,  // ← 必须启用
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('proxy error', err);
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('Sending Request to the Target:', req.method, req.url);
          });
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            console.log('Received Response from the Target:', proxyRes.statusCode, req.url);
          });
        },
      }
    }
  }
})
```

### 方案 3: 添加 WebSocket 连接状态显示

在 UI 中显示 WebSocket 连接状态：

```tsx
// 在 Console 组件中添加
{wsConnected && (
    <div className="text-xs text-green-500">
        ✅ WebSocket 已连接
    </div>
)}
{!wsConnected && breakdownTaskId && (
    <div className="text-xs text-yellow-500">
        ⚠️ WebSocket 未连接，使用轮询模式
    </div>
)}
```

### 方案 4: 强制使用轮询模式（临时方案）

如果 WebSocket 始终无法连接，可以临时强制使用轮询：

```tsx
const { isConnected: wsConnected, progress: wsProgress, currentStep: wsCurrentStep, usePolling } = useBreakdownWebSocket(
    breakdownTaskId,
    {
        onProgress: (data) => { /* ... */ },
        onComplete: () => { /* ... */ },
        onError: (error) => { /* ... */ },
        fallbackToPolling: true  // ← 已启用
    }
);

// 在 useEffect 中强制启动轮询
useEffect(() => {
    if (breakdownTaskId && selectedBatch) {
        console.log('[Polling] 强制启动轮询机制');
        startOptimizedPolling(breakdownTaskId, selectedBatch.id);
    }

    return () => {
        if (pollingIntervalRef.current) {
            clearTimeout(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
        }
    };
}, [breakdownTaskId, selectedBatch]);
```

## 总结

**代码逻辑是正确的**，WebSocket 应该会自动连接。问题可能出在：

1. ❌ 后端服务未启动或 WebSocket 端点不可用
2. ❌ 前端代理配置缺少 `ws: true`
3. ❌ API 调用失败，未返回 `task_id`
4. ❌ 浏览器控制台有错误但未被注意到

**建议的诊断顺序**：
1. 先添加详细日志（方案 1）
2. 在浏览器控制台查看日志
3. 检查 Vite 配置（方案 2）
4. 如果仍有问题，添加连接状态显示（方案 3）
5. 最后考虑强制轮询（方案 4）

**最可能的原因**：前端代理配置缺少 `ws: true`

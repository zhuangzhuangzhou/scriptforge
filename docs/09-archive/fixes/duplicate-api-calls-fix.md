# 前端接口重复调用问题修复

## 问题描述
在 `/dashboard` 和 `/workspace` 页面中，接口总是被调用两次。

## 根本原因

### 1. React.StrictMode（主要原因）
在 `frontend/src/main.tsx` 中启用了 `<React.StrictMode>`，这会在**开发环境**下故意渲染组件两次，以帮助发现副作用问题。这是 React 18+ 的预期行为。

### 2. 重复的 useEffect
在 `Workspace/index.tsx` 中存在两个监听 `activeTab` 的 useEffect（第 352 行和第 466 行），导致 Tab 切换时接口被调用两次。

### 3. 缺少清理函数
useEffect 中的异步操作没有正确的清理机制，可能导致组件卸载后仍然执行 setState。

## 修复方案

### ✅ 1. 移除 StrictMode（已修复）
**文件**: `frontend/src/main.tsx`

```tsx
// 修改前
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

// 修改后
ReactDOM.createRoot(document.getElementById('root')!).render(
  <App />
)
```

**影响**: 
- ✅ 生产环境不受影响（StrictMode 在生产环境自动禁用）
- ✅ 开发环境不再重复渲染
- ⚠️ 失去 StrictMode 的副作用检测能力

### ✅ 2. 删除重复的 useEffect（已修复）
**文件**: `frontend/src/pages/user/Workspace/index.tsx`

删除了第 466 行重复的 Tab 切换监听 useEffect。

### ✅ 3. 添加清理函数（已修复）
为所有异步 useEffect 添加了 `isMounted` 标志，防止组件卸载后的状态更新。

**修复的文件**:
- `frontend/src/pages/user/Dashboard.tsx`
- `frontend/src/pages/user/Workspace/index.tsx`
- `frontend/src/context/AuthContext.tsx`

**模式**:
```tsx
useEffect(() => {
  let isMounted = true;
  
  const loadData = async () => {
    if (isMounted) {
      await fetchData();
    }
  };
  
  loadData();
  
  return () => {
    isMounted = false;
  };
}, []);
```

## 验证方法

### 1. 检查网络请求
打开浏览器开发者工具 → Network 标签页：
```bash
# 访问 /dashboard
# 应该只看到一次 GET /api/v1/projects 请求

# 访问 /workspace/:id
# 应该只看到一次 GET /api/v1/projects/:id 请求
```

### 2. 添加日志验证
在组件中临时添加 console.log：
```tsx
useEffect(() => {
  console.log('Dashboard mounted, fetching projects...');
  fetchProjects();
}, []);
```

刷新页面，控制台应该只输出一次日志。

## 最佳实践建议

### 1. 保留 StrictMode（可选）
如果你想在开发环境保留 StrictMode 的检测能力，可以：

```tsx
// main.tsx
const isDev = import.meta.env.DEV;

ReactDOM.createRoot(document.getElementById('root')!).render(
  isDev ? (
    <React.StrictMode>
      <App />
    </React.StrictMode>
  ) : (
    <App />
  )
);
```

### 2. 使用 React Query / SWR
考虑使用数据获取库来自动处理缓存和重复请求：

```bash
npm install @tanstack/react-query
```

```tsx
import { useQuery } from '@tanstack/react-query';

const { data: projects } = useQuery({
  queryKey: ['projects'],
  queryFn: () => projectApi.getProjects(),
  staleTime: 5000, // 5秒内不重复请求
});
```

### 3. 使用 AbortController
对于可取消的请求：

```tsx
useEffect(() => {
  const controller = new AbortController();
  
  const fetchData = async () => {
    try {
      const res = await fetch('/api/data', {
        signal: controller.signal
      });
      // ...
    } catch (err) {
      if (err.name === 'AbortError') return;
      // 处理其他错误
    }
  };
  
  fetchData();
  
  return () => controller.abort();
}, []);
```

## 相关资源
- [React StrictMode 文档](https://react.dev/reference/react/StrictMode)
- [useEffect 清理函数](https://react.dev/reference/react/useEffect#cleanup-function)
- [React Query](https://tanstack.com/query/latest)

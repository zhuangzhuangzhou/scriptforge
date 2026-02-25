# 剧集拆解进度显示和按钮状态修复

## 目标
修复 Workspace 页面中剧集拆解(Plot)功能的两个关键问题，确保进度显示准确且操作按钮状态正确。

## 问题描述

### 问题 1: 拆解进度数据不准确
- **现象**: 页面上方显示 "20/167"，但实际已拆解 90 个批次
- **根本原因**: 前端直接从 `batches` 数组过滤计算进度，但该数组是分页加载的（每次只加载 20 条），无法反映全部批次的真实状态
- **影响**: 用户无法准确了解项目的真实进度

### 问题 2: 全部拆解/继续拆解按钮被禁用
- **现象**: 按钮处于禁用状态，无法发起全部拆解操作
- **根本原因**: 按钮禁用条件依赖 `batches` 数组过滤结果，由于分页加载，数组中可能不包含所有待拆解批次
- **影响**: 用户无法继续拆解剩余批次

## 需求

### 功能需求
1. 页面顶部的拆解进度显示必须反映**全部批次**的真实状态
2. 全部拆解/继续拆解按钮的禁用逻辑必须基于**全部批次**的状态，而非当前页的批次

### 技术需求
1. 使用后端 API `/breakdown/batch-progress/{projectId}` 获取全局进度数据
2. 在组件加载和批次列表刷新时同步更新全局进度
3. 按钮禁用条件改为基于 API 返回的统计数据

## 验收标准

- [ ] 页面顶部显示的拆解进度数字准确（completed/total_batches）
- [ ] 进度条百分比准确反映整体进度
- [ ] 当存在待拆解或失败的批次时，全部拆解/继续拆解按钮可用
- [ ] 当所有批次都已完成时，按钮正确禁用
- [ ] 批次列表刷新后，全局进度同步更新
- [ ] 不影响现有的批次列表分页加载功能

## 技术方案

### 1. 添加全局进度状态
```tsx
const [batchProgress, setBatchProgress] = useState<{
  total_batches: number;
  completed: number;
  in_progress: number;
  pending: number;
  failed: number;
  overall_progress: number;
} | null>(null);
```

### 2. 在组件加载时获取全局进度
```tsx
useEffect(() => {
  if (projectId && activeTab === 'PLOT') {
    fetchGlobalProgress();
  }
}, [projectId, activeTab]);

const fetchGlobalProgress = async () => {
  try {
    const res = await breakdownApi.getBatchProgress(projectId);
    setBatchProgress(res.data);
  } catch (err) {
    console.error('获取全局进度失败:', err);
  }
};
```

### 3. 修改进度显示逻辑
```tsx
// 使用 batchProgress 而不是 batches 数组
<span>
  {batchProgress?.completed || 0}/{batchProgress?.total_batches || batchTotal}
</span>
<div style={{
  width: `${batchProgress?.overall_progress || 0}} />
```

### 4. 修改按钮禁用条件
```tsx
const hasPendingBatches = (batchProgress?.pending || 0) + (batchProgress?.failed || 0) > 0;

disabled={
  !!breakdownTaskId ||
  isAllBreakdownRunning ||
  isBatchRunning ||
  !hasPendingBatches
}
```

### 5. 在批次列表刷新后同步更新全局进度
```tsx
const fetchBatches = async () => {
  // ... 现有逻辑
  await fetchGlobalProgress(); // 同步更新全局进度
};
```

## 影响范围

### 修改文件
- `frontend/src/pages/user/Workspace/index.tsx` - 主要修改文件

### 不影响
- 后端 API（已正确实现，无需修改）
- 批次列表的分页加载逻辑
- 其他标签页的功能

## 技术注意事项

1. **避免重复调用**: 使用 `useEffect` 依赖数组控制 API 调用时机
2. **错误处理**: API 调用失败时使用降级显示（显示 0 或使用 batchTotal）
3. **性能优化**: 只在必要时刷新全局进度（组件加载、批次列表刷新、批次状态变化）
4. **状态同步**: 确保 WebSocket 收到批次状态变化消息时也更新全局进度

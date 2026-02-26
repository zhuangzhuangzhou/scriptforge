# React Hooks 最佳实践

## 概述

本文档记录 React Hooks 使用中的常见陷阱和最佳实践。

---

## Common Mistake: 异步回调中的闭包陷阱

### 症状
异步回调函数中使用的 state 变量总是旧值,即使 state 已经更新。

### 示例场景
WebSocket 消息回调中需要使用最新的批次列表:

```typescript
// ❌ 错误: 闭包陷阱
const [batches, setBatches] = useState([]);

const { ... } = useBreakdownWebSocket(taskId, {
    onBatchSwitch: async (switchInfo) => {
        // 问题: 这里的 batches 是创建回调时的值,不是最新值
        const newBatch = batches.find(b => b.id === switchInfo.newBatchId);
        // 如果 batches 在回调创建后更新了,这里仍然是旧值
    }
});
```

### 原因
JavaScript 闭包机制: 回调函数捕获的是创建时的变量值,不会自动更新。

```typescript
// 回调创建时 batches = [batch1, batch2]
const callback = () => {
    console.log(batches);  // 永远是 [batch1, batch2]
};

// 即使后来更新了 batches
setBatches([batch1, batch2, batch3]);

// 回调中的 batches 仍然是旧值
callback();  // 输出: [batch1, batch2]
```

### 修复方案 1: 直接调用 API (推荐)

```typescript
// ✅ 正确: 直接调用 API 获取最新数据
const { ... } = useBreakdownWebSocket(taskId, {
    onBatchSwitch: async (switchInfo) => {
        // 直接调用 API,不依赖闭包变量
        const res = await projectApi.getBatches(projectId!, 1, 20);
        const freshBatches = res.data?.items || [];
        setBatches(freshBatches);

        // 使用刚获取的最新数据
        const newBatch = freshBatches.find(b => b.id === switchInfo.newBatchId);
        if (newBatch) {
            setSelectedBatch(newBatch);
        }
    }
});
```

### 修复方案 2: 使用 useRef

```typescript
// ✅ 正确: 使用 ref 保存最新值
const [batches, setBatches] = useState([]);
const batchesRef = useRef(batches);

// 每次 batches 更新时同步到 ref
useEffect(() => {
    batchesRef.current = batches;
}, [batches]);

const { ... } = useBreakdownWebSocket(taskId, {
    onBatchSwitch: async (switchInfo) => {
        // 使用 ref.current 获取最新值
        const newBatch = batchesRef.current.find(b => b.id === switchInfo.newBatchId);
    }
});
```

### 修复方案 3: 使用函数式更新

```typescript
// ✅ 正确: 使用函数式 setState
const { ... } = useBreakdownWebSocket(taskId, {
    onBatchSwitch: async (switchInfo) => {
        // 使用函数式更新,可以访问最新的 state
        setBatches(prevBatches => {
            const newBatch = prevBatches.find(b => b.id === switchInfo.newBatchId);
            // ... 处理逻辑
            return prevBatches;
        });
    }
});
```

### 最佳实践

**优先级排序**:
1. **直接调用 API** (最可靠,数据最新)
2. **使用 useRef** (适合只读场景)
3. **函数式更新** (适合需要基于旧值计算新值的场景)

**避免**:
- ❌ 直接在回调中使用 state 变量
- ❌ 依赖 useEffect 的依赖数组来"刷新"回调

---

## Pattern: Custom Hook 回调设计

### 问题
Custom Hook 提供回调接口时,如何避免闭包陷阱?

### 解决方案: 提供必要的上下文

```typescript
// ❌ 不好: 回调参数不足,强迫用户使用闭包变量
interface UseBreakdownLogsOptions {
    onBatchSwitch?: (batchNumber: number) => void;
}

// 用户被迫这样用:
const [batches, setBatches] = useState([]);
useBreakdownWebSocket(taskId, {
    onBatchSwitch: (batchNumber) => {
        // 必须使用闭包变量 batches (可能是旧值)
        const batch = batches.find(b => b.batch_number === batchNumber);
    }
});

// ✅ 好: 回调参数包含所有必要信息
interface UseBreakdownLogsOptions {
    onBatchSwitch?: (info: {
        newTaskId: string;
        newBatchId: string;
        newBatchNumber: number;
    }) => void;
}

// 用户可以直接使用回调参数:
useBreakdownWebSocket(taskId, {
    onBatchSwitch: async (switchInfo) => {
        // 所有信息都在参数中,不需要闭包变量
        const res = await api.getBatch(switchInfo.newBatchId);
        setSelectedBatch(res.data);
    }
});
```

### 为什么这样做?

- 减少对闭包变量的依赖
- 回调参数自包含,更容易理解
- 避免用户犯闭包陷阱的错误

---

## Pattern: 依赖数组管理

### 问题
useEffect/useCallback 的依赖数组应该包含哪些变量?

### 规则

```typescript
// ✅ 规则 1: 包含所有使用的外部变量
useEffect(() => {
    if (projectId) {
        fetchProject(projectId);  // 使用了 projectId 和 fetchProject
    }
}, [projectId, fetchProject]);  // 都要包含

// ✅ 规则 2: 函数依赖用 useCallback 包裹
const fetchProject = useCallback(async (id: string) => {
    const res = await api.getProject(id);
    setProject(res.data);
}, []);  // 如果函数内部没有依赖,可以是空数组

// ✅ 规则 3: 如果依赖太多,考虑拆分 effect
useEffect(() => {
    // 逻辑 A: 依赖 projectId
    if (projectId) {
        fetchProject(projectId);
    }
}, [projectId]);

useEffect(() => {
    // 逻辑 B: 依赖 batchId
    if (batchId) {
        fetchBatch(batchId);
    }
}, [batchId]);
```

### 常见错误

```typescript
// ❌ 错误 1: 遗漏依赖
useEffect(() => {
    console.log(count);  // 使用了 count
}, []);  // 但依赖数组是空的

// ❌ 错误 2: 不必要的依赖
useEffect(() => {
    fetchData();
}, [fetchData]);  // fetchData 每次渲染都是新函数,导致无限循环

// ✅ 正确: 用 useCallback 稳定函数引用
const fetchData = useCallback(() => {
    // ...
}, []);

useEffect(() => {
    fetchData();
}, [fetchData]);  // 现在 fetchData 引用稳定了
```

---

## Pattern: 避免过度渲染

### 问题
组件频繁重新渲染,影响性能。

### 解决方案 1: useMemo 缓存计算结果

```typescript
// ❌ 不好: 每次渲染都重新计算
const filteredBatches = batches.filter(b => b.status === 'completed');

// ✅ 好: 只在 batches 变化时重新计算
const filteredBatches = useMemo(
    () => batches.filter(b => b.status === 'completed'),
    [batches]
);
```

### 解决方案 2: useCallback 缓存函数

```typescript
// ❌ 不好: 每次渲染都创建新函数
const handleClick = () => {
    console.log('clicked');
};

// ✅ 好: 函数引用稳定
const handleClick = useCallback(() => {
    console.log('clicked');
}, []);
```

### 解决方案 3: React.memo 避免子组件重渲染

```typescript
// ❌ 不好: 父组件渲染时,子组件总是重渲染
const BatchCard = ({ batch }) => {
    return <div>{batch.name}</div>;
};

// ✅ 好: 只在 props 变化时重渲染
const BatchCard = React.memo(({ batch }) => {
    return <div>{batch.name}</div>;
});
```

---

## Gotcha: useEffect 清理函数

> **Warning**: useEffect 的清理函数会在组件卸载或依赖变化时执行。
>
> 常见错误: 忘记清理定时器、WebSocket 连接等资源。

```typescript
// ❌ 错误: 没有清理定时器
useEffect(() => {
    const timer = setInterval(() => {
        fetchData();
    }, 5000);
    // 组件卸载时定时器仍在运行,导致内存泄漏
}, []);

// ✅ 正确: 清理定时器
useEffect(() => {
    const timer = setInterval(() => {
        fetchData();
    }, 5000);

    return () => {
        clearInterval(timer);  // 清理函数
    };
}, []);
```

---

## Pattern: 双数据源进度合并

### 问题
同时使用 WebSocket（实时）和 HTTP 轮询获取进度时，两个数据源可能产生冲突，导致进度显示被重置。

### 场景
```typescript
// 场景: Script 生成页面
// - useScriptPolling: HTTP 轮询获取进度（启动任务后立即开始）
// - useConsoleLogger: WebSocket 连接获取实时日志和进度

// ❌ 错误: 直接使用单一数据源
const { progress } = useScriptPolling(...);  // 启动时有值
const { progress: wsProgress } = useConsoleLogger(...);  // WebSocket 连接后覆盖

// 问题: WebSocket 连接成功后，wsProgress 初始为 0，覆盖了已有的 progress
<Progress percent={wsProgress} />  // 进度被重置为 0
```

### 解决方案: 提取并合并双数据源

```typescript
// ✅ 正确: 分别提取两个数据源，然后合并
const { progress, currentStep } = useScriptPolling({
  onComplete: handleComplete,
  onError: handleError,
});

const {
  logs,
  progress: wsProgress,        // 重命名避免冲突
  currentStep: wsCurrentStep,  // 重命名避免冲突
} = useConsoleLogger(taskId, { enableWebSocket: true });

// 合并策略: WebSocket 有值时优先使用，否则使用轮询值
const effectiveProgress = wsProgress > 0 ? wsProgress : progress;
const effectiveCurrentStep = wsCurrentStep || currentStep;

// 使用合并后的值
<Progress percent={effectiveProgress} />
<span>{effectiveCurrentStep}</span>
```

### 为什么这样做?

1. **时序问题**: HTTP 轮询在任务启动后立即开始，WebSocket 需要时间建立连接
2. **初始值问题**: WebSocket 连接成功后，状态初始为 0，会覆盖已有进度
3. **优先级**: WebSocket 数据更实时，有值时应优先使用

### 合并策略选择

| 策略 | 适用场景 | 示例 |
|------|----------|------|
| WebSocket 优先 | 进度值（0 表示无数据） | `ws > 0 ? ws : poll` |
| 非空优先 | 字符串状态 | `ws \|\| poll` |
| 最大值 | 进度只增不减 | `Math.max(ws, poll)` |
| 时间戳比较 | 需要最新数据 | 比较更新时间 |

### 常见错误

```typescript
// ❌ 错误 1: 只使用 WebSocket 数据
const { progress } = useConsoleLogger(taskId);
// 问题: WebSocket 连接前进度为 0

// ❌ 错误 2: 只使用轮询数据
const { progress } = useScriptPolling(...);
// 问题: 轮询间隔内进度不更新

// ❌ 错误 3: 在 Hook 内部合并
// 问题: 两个 Hook 相互独立，无法在内部访问对方的值
```

---

## Pattern: 状态粒度控制 - 避免全局状态影响局部 UI

### 问题
使用全局状态控制多个组件的显示时，会导致"一人操作，全员受影响"的问题。

### 场景
```typescript
// 场景: 剧本生成页面
// - 左侧: 剧集列表（可点击切换）
// - 右侧: 剧本详情（显示内容或"生成中"状态）

// ❌ 错误: 使用全局状态
const isAnyGenerating = isGenerating || isBatchProcessing;

<ScriptDetail
  isGenerating={isAnyGenerating}  // 全局状态
  ...
/>

// 问题: 只要有任何生成任务在进行，所有剧集都显示"生成中"
// 用户无法切换查看其他已完成的剧集
```

### 解决方案: 计算当前项的精确状态

```typescript
// ✅ 正确: 计算当前选中项是否正在处理
const isCurrentEpisodeGenerating = useMemo(() => {
  // 单任务: 检查当前任务的目标是否为选中项
  if (isGenerating && generatingEpisode === selectedEpisode) {
    return true;
  }
  // 批量任务: 检查队列当前项是否为选中项
  if (isBatchProcessing && batchQueue[batchCurrentIndex]?.episodeNumber === selectedEpisode) {
    return true;
  }
  return false;
}, [isGenerating, generatingEpisode, selectedEpisode, isBatchProcessing, batchQueue, batchCurrentIndex]);

<ScriptDetail
  isGenerating={isCurrentEpisodeGenerating}  // 精确状态
  ...
/>

// 效果: 只有正在生成的那一集显示"生成中"，其他剧集可正常查看
```

### 为什么这样做?

1. **用户体验**: 用户可以在等待生成时查看其他内容，不会被"锁定"
2. **状态精确**: 每个组件只关心与自己相关的状态
3. **性能优化**: useMemo 避免每次渲染都重新计算

### 适用场景

| 场景 | 全局状态 | 精确状态 |
|------|----------|----------|
| 列表项操作 | `isAnyLoading` | `loadingItemId === currentId` |
| 批量处理 | `isBatchProcessing` | `queue[currentIndex]?.id === selectedId` |
| 多标签页 | `isAnyTabLoading` | `loadingTabKey === activeTabKey` |

### 常见错误

```typescript
// ❌ 错误 1: 直接传递全局状态
<ItemDetail isLoading={isAnyLoading} />

// ❌ 错误 2: 在子组件内部判断（职责不清）
const ItemDetail = ({ globalLoadingState, itemId }) => {
  // 子组件不应该知道全局状态的结构
  const isLoading = globalLoadingState.loadingId === itemId;
};

// ✅ 正确: 父组件计算精确状态后传递
const isCurrentItemLoading = loadingItemId === selectedItemId;
<ItemDetail isLoading={isCurrentItemLoading} />
```

---

## Pattern: 异步错误类型处理

### 问题
在 try-catch 中使用 `any` 类型处理错误，违反 TypeScript 严格模式，且无法获得类型提示。

### 场景
```typescript
// ❌ 错误: 使用 any 类型
const handleSubmit = async () => {
  try {
    await api.create(data);
  } catch (error: any) {  // ESLint: Unexpected any
    message.error(error.response?.data?.detail || '操作失败');
  }
};
```

### 解决方案: 使用 unknown + 类型断言

```typescript
// ✅ 正确: 使用 unknown 并进行类型断言
const handleSubmit = async () => {
  try {
    await api.create(data);
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } };
    message.error(err.response?.data?.detail || '操作失败');
  }
};
```

### 为什么这样做?

1. **类型安全**: `unknown` 是类型安全的 `any`，强制进行类型检查
2. **ESLint 合规**: 避免 `@typescript-eslint/no-explicit-any` 警告
3. **可维护性**: 类型断言明确表达了期望的错误结构

### 常用错误类型断言

```typescript
// Axios 错误响应
type AxiosErrorResponse = {
  response?: {
    data?: {
      detail?: string;
      message?: string;
    };
    status?: number;
  };
};

// 使用
catch (error: unknown) {
  const err = error as AxiosErrorResponse;
  const errorMsg = err.response?.data?.detail
    || err.response?.data?.message
    || '操作失败';
  message.error(errorMsg);
}
```

### 进阶: 类型守卫函数

```typescript
// 定义类型守卫
function isAxiosError(error: unknown): error is AxiosErrorResponse {
  return typeof error === 'object' && error !== null && 'response' in error;
}

// 使用
catch (error: unknown) {
  if (isAxiosError(error)) {
    message.error(error.response?.data?.detail || '操作失败');
  } else {
    message.error('未知错误');
  }
}
```

---

## 测试建议

### 测试闭包陷阱

```typescript
import { renderHook, act } from '@testing-library/react-hooks';

test('回调应该使用最新的 state', async () => {
    const { result } = renderHook(() => useMyHook());

    // 更新 state
    act(() => {
        result.current.updateState('new value');
    });

    // 触发回调
    await act(async () => {
        await result.current.triggerCallback();
    });

    // 验证回调使用了最新的 state
    expect(result.current.lastCallbackValue).toBe('new value');
});
```

---

## 相关文档

- [组件重构指南](./component-refactoring.md)
- [性能优化](./performance-optimization.md)
- [WebSocket 处理](./websocket-handling.md)

---

## 更新日志

| 日期 | 更新内容 | 作者 |
|------|----------|------|
| 2026-02-26 | 更新: useBreakdownLogs 合并到 useBreakdownWebSocket，统一使用 /ws/breakdown 端点 | Claude Opus 4.6 |
| 2026-02-26 | 新增: 异步错误类型处理模式 (unknown + 类型断言) | Claude Opus 4.6 |
| 2026-02-25 | 新增: 状态粒度控制模式 (避免全局状态影响局部 UI) | Claude Opus 4.6 |
| 2026-02-25 | 新增: 双数据源进度合并模式 (WebSocket + HTTP 轮询) | Claude Opus 4.6 |
| 2026-02-23 | 初始版本: React Hooks 最佳实践 | Claude Opus 4.6 |

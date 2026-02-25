# 前端性能优化规范

## 核心原则

> **一次加载，多次使用 - 使用缓存避免重复的 API 请求**

## Common Mistake: useEffect 中的重复 API 调用

### 症状

打开浏览器开发者工具的 Network 面板，发现同一个接口被调用多次，且参数完全相同。

**真实案例：** ScriptTab 组件进入时调用了 7 个接口，其中 2 个是重复请求：

```
1. batches?page=1&page_size=20 - 第1次
2. 42b45748... (Batch 1 拆解结果)
3. 48a28941... (Batch 2 拆解结果)
4. 9f59c227... (Batch 1 剧本列表)
5. 7b26a5ee... (Batch 2 剧本列表)
6. batches?page=1&page_size=20 - 第2次（重复！）
7. 42b45748... - 第2次（重复！）
```

### 原因

多个函数在不同的 useEffect 中独立调用相同的 API：

```typescript
// ❌ 错误示例
const ScriptTab = ({ projectId }) => {
  // 函数1: 加载剧集列表
  const loadEpisodes = useCallback(async () => {
    const batchesResponse = await projectApi.getBatches(projectId);
    const batches = batchesResponse.data.items;
    
    for (const batch of batches) {
      const breakdownResponse = await breakdownApi.getBreakdownResults(batch.id);
      // 处理数据...
    }
  }, [projectId]);
  
  // 函数2: 加载单集剧本
  const loadEpisodeScript = useCallback(async (episodeNumber) => {
    // 重复查询相同的批次和拆解结果！
    const batchesResponse = await projectApi.getBatches(projectId);
    const batches = batchesResponse.data.items;
    
    for (const batch of batches) {
      const breakdownResponse = await breakdownApi.getBreakdownResults(batch.id);
      // 查找剧集...
    }
  }, [projectId]);
  
  useEffect(() => {
    loadEpisodes();
  }, [projectId, loadEpisodes]);
  
  useEffect(() => {
    if (selectedEpisode) {
      loadEpisodeScript(selectedEpisode);  // 重复调用！
    }
  }, [selectedEpisode, loadEpisodeScript]);
};
```

### 解决方案

**使用 useRef 缓存映射关系：**

```typescript
// ✅ 正确示例
const ScriptTab = ({ projectId }) => {
  // 缓存：episode → breakdownId 映射
  const episodeToBreakdownMapRef = useRef<Map<number, string>>(new Map());
  
  // 函数1: 一次性加载所有数据并缓存
  const loadEpisodes = useCallback(async () => {
    if (!projectId) return;
    
    // 1. 获取批次
    const batchesResponse = await projectApi.getBatches(projectId);
    const batches = batchesResponse.data.items;
    
    // 2. 获取拆解结果并建立映射
    const breakdownIdMap = new Map<number, string>();
    
    for (const batch of batches) {
      const breakdownResponse = await breakdownApi.getBreakdownResults(batch.id);
      const data = breakdownResponse.data;
      
      if (data.plot_points) {
        data.plot_points.forEach(pp => {
          if (pp.episode) {
            breakdownIdMap.set(pp.episode, data.id);
          }
        });
      }
    }
    
    // 3. 缓存映射关系
    episodeToBreakdownMapRef.current = breakdownIdMap;
    
    // 4. 加载剧本列表...
  }, [projectId]);
  
  // 函数2: 直接使用缓存，不再重复查询
  const loadEpisodeScript = useCallback(async (episodeNumber) => {
    // 从缓存中获取 breakdownId
    const targetBreakdownId = episodeToBreakdownMapRef.current.get(episodeNumber);
    
    if (!targetBreakdownId) {
      console.warn(`未找到第 ${episodeNumber} 集的拆解结果`);
      return;
    }
    
    // 直接加载剧本，无需重复查询批次
    const response = await scriptApi.getEpisodeScript(targetBreakdownId, episodeNumber);
    setCurrentScript(response.data);
  }, []);
  
  useEffect(() => {
    loadEpisodes();
  }, [projectId, loadEpisodes]);
  
  useEffect(() => {
    if (selectedEpisode) {
      loadEpisodeScript(selectedEpisode);  // 使用缓存，不重复请求
    }
  }, [selectedEpisode, loadEpisodeScript]);
};
```

### 效果

- **优化前：** 7 个接口调用（包含 2 个重复）
- **优化后：** 5 个接口调用（减少 28.6%）

## Pattern: 数据加载和缓存策略

### 问题

如何设计数据加载逻辑，避免重复请求？

### 解决方案

**三层缓存策略：**

```typescript
// 1. 组件级缓存（useRef）- 适用于组件生命周期内的数据
const dataMapRef = useRef<Map<string, any>>(new Map());

// 2. 状态缓存（useState）- 适用于需要触发重渲染的数据
const [cachedData, setCachedData] = useState<any>(null);

// 3. 全局缓存（Context/Redux）- 适用于跨组件共享的数据
const { globalCache } = useContext(CacheContext);
```

### 选择指南

| 缓存类型 | 使用场景 | 生命周期 | 触发重渲染 |
|---------|---------|---------|-----------|
| **useRef** | 映射关系、配置数据 | 组件挂载期间 | ❌ 否 |
| **useState** | 列表数据、详情数据 | 组件挂载期间 | ✅ 是 |
| **Context** | 用户信息、全局配置 | 应用运行期间 | ✅ 是 |
| **Redux** | 复杂状态管理 | 应用运行期间 | ✅ 是 |

### 示例：组合使用

```typescript
const ScriptTab = ({ projectId }) => {
  // useRef: 缓存映射关系（不触发重渲染）
  const episodeToBreakdownMapRef = useRef<Map<number, string>>(new Map());
  
  // useState: 缓存列表数据（触发重渲染）
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [currentScript, setCurrentScript] = useState<Script | null>(null);
  
  const loadEpisodes = useCallback(async () => {
    // 1. 加载数据
    const data = await fetchData();
    
    // 2. 更新映射缓存（不触发重渲染）
    episodeToBreakdownMapRef.current = buildMap(data);
    
    // 3. 更新列表状态（触发重渲染）
    setEpisodes(data.episodes);
  }, [projectId]);
  
  const loadEpisodeScript = useCallback(async (episodeNumber) => {
    // 使用映射缓存查找
    const breakdownId = episodeToBreakdownMapRef.current.get(episodeNumber);
    
    if (breakdownId) {
      const script = await scriptApi.getEpisodeScript(breakdownId, episodeNumber);
      setCurrentScript(script);  // 更新状态，触发重渲染
    }
  }, []);
  
  return (
    <div>
      {episodes.map(ep => (
        <EpisodeItem 
          key={ep.episode} 
          episode={ep}
          onClick={() => loadEpisodeScript(ep.episode)}
        />
      ))}
      {currentScript && <ScriptViewer script={currentScript} />}
    </div>
  );
};
```

## Pattern: 批量数据加载优化

### 问题

需要加载多个相关资源时，如何减少请求次数？

### 解决方案

**一次性加载所有数据，然后在内存中处理：**

```typescript
// ✅ 推荐：一次性加载
const loadAllData = async () => {
  // 1. 并行加载所有批次
  const batchesResponse = await projectApi.getBatches(projectId);
  const batches = batchesResponse.data.items;
  
  // 2. 并行加载所有拆解结果
  const breakdownPromises = batches.map(batch => 
    breakdownApi.getBreakdownResults(batch.id)
  );
  const breakdownResults = await Promise.all(breakdownPromises);
  
  // 3. 在内存中处理数据
  const episodeMap = new Map();
  breakdownResults.forEach(result => {
    result.data.plot_points?.forEach(pp => {
      if (pp.episode) {
        episodeMap.set(pp.episode, result.data.id);
      }
    });
  });
  
  return episodeMap;
};
```

### 对比

```typescript
// ❌ 不推荐：串行加载
for (const batch of batches) {
  const breakdown = await breakdownApi.getBreakdownResults(batch.id);
  // 处理...
}
// 耗时：n * 请求时间

// ✅ 推荐：并行加载
const breakdownPromises = batches.map(batch =>
  breakdownApi.getBreakdownResults(batch.id)
);
const breakdowns = await Promise.all(breakdownPromises);
// 耗时：max(请求时间)
```

### 重要: 并行请求的错误处理

> **Warning**: 使用 `Promise.all` 时,如果任何一个请求失败,整个 `Promise.all` 都会失败。

**问题场景**:
```typescript
// ❌ 错误: 一个请求失败,所有数据都丢失
const breakdownPromises = batches.map(batch =>
  breakdownApi.getBreakdownResults(batch.id)
);
const breakdowns = await Promise.all(breakdownPromises);
// 如果第 5 个批次失败,前 4 个批次的数据也会丢失
```

**正确做法**:
```typescript
// ✅ 正确: 单个请求失败不影响其他请求
const breakdownPromises = batches.map(batch =>
  breakdownApi.getBreakdownResults(batch.id)
    .catch(err => {
      console.warn(`获取批次 ${batch.id} 失败:`, err);
      return null;  // 关键: 返回 null 而不是抛出异常
    })
);

const breakdownResponses = await Promise.all(breakdownPromises);

// 处理结果时过滤掉失败的请求
breakdownResponses.forEach((response) => {
  if (!response) return;  // 跳过失败的请求

  const data = response.data;
  // 处理成功的数据...
});
```

**性能对比**:

| 场景 | 串行 (for loop) | 并行 (无错误处理) | 并行 (有错误处理) |
|------|----------------|------------------|------------------|
| 50 个批次全部成功 | ~50 秒 | ~1 秒 | ~1 秒 |
| 50 个批次,第 5 个失败 | ~5 秒后失败 | ~1 秒后全部失败 | ~1 秒,获得 49 个结果 |
| 用户体验 | 差 | 差 (全部丢失) | **好 (部分成功)** |

**为什么这样做?**
- 单个批次失败不应该影响其他批次的数据
- 用户可以看到部分结果,而不是什么都看不到
- 提供更好的容错性和用户体验

## Gotcha: useCallback 依赖项陷阱

> **Warning**: useCallback 的依赖项不完整会导致闭包陷阱，使用过期的数据。

### 问题场景

```typescript
// ❌ 错误：缺少依赖项
const loadEpisodeScript = useCallback(async (episodeNumber) => {
  const breakdownId = episodeToBreakdownMapRef.current.get(episodeNumber);
  
  if (breakdownId) {
    const script = await scriptApi.getEpisodeScript(breakdownId, episodeNumber);
    setCurrentScript(script);
  }
}, []);  // ❌ 缺少 projectId 依赖

// 问题：projectId 变化时，函数不会重新创建，仍使用旧的 projectId
```

### 正确做法

```typescript
// ✅ 方案1：添加必要的依赖项
const loadEpisodeScript = useCallback(async (episodeNumber) => {
  if (!projectId) return;  // 使用 projectId
  
  const breakdownId = episodeToBreakdownMapRef.current.get(episodeNumber);
  // ...
}, [projectId]);  // ✅ 包含 projectId

// ✅ 方案2：使用 useRef 避免依赖
const projectIdRef = useRef(projectId);
useEffect(() => {
  projectIdRef.current = projectId;
}, [projectId]);

const loadEpisodeScript = useCallback(async (episodeNumber) => {
  const currentProjectId = projectIdRef.current;
  // ...
}, []);  // 不需要依赖 projectId
```

## Pattern: 清理缓存策略

### 问题

何时应该清理缓存？

### 解决方案

```typescript
const ScriptTab = ({ projectId }) => {
  const episodeToBreakdownMapRef = useRef<Map<number, string>>(new Map());
  
  const loadEpisodes = useCallback(async () => {
    if (!projectId) return;
    
    // 加载数据...
    const breakdownIdMap = new Map();
    // ...
    
    // 更新缓存
    episodeToBreakdownMapRef.current = breakdownIdMap;
    
    // 如果没有数据，清空缓存
    if (completedBatches.length === 0) {
      episodeToBreakdownMapRef.current.clear();
    }
  }, [projectId]);
  
  // 监听 projectId 变化，重置缓存
  useEffect(() => {
    // projectId 变化时，清空缓存
    episodeToBreakdownMapRef.current.clear();
  }, [projectId]);
  
  // 组件卸载时自动清理（useRef 会自动处理）
};
```

## Pattern: API 分页加载

### 问题

大项目返回大量数据导致页面加载慢、传输数据量大

### 解决方案

```typescript
// 前端支持分页参数
const breakdownApi = {
  getProjectBreakdowns: async (projectId: string, page: number = 1, pageSize: number = 20) => {
    return api.get('/breakdown/project-breakdowns', {
      params: { project_id: projectId, page, page_size: pageSize }
    });
  }
};

// 组件中使用
const breakdowns = breakdownsResponse.data.items || [];
```

### 后端实现要点

1. 添加分页参数：`page`, `page_size`
2. 使用 `func.count()` 查询总数
3. 使用 `offset()` 和 `limit()` 实现分页
4. 返回格式：`{ items: [], total, page, page_size }`

### 优化效果

| 优化点 | 效果 |
|--------|------|
| 减少返回字段 | 只返回前端需要的字段 |
| 添加分页 | 支持大项目分页加载 |
| 指定字段查询 | 减少数据库 IO |

## 性能检查清单

实现数据加载时，检查以下项目：

- [ ] 打开 Network 面板，检查是否有重复请求
- [ ] 相同的 API 调用是否可以合并
- [ ] 是否可以使用缓存避免重复查询
- [ ] 批量加载是否使用了并行请求
- [ ] useCallback 的依赖项是否完整
- [ ] 缓存是否在适当的时机清理

## 调试技巧

### 1. 识别重复请求

```typescript
// 在 API 调用前添加日志
const getBatches = async (projectId: string) => {
  console.log('[API] getBatches called', { projectId, stack: new Error().stack });
  return axios.get(`/api/projects/${projectId}/batches`);
};
```

### 2. 监控缓存命中率

```typescript
const episodeToBreakdownMapRef = useRef<Map<number, string>>(new Map());
let cacheHits = 0;
let cacheMisses = 0;

const loadEpisodeScript = useCallback(async (episodeNumber) => {
  const breakdownId = episodeToBreakdownMapRef.current.get(episodeNumber);
  
  if (breakdownId) {
    cacheHits++;
    console.log('[Cache] Hit', { episodeNumber, hitRate: cacheHits / (cacheHits + cacheMisses) });
  } else {
    cacheMisses++;
    console.log('[Cache] Miss', { episodeNumber });
  }
  
  // ...
}, []);
```

### 3. 使用 React DevTools Profiler

1. 打开 React DevTools
2. 切换到 Profiler 标签
3. 点击录制按钮
4. 执行操作
5. 查看组件渲染次数和耗时

## 相关资源

- [React Hooks 文档](https://react.dev/reference/react)
- [useCallback 最佳实践](https://react.dev/reference/react/useCallback)
- [useRef 使用指南](https://react.dev/reference/react/useRef)

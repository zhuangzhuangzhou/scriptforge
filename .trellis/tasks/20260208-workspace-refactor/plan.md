# Workspace.tsx 重构计划：组件拆分与状态管理优化

## 背景

用户发现 `frontend/src/pages/user/Workspace.tsx` 文件过大（36694 tokens，约 2500 行代码），这是一个典型的"上帝组件"问题。该组件包含了 6 个标签页的所有功能，导致：

1. **代码可维护性差**：47 个状态变量、21+ 个处理函数混杂在一起
2. **难以理解和修改**：单个文件包含多个独立功能模块
3. **测试困难**：无法对单个功能模块进行独立测试
4. **性能问题**：所有标签页的逻辑都在一个组件中，即使未激活也会执行

本计划将对 Workspace.tsx 和 Admin 页面进行系统性重构，按标签页拆分组件，提取 Custom Hooks，优化状态管理。

## 重要约束

### ⚠️ 关键要求

1. **UI 样式不变**：重构过程中不得更改任何 UI 样式，重构后的页面必须与当前页面一模一样
2. **Admin 页面重构**：`/admin` 页面的内容也需要进行重构
3. **文档更新**：重构完成后，需要更新各类说明文档，确保后续开发顺利

---

## 探索发现

### 文件复杂度统计

| 指标 | 当前值 | 建议值 | 状态 |
|------|--------|--------|------|
| 单个组件行数 | 2,500 | < 500 | ❌ 过大 |
| 状态变量数 | 47 | < 15 | ❌ 过多 |
| useEffect 数 | 4 | < 3 | ⚠️ 可接受 |
| 处理函数数 | 21+ | < 10 | ❌ 过多 |

### 标签页代码分布

| 标签页 | 代码行数 | 状态变量 | 复杂度 | 优先级 |
|--------|---------|---------|--------|--------|
| **PLOT** | 239 行 | 23 个 | ⭐⭐⭐⭐⭐ | 🔴 最高 |
| **CONFIG** | 237 行 | 12 个 | ⭐⭐⭐⭐ | 🟡 高 |
| **SOURCE** | 176 行 | 11 个 | ⭐⭐⭐ | 🟡 中 |
| **SCRIPT** | 177 行 | 1 个 | ⭐⭐⭐ | 🟢 低 |
| **AGENTS** | 40 行 | 2 个 | ⭐ | 🟢 低 |
| **SKILLS** | 25 行 | 0 个 | ⭐ | 🟢 低 |

### 关键问题

1. **PLOT 标签页是瓶颈**：占代码复杂度的 40%，包含最复杂的异步流程
2. **状态管理混乱**：47 个状态变量没有逻辑分组，难以维护
3. **轮询逻辑重复**：`pollBreakdownStatus` 和 `pollBatchProgress` 有相似代码
4. **错误处理分散**：错误处理逻辑分布在多个函数中

---

## 重构目标

### 目标 1：拆分所有标签页为独立模块
- **PLOT 标签页**（最复杂）：拆分为批次列表、详情展示、控制按钮等组件
- **CONFIG 标签页**（项目配置页）：拆分为项目信息、文件管理、配置卡片等组件
- **SOURCE 标签页**（小说原文页）：拆分为章节列表、章节查看器、上传模态框等组件
- **SCRIPT 标签页**：拆分为剧集列表、编辑器、质检报告等组件
- **AGENTS 标签页**：拆分为智能体卡片组件
- **SKILLS 标签页**：拆分为技能卡片组件

### 目标 2：提取 Custom Hooks
- `useBreakdownPolling` - 处理拆解轮询
- `useBatchProgress` - 处理批量进度
- `useBreakdownQueue` - 处理队列管理
- `useChapterList` - 处理章节列表管理
- `useChapterSearch` - 处理章节搜索
- `useProjectConfig` - 处理项目配置
- `useFileUpload` - 处理文件上传

### 目标 3：优化状态管理
- 将相关状态分组
- 减少全局状态数量
- 每个标签页独立管理自己的状态

---

## 重构方案

### 完整目录结构

```
frontend/src/pages/user/Workspace/
├── index.tsx                          # 主容器（保留原 Workspace.tsx 的框架）
│
├── PlotTab/                           # PLOT 标签页（剧情拆解）
│   ├── index.tsx                      # PlotTab 主容器
│   ├── BatchList.tsx                  # 左侧批次列表
│   ├── BatchCard.tsx                  # 批次卡片组件
│   ├── BreakdownDetail.tsx            # 右侧拆解详情
│   ├── BreakdownControls.tsx          # 拆解控制按钮组
│   └── hooks/
│       ├── useBreakdownPolling.ts     # 拆解轮询 Hook
│       ├── useBatchProgress.ts        # 批量进度 Hook
│       └── useBreakdownQueue.ts       # 队列管理 Hook
│
├── ConfigTab/                         # CONFIG 标签页（项目配置）
│   ├── index.tsx                      # ConfigTab 主容器
│   ├── ProjectInfo.tsx                # 项目基础信息编辑
│   ├── StatCards.tsx                  # 统计卡片组
│   ├── SourceFileManager.tsx          # 小说源文件管理
│   ├── BatchConfig.tsx                # 批次配置
│   ├── ModelSelector.tsx              # 模型选择
│   └── hooks/
│       ├── useProjectConfig.ts        # 项目配置管理
│       └── useFileUpload.ts           # 文件上传
│
├── SourceTab/                         # SOURCE 标签页（小说原文）
│   ├── index.tsx                      # SourceTab 主容器
│   ├── ChapterList.tsx                # 章节列表
│   ├── ChapterCard.tsx                # 章节卡片
│   ├── ChapterViewer.tsx              # 章节查看器
│   ├── UploadModal.tsx                # 上传弹窗
│   └── hooks/
│       ├── useChapterList.ts          # 章节列表管理
│       └── useChapterSearch.ts        # 章节搜索
│
├── ScriptTab/                         # SCRIPT 标签页（剧本）
│   ├── index.tsx                      # ScriptTab 主容器
│   ├── EpisodeList.tsx                # 左侧剧集列表
│   ├── ScriptEditor.tsx               # 中间剧本编辑器
│   └── QCReport.tsx                   # 右侧质检报告
│
├── AgentsTab/                         # AGENTS 标签页（智能体）
│   ├── index.tsx                      # AgentsTab 主容器
│   └── AgentCard.tsx                  # 智能体卡片
│
└── SkillsTab/                         # SKILLS 标签页（技能库）
    ├── index.tsx                      # SkillsTab 主容器
    └── SkillCard.tsx                  # 技能卡片
```

---

### 阶段 1：拆分 PLOT 标签页（优先级最高）

##### 1. `PlotTab/index.tsx` - 主容器
**职责**：
- 管理 PLOT 标签页的整体状态
- 协调子组件之间的通信
- 处理 API 调用

**状态管理**：
```typescript
// 批次相关
const [batches, setBatches] = useState<Batch[]>([]);
const [selectedBatch, setSelectedBatch] = useState<Batch | null>(null);

// 拆解结果
const [breakdownResult, setBreakdownResult] = useState<PlotBreakdown | null>(null);

// 使用 Custom Hooks
const { taskId, progress, isRunning, startBreakdown, cancelBreakdown } = useBreakdownPolling();
const { batchProgress, refreshProgress } = useBatchProgress(projectId);
```

##### 2. `PlotTab/BatchList.tsx` - 批次列表
**职责**：
- 展示批次列表
- 处理批次选择
- 显示批次状态和进度

**Props**：
```typescript
interface BatchListProps {
  batches: Batch[];
  selectedBatch: Batch | null;
  onSelectBatch: (batch: Batch) => void;
  onStartBreakdown: (batchId: string) => void;
  isLoading: boolean;
}
```

##### 3. `PlotTab/BatchCard.tsx` - 批次卡片
**职责**：
- 展示单个批次信息
- 显示状态徽章
- 显示进度条

**Props**：
```typescript
interface BatchCardProps {
  batch: Batch;
  isSelected: boolean;
  onClick: () => void;
  onStartBreakdown: () => void;
}
```

##### 4. `PlotTab/BreakdownDetail.tsx` - 拆解详情
**职责**：
- 展示拆解结果
- 显示冲突、伏笔、角色等信息
- 提供导出功能

**Props**：
```typescript
interface BreakdownDetailProps {
  result: PlotBreakdown | null;
  loading: boolean;
}
```

##### 5. `PlotTab/BreakdownControls.tsx` - 控制按钮组
**职责**：
- 提供拆解操作按钮（单个、循环、批量）
- 显示按钮状态（禁用、加载中）
- 处理按钮点击事件

**Props**：
```typescript
interface BreakdownControlsProps {
  selectedBatch: Batch | null;
  isRunning: boolean;
  onStartSingle: () => void;
  onStartLoop: () => void;
  onStartBatch: () => void;
  onCancel: () => void;
}
```

---

### 阶段 2：拆分 CONFIG 标签页（项目配置页）

#### 关键文件说明

##### 1. `ConfigTab/index.tsx` - 主容器
**职责**：
- 管理项目配置的整体状态
- 协调子组件之间的通信
- 处理配置保存和更新

**状态管理**：
```typescript
const [project, setProject] = useState<any>(null);
const [formData, setFormData] = useState({
  name: '',
  novel_type: '',
  description: '',
  batch_size: 5
});

// 使用 Custom Hooks
const { uploading, uploadFile } = useFileUpload();
const { saving, saveConfig } = useProjectConfig();
```

##### 2. `ConfigTab/ProjectInfo.tsx` - 项目基础信息
**职责**：
- 项目名称、类型、描述编辑
- 表单验证
- 实时保存

**Props**：
```typescript
interface ProjectInfoProps {
  formData: {
    name: string;
    novel_type: string;
    description: string;
  };
  onChange: (field: string, value: string) => void;
  onSave: () => void;
  saving: boolean;
}
```

##### 3. `ConfigTab/StatCards.tsx` - 统计卡片组
**职责**：
- 展示项目统计信息（总章节、字数、进度等）
- 卡片布局和样式

**Props**：
```typescript
interface StatCardsProps {
  totalChapters: number;
  totalWords: number;
  breakdownProgress: number;
  status: string;
}
```

##### 4. `ConfigTab/SourceFileManager.tsx` - 源文件管理
**职责**：
- 小说文件上传
- 文件列表展示
- 文件删除

**Props**：
```typescript
interface SourceFileManagerProps {
  projectId: string;
  onUploadSuccess: () => void;
}
```

##### 5. `ConfigTab/BatchConfig.tsx` - 批次配置
**职责**：
- 拆剧批次设置
- 章节拆分规则选择
- 智能拆分按钮

**Props**：
```typescript
interface BatchConfigProps {
  batchSize: number;
  splitRule: string;
  onBatchSizeChange: (size: number) => void;
  onSplitRuleChange: (rule: string) => void;
  onSplit: () => void;
  splitting: boolean;
}
```

##### 6. `ConfigTab/ModelSelector.tsx` - 模型选择
**职责**：
- 拆解模型选择
- 生成模型选择
- 模型配置

**Props**：
```typescript
interface ModelSelectorProps {
  breakdownModel: string;
  scriptModel: string;
  onBreakdownModelChange: (model: string) => void;
  onScriptModelChange: (model: string) => void;
}
```

---

### 阶段 3：拆分 SOURCE 标签页（小说原文页）

#### 关键文件说明

##### 1. `SourceTab/index.tsx` - 主容器
**职责**：
- 管理章节列表状态
- 处理章节选择和查看
- 协调子组件通信

**状态管理**：
```typescript
const [chapters, setChapters] = useState<any[]>([]);
const [selectedChapter, setSelectedChapter] = useState<any>(null);

// 使用 Custom Hooks
const { loading, loadMore, hasMore } = useChapterList(projectId);
const { keyword, setKeyword, filteredChapters } = useChapterSearch(chapters);
```

##### 2. `SourceTab/ChapterList.tsx` - 章节列表
**职责**：
- 展示章节列表（无限滚动）
- 章节搜索
- 章节操作按钮

**Props**：
```typescript
interface ChapterListProps {
  chapters: any[];
  selectedChapter: any | null;
  onSelectChapter: (chapter: any) => void;
  onDeleteChapter: (chapterId: string) => void;
  onLoadMore: () => void;
  hasMore: boolean;
  loading: boolean;
}
```

##### 3. `SourceTab/ChapterCard.tsx` - 章节卡片
**职责**：
- 展示单个章节信息
- 章节状态徽章
- 操作按钮（查看、删除）

**Props**：
```typescript
interface ChapterCardProps {
  chapter: any;
  isSelected: boolean;
  onClick: () => void;
  onDelete: () => void;
}
```

##### 4. `SourceTab/ChapterViewer.tsx` - 章节查看器
**职责**：
- 展示章节内容
- 滚动阅读
- 导出功能

**Props**：
```typescript
interface ChapterViewerProps {
  chapter: any | null;
  loading: boolean;
}
```

##### 5. `SourceTab/UploadModal.tsx` - 上传弹窗
**职责**：
- 章节文件上传
- 插入位置选择
- 文件验证

**Props**：
```typescript
interface UploadModalProps {
  visible: boolean;
  onClose: () => void;
  onUpload: (file: File, position: 'after' | 'end') => void;
  uploading: boolean;
}
```

---

### 阶段 4：拆分 SCRIPT 标签页

#### 关键文件说明

##### 1. `ScriptTab/index.tsx` - 主容器
**职责**：
- 管理剧集列表和选中状态
- 协调三列布局

**状态管理**：
```typescript
const [selectedEpisodeId, setSelectedEpisodeId] = useState<number>(1);
const selectedEpisode = episodes.find(ep => ep.id === selectedEpisodeId);
```

##### 2. `ScriptTab/EpisodeList.tsx` - 剧集列表
**职责**：
- 展示剧集列表
- 剧集选择
- 状态徽章

**Props**：
```typescript
interface EpisodeListProps {
  episodes: any[];
  selectedId: number;
  onSelect: (id: number) => void;
}
```

##### 3. `ScriptTab/ScriptEditor.tsx` - 剧本编辑器
**职责**：
- 展示剧本内容
- Markdown 渲染
- 导出功能

**Props**：
```typescript
interface ScriptEditorProps {
  episode: any;
}
```

##### 4. `ScriptTab/QCReport.tsx` - 质检报告
**职责**：
- 展示质检结果
- 得分和检查项
- 问题高亮

**Props**：
```typescript
interface QCReportProps {
  report: any | null;
}
```

---

### 阶段 5：拆分 AGENTS 和 SKILLS 标签页

#### AGENTS 标签页

##### 1. `AgentsTab/index.tsx` - 主容器
**职责**：
- 管理智能体列表
- 打开配置弹窗

##### 2. `AgentsTab/AgentCard.tsx` - 智能体卡片
**职责**：
- 展示智能体信息
- 状态指示
- 配置按钮

**Props**：
```typescript
interface AgentCardProps {
  agent: any;
  onConfigure: () => void;
}
```

#### SKILLS 标签页

##### 1. `SkillsTab/index.tsx` - 主容器
**职责**：
- 管理技能列表
- 添加自定义技能

##### 2. `SkillsTab/SkillCard.tsx` - 技能卡片
**职责**：
- 展示技能信息
- 启用/禁用开关

**Props**：
```typescript
interface SkillCardProps {
  skill: any;
  onToggle: (id: string) => void;
}
```

---

### 阶段 6：提取 Custom Hooks（所有标签页）

#### PLOT 标签页 Hooks

#### 1. `useBreakdownPolling.ts` - 拆解轮询 Hook

**功能**：
- 启动单个拆解任务
- 轮询任务状态
- 自动更新进度
- 处理任务完成/失败

**接口**：
```typescript
interface UseBreakdownPollingOptions {
  onComplete?: (result: any) => void;
  onError?: (error: string) => void;
  pollInterval?: number;
}

export const useBreakdownPolling = (options?: UseBreakdownPollingOptions) => {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState('');

  const startBreakdown = async (batchId: string, config?: any) => {
    const res = await breakdownApi.startBreakdown(batchId, config);
    setTaskId(res.data.task_id);
    setIsRunning(true);
    // 开始轮询
  };

  const cancelBreakdown = () => {
    setTaskId(null);
    setIsRunning(false);
  };

  return {
    taskId,
    progress,
    isRunning,
    currentStep,
    startBreakdown,
    cancelBreakdown
  };
};
```

**实现细节**：
- 使用 `useEffect` 监听 `taskId` 变化，自动开始轮询
- 使用 `setInterval` 每 2 秒查询一次任务状态
- 任务完成后自动停止轮询，调用 `onComplete` 回调
- 任务失败后调用 `onError` 回调

#### 2. `useBatchProgress.ts` - 批量进度 Hook

**功能**：
- 获取批量拆解进度
- 自动刷新进度
- 提供进度统计

**接口**：
```typescript
export const useBatchProgress = (projectId: string | null) => {
  const [batchProgress, setBatchProgress] = useState<{
    total: number;
    completed: number;
    in_progress: number;
    pending: number;
    failed: number;
  } | null>(null);

  const [isLoading, setIsLoading] = useState(false);

  const refreshProgress = async () => {
    if (!projectId) return;
    setIsLoading(true);
    const res = await breakdownApi.getBatchProgress(projectId);
    setBatchProgress(res.data);
    setIsLoading(false);
  };

  useEffect(() => {
    if (projectId) {
      refreshProgress();
      const interval = setInterval(refreshProgress, 5000);
      return () => clearInterval(interval);
    }
  }, [projectId]);

  return {
    batchProgress,
    isLoading,
    refreshProgress
  };
};
```

#### 3. `useBreakdownQueue.ts` - 队列管理 Hook

**功能**：
- 管理拆解队列
- 依次执行队列中的任务
- 提供队列状态

**接口**：
```typescript
export const useBreakdownQueue = () => {
  const [queue, setQueue] = useState<string[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);

  const startQueue = (batchIds: string[]) => {
    setQueue(batchIds);
    setCurrentIndex(0);
    setIsProcessing(true);
  };

  const processNext = async () => {
    if (currentIndex >= queue.length) {
      setIsProcessing(false);
      return;
    }
    // 处理当前任务
    const batchId = queue[currentIndex];
    await breakdownApi.startBreakdown(batchId);
    setCurrentIndex(prev => prev + 1);
  };

  return {
    queue,
    currentIndex,
    isProcessing,
    startQueue,
    processNext
  };
};
```

#### CONFIG 标签页 Hooks

#### 4. `useProjectConfig.ts` - 项目配置管理 Hook

**功能**：
- 加载项目配置
- 保存配置更新
- 表单验证

**接口**：
```typescript
export const useProjectConfig = (projectId: string | null) => {
  const [config, setConfig] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  const loadConfig = async () => {
    if (!projectId) return;
    const res = await projectApi.getProject(projectId);
    setConfig(res.data);
  };

  const saveConfig = async (data: any) => {
    if (!projectId) return;
    setSaving(true);
    await projectApi.updateProject(projectId, data);
    setSaving(false);
  };

  useEffect(() => {
    loadConfig();
  }, [projectId]);

  return {
    config,
    saving,
    saveConfig,
    reloadConfig: loadConfig
  };
};
```

#### 5. `useFileUpload.ts` - 文件上传 Hook

**功能**：
- 处理文件上传
- 进度跟踪
- 错误处理

**接口**：
```typescript
export const useFileUpload = () => {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const uploadFile = async (projectId: string, file: File) => {
    setUploading(true);
    setProgress(0);

    try {
      const res = await projectApi.uploadFile(projectId, file);
      setProgress(100);
      return res;
    } catch (error) {
      throw error;
    } finally {
      setUploading(false);
    }
  };

  return {
    uploading,
    progress,
    uploadFile
  };
};
```

#### SOURCE 标签页 Hooks

#### 6. `useChapterList.ts` - 章节列表管理 Hook

**功能**：
- 加载章节列表
- 分页加载
- 无限滚动

**接口**：
```typescript
export const useChapterList = (projectId: string | null) => {
  const [chapters, setChapters] = useState<any[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);

  const loadChapters = async (pageNum: number = 1, append: boolean = false) => {
    if (!projectId) return;
    setLoading(true);

    const res = await projectApi.getChapters(projectId, pageNum, 20);
    const newChapters = res.data.items || [];

    if (append) {
      setChapters(prev => [...prev, ...newChapters]);
    } else {
      setChapters(newChapters);
    }

    setHasMore(newChapters.length === 20);
    setLoading(false);
  };

  const loadMore = () => {
    if (!loading && hasMore) {
      const nextPage = page + 1;
      setPage(nextPage);
      loadChapters(nextPage, true);
    }
  };

  useEffect(() => {
    if (projectId) {
      loadChapters(1, false);
    }
  }, [projectId]);

  return {
    chapters,
    loading,
    hasMore,
    loadMore,
    reload: () => loadChapters(1, false)
  };
};
```

#### 7. `useChapterSearch.ts` - 章节搜索 Hook

**功能**：
- 关键词搜索
- 实时过滤
- 防抖处理

**接口**：
```typescript
export const useChapterSearch = (chapters: any[]) => {
  const [keyword, setKeyword] = useState('');
  const [filteredChapters, setFilteredChapters] = useState(chapters);

  useEffect(() => {
    if (!keyword) {
      setFilteredChapters(chapters);
      return;
    }

    const timer = setTimeout(() => {
      const filtered = chapters.filter(ch =>
        ch.title?.toLowerCase().includes(keyword.toLowerCase()) ||
        ch.content?.toLowerCase().includes(keyword.toLowerCase())
      );
      setFilteredChapters(filtered);
    }, 300);

    return () => clearTimeout(timer);
  }, [keyword, chapters]);

  return {
    keyword,
    setKeyword,
    filteredChapters
  };
};
```

---

### 阶段 7：重构主容器 `Workspace/index.tsx`

#### 简化后的结构

```typescript
const Workspace: React.FC<ProjectWorkspaceProps> = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [activeTab, setActiveTab] = useState<Tab>('CONFIG');
  const [project, setProject] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // 全局状态（所有标签页共享）
  const [showConsole, setShowConsole] = useState(false);
  const [showCopilot, setShowCopilot] = useState(false);

  // 使用 useConsoleLogger Hook
  const {
    logs,
    llmStats,
    isConnected,
    addLog,
    clearLogs,
    fetchLLMCallLogs
  } = useConsoleLogger(breakdownTaskId);

  // 加载项目数据
  useEffect(() => {
    if (projectId) {
      fetchProject();
    }
  }, [projectId]);

  const fetchProject = async () => {
    setLoading(true);
    const res = await projectApi.getProject(projectId!);
    setProject(res.data);
    setLoading(false);
  };

  // 渲染内容
  const renderContent = () => {
    switch (activeTab) {
      case 'CONFIG':
        return <ConfigTab projectId={projectId!} project={project} onUpdate={fetchProject} />;
      case 'SOURCE':
        return <SourceTab projectId={projectId!} />;
      case 'AGENTS':
        return <AgentsTab />;
      case 'SKILLS':
        return <SkillsTab />;
      case 'PLOT':
        return <PlotTab projectId={projectId!} project={project} />;
      case 'SCRIPT':
        return <ScriptTab />;
      default:
        return null;
    }
  };

  return (
    <div className="flex h-screen bg-slate-950">
      {/* 侧边栏 */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* 主内容区 */}
      <div className="flex-1 overflow-hidden">
        {renderContent()}
      </div>

      {/* 全局组件 */}
      <ConsoleLogger
        logs={logs}
        llmStats={llmStats}
        visible={showConsole}
        isProcessing={isProcessing}
        onClose={() => setShowConsole(false)}
      />
      <AICopilot visible={showCopilot} onClose={() => setShowCopilot(false)} />
    </div>
  );
};
```

**关键改进**：
- 状态变量从 47 个减少到约 10 个
- 每个标签页独立管理自己的状态
- 主容器只负责标签页切换和全局状态

---

## 实施步骤

### 步骤 1：创建目录结构（1 天）

1. 创建 `frontend/src/pages/user/Workspace/` 目录
2. 创建所有标签页子目录：
   - `PlotTab/` 和 `PlotTab/hooks/`
   - `ConfigTab/` 和 `ConfigTab/hooks/`
   - `SourceTab/` 和 `SourceTab/hooks/`
   - `ScriptTab/`
   - `AgentsTab/`
   - `SkillsTab/`
3. 移动原 `Workspace.tsx` 为 `Workspace/index.tsx`

### 步骤 2：提取 Custom Hooks（2 天）

**PLOT 标签页 Hooks**（1 天）：
1. 创建 `useBreakdownPolling.ts` - 拆解轮询
2. 创建 `useBatchProgress.ts` - 批量进度
3. 创建 `useBreakdownQueue.ts` - 队列管理

**CONFIG 和 SOURCE 标签页 Hooks**（1 天）：
1. 创建 `useProjectConfig.ts` - 项目配置
2. 创建 `useFileUpload.ts` - 文件上传
3. 创建 `useChapterList.ts` - 章节列表
4. 创建 `useChapterSearch.ts` - 章节搜索

### 步骤 3：拆分 PLOT 标签页（2 天）

1. 创建 `PlotTab/index.tsx` - 主容器
2. 创建 `BatchList.tsx` - 批次列表
3. 创建 `BatchCard.tsx` - 批次卡片
4. 创建 `BreakdownDetail.tsx` - 拆解详情
5. 创建 `BreakdownControls.tsx` - 控制按钮组
6. 集成 Custom Hooks
7. 测试功能

### 步骤 4：拆分 CONFIG 标签页（2 天）

1. 创建 `ConfigTab/index.tsx` - 主容器
2. 创建 `ProjectInfo.tsx` - 项目信息
3. 创建 `StatCards.tsx` - 统计卡片
4. 创建 `SourceFileManager.tsx` - 文件管理
5. 创建 `BatchConfig.tsx` - 批次配置
6. 创建 `ModelSelector.tsx` - 模型选择
7. 集成 Custom Hooks
8. 测试功能

### 步骤 5：拆分 SOURCE 标签页（2 天）

1. 创建 `SourceTab/index.tsx` - 主容器
2. 创建 `ChapterList.tsx` - 章节列表
3. 创建 `ChapterCard.tsx` - 章节卡片
4. 创建 `ChapterViewer.tsx` - 章节查看器
5. 创建 `UploadModal.tsx` - 上传弹窗
6. 集成 Custom Hooks
7. 测试功能

### 步骤 6：拆分 SCRIPT 标签页（1 天）

1. 创建 `ScriptTab/index.tsx` - 主容器
2. 创建 `EpisodeList.tsx` - 剧集列表
3. 创建 `ScriptEditor.tsx` - 剧本编辑器
4. 创建 `QCReport.tsx` - 质检报告
5. 测试功能

### 步骤 7：拆分 AGENTS 和 SKILLS 标签页（1 天）

1. 创建 `AgentsTab/index.tsx` 和 `AgentCard.tsx`
2. 创建 `SkillsTab/index.tsx` 和 `SkillCard.tsx`
3. 测试功能

### 步骤 8：重构主容器（1 天）

1. 简化 `Workspace/index.tsx`
2. 导入所有标签页组件
3. 更新路由和导入路径
4. 测试标签页切换

### 步骤 9：测试和优化（2 天）

1. 功能测试（所有标签页）
2. 性能测试
3. 代码审查
4. 优化和修复

---

## 文件修改清单

### 新建文件

| 文件 | 用途 |
|------|------|
| **主容器** | |
| `frontend/src/pages/user/Workspace/index.tsx` | 主容器（重构后） |
| **PLOT 标签页** | |
| `frontend/src/pages/user/Workspace/PlotTab/index.tsx` | PLOT 主容器 |
| `frontend/src/pages/user/Workspace/PlotTab/BatchList.tsx` | 批次列表 |
| `frontend/src/pages/user/Workspace/PlotTab/BatchCard.tsx` | 批次卡片 |
| `frontend/src/pages/user/Workspace/PlotTab/BreakdownDetail.tsx` | 拆解详情 |
| `frontend/src/pages/user/Workspace/PlotTab/BreakdownControls.tsx` | 控制按钮组 |
| `frontend/src/pages/user/Workspace/PlotTab/hooks/useBreakdownPolling.ts` | 拆解轮询 Hook |
| `frontend/src/pages/user/Workspace/PlotTab/hooks/useBatchProgress.ts` | 批量进度 Hook |
| `frontend/src/pages/user/Workspace/PlotTab/hooks/useBreakdownQueue.ts` | 队列管理 Hook |
| **CONFIG 标签页** | |
| `frontend/src/pages/user/Workspace/ConfigTab/index.tsx` | CONFIG 主容器 |
| `frontend/src/pages/user/Workspace/ConfigTab/ProjectInfo.tsx` | 项目信息 |
| `frontend/src/pages/user/Workspace/ConfigTab/StatCards.tsx` | 统计卡片 |
| `frontend/src/pages/user/Workspace/ConfigTab/SourceFileManager.tsx` | 文件管理 |
| `frontend/src/pages/user/Workspace/ConfigTab/BatchConfig.tsx` | 批次配置 |
| `frontend/src/pages/user/Workspace/ConfigTab/ModelSelector.tsx` | 模型选择 |
| `frontend/src/pages/user/Workspace/ConfigTab/hooks/useProjectConfig.ts` | 项目配置 Hook |
| `frontend/src/pages/user/Workspace/ConfigTab/hooks/useFileUpload.ts` | 文件上传 Hook |
| **SOURCE 标签页** | |
| `frontend/src/pages/user/Workspace/SourceTab/index.tsx` | SOURCE 主容器 |
| `frontend/src/pages/user/Workspace/SourceTab/ChapterList.tsx` | 章节列表 |
| `frontend/src/pages/user/Workspace/SourceTab/ChapterCard.tsx` | 章节卡片 |
| `frontend/src/pages/user/Workspace/SourceTab/ChapterViewer.tsx` | 章节查看器 |
| `frontend/src/pages/user/Workspace/SourceTab/UploadModal.tsx` | 上传弹窗 |
| `frontend/src/pages/user/Workspace/SourceTab/hooks/useChapterList.ts` | 章节列表 Hook |
| `frontend/src/pages/user/Workspace/SourceTab/hooks/useChapterSearch.ts` | 章节搜索 Hook |
| **SCRIPT 标签页** | |
| `frontend/src/pages/user/Workspace/ScriptTab/index.tsx` | SCRIPT 主容器 |
| `frontend/src/pages/user/Workspace/ScriptTab/EpisodeList.tsx` | 剧集列表 |
| `frontend/src/pages/user/Workspace/ScriptTab/ScriptEditor.tsx` | 剧本编辑器 |
| `frontend/src/pages/user/Workspace/ScriptTab/QCReport.tsx` | 质检报告 |
| **AGENTS 标签页** | |
| `frontend/src/pages/user/Workspace/AgentsTab/index.tsx` | AGENTS 主容器 |
| `frontend/src/pages/user/Workspace/AgentsTab/AgentCard.tsx` | 智能体卡片 |
| **SKILLS 标签页** | |
| `frontend/src/pages/user/Workspace/SkillsTab/index.tsx` | SKILLS 主容器 |
| `frontend/src/pages/user/Workspace/SkillsTab/SkillCard.tsx` | 技能卡片 |

### 删除文件

| 文件 | 原因 |
|------|------|
| `frontend/src/pages/user/Workspace.tsx` | 重构为 `Workspace/index.tsx` |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `frontend/src/App.tsx` | 更新路由导入路径（如果需要） |

---

## 验收标准

### 功能验收

- [ ] **PLOT 标签页**
  - [ ] 批次列表正常加载和显示
  - [ ] 批次选择功能正常
  - [ ] 单个拆解任务启动和轮询正常
  - [ ] 循环拆解功能正常
  - [ ] 批量拆解功能正常
  - [ ] 进度条实时更新
  - [ ] 拆解结果正常展示
  - [ ] 错误处理和重试功能正常

- [ ] **CONFIG 标签页**
  - [ ] 项目信息编辑和保存正常
  - [ ] 统计卡片显示正确
  - [ ] 文件上传功能正常
  - [ ] 批次配置功能正常
  - [ ] 模型选择功能正常
  - [ ] 智能拆分功能正常

- [ ] **SOURCE 标签页**
  - [ ] 章节列表加载正常
  - [ ] 无限滚动加载正常
  - [ ] 章节搜索功能正常
  - [ ] 章节查看功能正常
  - [ ] 章节上传功能正常
  - [ ] 章节删除功能正常

- [ ] **SCRIPT 标签页**
  - [ ] 剧集列表显示正常
  - [ ] 剧本内容显示正常
  - [ ] 质检报告显示正常
  - [ ] 导出功能正常

- [ ] **AGENTS 标签页**
  - [ ] 智能体列表显示正常
  - [ ] 配置弹窗打开正常

- [ ] **SKILLS 标签页**
  - [ ] 技能列表显示正常
  - [ ] 启用/禁用功能正常

- [ ] **全局功能**
  - [ ] 标签页切换正常
  - [ ] Console Logger 集成正常
  - [ ] AI Copilot 集成正常

### 代码质量验收

- [ ] 主容器代码行数 < 500 行
- [ ] PlotTab 主容器代码行数 < 200 行
- [ ] 单个子组件代码行数 < 150 行
- [ ] 状态变量数量合理（主容器 < 15 个）
- [ ] 所有组件有完整的 TypeScript 类型定义
- [ ] 无 `any` 类型（除非必要）
- [ ] Custom Hooks 有清晰的接口定义

### 性能验收

- [ ] 组件渲染性能无明显下降
- [ ] 无不必要的重渲染
- [ ] 轮询逻辑不影响其他标签页

---

## 风险与缓解

### 风险 1：重构过程中引入 Bug

**风险**：拆分组件时可能遗漏某些逻辑或状态

**缓解**：
- 逐步重构，每次只拆分一个标签页
- 充分测试每个拆分步骤
- 保留原代码作为参考
- 使用 Git 分支进行重构

### 风险 2：状态管理复杂度增加

**风险**：拆分后组件间通信可能变复杂

**缓解**：
- 使用 Props 传递简单状态
- 使用 Custom Hooks 封装复杂逻辑
- 必要时使用 Context 共享状态

### 风险 3：性能问题

**风险**：拆分后可能增加组件渲染次数

**缓解**：
- 使用 `React.memo` 优化子组件
- 使用 `useCallback` 和 `useMemo` 优化函数和计算
- 监控组件渲染性能

---

## 后续扩展方向

### 阶段 2：拆分其他标签页（可选）

**已包含在主计划中**，所有标签页都将被拆分。

### 阶段 3：状态管理优化（可选）

1. 引入 Context API 管理全局状态
2. 使用 useReducer 管理复杂状态
3. 考虑使用 Zustand 或 Jotai 进行状态管理

### 阶段 4：性能优化（可选）

1. 使用 React.memo 优化子组件
2. 使用 useCallback 和 useMemo 优化函数和计算
3. 实现虚拟滚动（章节列表、批次列表）
4. 代码分割和懒加载

---

## 预计工期

| 阶段 | 任务 | 工期 |
|------|------|------|
| **阶段 1** | 创建目录结构 | 1 天 |
| **阶段 2** | 提取 Custom Hooks | 2 天 |
| **阶段 3** | 拆分 PLOT 标签页 | 2 天 |
| **阶段 4** | 拆分 CONFIG 标签页 | 2 天 |
| **阶段 5** | 拆分 SOURCE 标签页 | 2 天 |
| **阶段 6** | 拆分 SCRIPT 标签页 | 1 天 |
| **阶段 7** | 拆分 AGENTS 和 SKILLS 标签页 | 1 天 |
| **阶段 8** | 重构主容器 | 1 天 |
| **阶段 9** | 测试和优化 | 2 天 |
| **总计** | | **14 天** |

**注意**：这是完整重构所有标签页的工期。可以分阶段实施，优先完成 PLOT、CONFIG、SOURCE 三个最复杂的标签页（约 8-9 天）。

---

## 关键文件路径

### 当前文件
- `frontend/src/pages/user/Workspace.tsx` (2500 行，需要重构)

### 重构后文件（主要文件）
- `frontend/src/pages/user/Workspace/index.tsx` (主容器，约 300 行)
- `frontend/src/pages/user/Workspace/PlotTab/index.tsx` (约 150 行)
- `frontend/src/pages/user/Workspace/ConfigTab/index.tsx` (约 120 行)
- `frontend/src/pages/user/Workspace/SourceTab/index.tsx` (约 100 行)
- `frontend/src/pages/user/Workspace/ScriptTab/index.tsx` (约 80 行)
- `frontend/src/pages/user/Workspace/AgentsTab/index.tsx` (约 50 行)
- `frontend/src/pages/user/Workspace/SkillsTab/index.tsx` (约 40 行)

**总计**：约 840 行（主容器 + 各标签页主容器），相比原来的 2500 行减少了 66%

---

## 验证方法

### 功能测试

1. **批次列表测试**
   ```
   1. 进入 PLOT 标签页
   2. 验证批次列表正常加载
   3. 点击批次，验证选中状态
   4. 验证批次状态徽章显示正确
   ```

2. **拆解任务测试**
   ```
   1. 选择一个 pending 批次
   2. 点击"开始拆解"按钮
   3. 验证进度条开始更新
   4. 验证 Console Logger 显示日志
   5. 等待任务完成，验证结果展示
   ```

3. **批量拆解测试**
   ```
   1. 点击"批量拆解"按钮
   2. 验证所有 pending 批次开始拆解
   3. 验证批量进度统计正确
   4. 验证任务依次完成
   ```

### 代码审查

1. 检查所有新建文件的类型定义
2. 检查 Props 接口是否完整
3. 检查是否有未使用的导入
4. 检查是否有 `any` 类型
5. 检查是否有重复代码

### 性能测试

1. 使用 React DevTools Profiler 检查组件渲染
2. 验证切换标签页时无不必要的重渲染
3. 验证轮询不影响其他标签页性能

---

## Admin 页面重构（必须完成）

根据初步分析，Admin 页面包含以下文件：
- `Dashboard.tsx` - 管理后台首页
- `UserManagement.tsx` (248 行) - 用户管理页面
- `AIConfiguration.tsx` (394 行) - AI 配置管理页面

### 重构方案

#### 1. AIConfiguration 页面拆分（394 行）

**目录结构**：
```
frontend/src/pages/admin/AIConfiguration/
├── index.tsx                      # 主容器
├── ConfigTable.tsx                # 配置表格组件
├── ConfigModal.tsx                # 配置编辑弹窗
└── hooks/
    └── useConfigManagement.ts     # 配置管理 Hook
```

**拆分理由**：
- 包含用户配置和系统配置两个标签页
- 表格、弹窗、表单逻辑复杂
- 状态管理较多（8 个 useState）

#### 2. UserManagement 页面拆分（248 行）

**目录结构**：
```
frontend/src/pages/admin/UserManagement/
├── index.tsx                      # 主容器
├── UserTable.tsx                  # 用户表格组件
├── UserEditModal.tsx              # 用户编辑弹窗
└── hooks/
    └── useUserManagement.ts       # 用户管理 Hook
```

**拆分理由**：
- 包含用户列表、编辑、分页等功能
- 表格和弹窗逻辑可以独立

#### 3. Dashboard 页面

**评估**：Dashboard 页面相对简单，暂不拆分，但需要检查是否有复杂逻辑。

---

## 文档更新（必须完成）

重构完成后，需要更新以下文档：

### 1. 组件文档

**新建文件**：`frontend/src/pages/user/Workspace/README.md`

**内容**：
- 目录结构说明
- 各标签页组件的职责
- Custom Hooks 使用说明
- Props 接口文档
- 开发指南

### 2. 开发指南

**更新文件**：`frontend/src/CLAUDE.md`

**新增内容**：
- Workspace 组件重构说明
- 如何添加新的标签页
- 如何创建 Custom Hook
- 组件拆分最佳实践

### 3. API 文档

**更新文件**：`frontend/src/services/README.md`（如果不存在则新建）

**内容**：
- API 服务模块说明
- 各 API 方法的参数和返回值
- Mock 数据使用说明

### 4. 项目根目录文档

**更新文件**：`CLAUDE.md`

**新增内容**：
- 前端组件重构记录
- 重构后的目录结构
- 重构带来的改进

### 5. 迁移指南

**新建文件**：`docs/refactoring/workspace-migration-guide.md`

**内容**：
- 重构前后对比
- 如何查找原有代码
- 常见问题解答

---

## 实施步骤（更新版）

### 步骤 1：创建目录结构（1 天）

1. 创建 `frontend/src/pages/user/Workspace/` 目录及所有子目录
2. 创建 `frontend/src/pages/admin/AIConfiguration/` 目录
3. 创建 `frontend/src/pages/admin/UserManagement/` 目录
4. 移动原文件为新目录的 `index.tsx`

### 步骤 2-8：（与之前相同）

### 步骤 9：拆分 Admin 页面（2 天）

1. 拆分 AIConfiguration 页面（1 天）
   - 创建 ConfigTable.tsx
   - 创建 ConfigModal.tsx
   - 提取 useConfigManagement Hook
   - 测试功能

2. 拆分 UserManagement 页面（1 天）
   - 创建 UserTable.tsx
   - 创建 UserEditModal.tsx
   - 提取 useUserManagement Hook
   - 测试功能

### 步骤 10：更新文档（1 天）

1. 创建 Workspace 组件文档（0.5 天）
   - 编写 README.md
   - 更新 CLAUDE.md
   - 创建迁移指南

2. 创建 Admin 组件文档（0.5 天）
   - 编写 README.md
   - 更新开发指南

### 步骤 11：最终测试和优化（1 天）

1. 全面功能测试
2. 性能测试
3. 代码审查
4. 文档审查

---

## 预计工期（更新版）

| 阶段 | 任务 | 工期 |
|------|------|------|
| **阶段 1** | 创建目录结构 | 1 天 |
| **阶段 2** | 提取 Custom Hooks | 2 天 |
| **阶段 3** | 拆分 PLOT 标签页 | 2 天 |
| **阶段 4** | 拆分 CONFIG 标签页 | 2 天 |
| **阶段 5** | 拆分 SOURCE 标签页 | 2 天 |
| **阶段 6** | 拆分 SCRIPT 标签页 | 1 天 |
| **阶段 7** | 拆分 AGENTS 和 SKILLS 标签页 | 1 天 |
| **阶段 8** | 重构主容器 | 1 天 |
| **阶段 9** | 拆分 Admin 页面 | 2 天 |
| **阶段 10** | 更新文档 | 1 天 |
| **阶段 11** | 最终测试和优化 | 1 天 |
| **总计** | | **16 天** |

**注意**：
- 可以分阶段实施，优先完成 Workspace 重构（12 天）
- Admin 页面重构和文档更新可以并行进行（3 天）
- 总工期约 2-3 周

---

## 验收标准（更新版）

### Workspace 页面验收

（与之前相同）

### Admin 页面验收

- [ ] **AIConfiguration 页面**
  - [ ] 用户配置标签页正常
  - [ ] 系统配置标签页正常
  - [ ] 配置创建功能正常
  - [ ] 配置编辑功能正常
  - [ ] 配置删除功能正常
  - [ ] 配置克隆功能正常

- [ ] **UserManagement 页面**
  - [ ] 用户列表加载正常
  - [ ] 用户搜索功能正常
  - [ ] 用户编辑功能正常
  - [ ] 分页功能正常

### 文档验收

- [ ] Workspace README.md 完整且清晰
- [ ] Admin README.md 完整且清晰
- [ ] CLAUDE.md 更新完整
- [ ] 迁移指南清晰易懂
- [ ] API 文档完整

---

## 关键约束（重申）

### ⚠️ 必须遵守

1. **UI 样式不变**：
   - 所有 className 保持不变
   - 所有样式类保持不变
   - 布局结构保持不变
   - 颜色、间距、字体等视觉效果完全一致

2. **功能不变**：
   - 所有交互逻辑保持不变
   - 所有 API 调用保持不变
   - 所有状态管理逻辑保持不变（只是位置改变）

3. **重构原则**：
   - 只做结构重构，不做功能改进
   - 只做代码拆分，不做逻辑优化
   - 保持向后兼容

---

## 风险与缓解（更新版）

### 风险 4：UI 样式意外改变

**风险**：重构过程中可能不小心修改了样式

**缓解**：
- 使用 Git 对比工具检查每次修改
- 截图对比重构前后的页面
- 使用 Storybook 或视觉回归测试工具
- 每个组件拆分后立即测试 UI

### 风险 5：文档不完整

**风险**：文档更新不及时或不完整

**缓解**：
- 在重构过程中同步更新文档
- 使用文档模板确保完整性
- 代码审查时检查文档
- 让其他开发者试用并反馈


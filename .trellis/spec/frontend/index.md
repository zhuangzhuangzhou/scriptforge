# AI ScriptFlow 前端开发规范

## 1. 技术栈规范 (Tech Stack)

| 核心组件 | 版本 | 选型说明 |
|-----------|-------------|-------------|
| **React** | `^18.2.0` | 函数式组件 + Hooks 范式 |
| **Vite** | `^5.0.8` | 高性能构建工具与 HMR |
| **TypeScript** | `^5.2.2` | 严格模式开启，禁止隐式 any |
| **UI System** | **Ant Design** `^5.12.0` (基础) + **TailwindCSS** `^3.4.17` (样式) | 混合架构 |
| **State Mgmt** | **Zustand** `^4.4.7` | 轻量级原子状态管理 |
| **Animation** | **Framer Motion** `^12.0.0` | 复杂交互动效 |
| **HTTP** | **Axios** `^1.6.2` | 带拦截器的请求封装 |

## 2. 代码风格与规范 (Code Standards)

### 2.1 格式化 (Linting)
- **规则集**: `eslint:recommended` + `@typescript-eslint/recommended` + `react-hooks/recommended`
- **主要规则**:
    - **引号**: 单引号 (`'`)
    - **分号**: 必须使用 (`;`)
    - **类型**: 避免 `any`，接口类型定义优先 (`interface`)
    - **变量**: 禁止未使用的变量 (`no-unused-vars`)
    - **导出**: 每个文件仅导出一个主要组件 (`export default`)

### 2.2 目录结构补充
```text
src/
├── services/
│   ├── api.ts              # Axios 实例与拦截器
│   └── mockData.ts         # Mock 数据
├── store/                  # (目前为空目录) Zustand Store 预留位置
├── types.ts                # 全局 TypeScript 接口定义
├── index.css               # Tailwind 指令与全局样式
├── components/
│   ├── ui/                 # 基础 Glass UI 组件 (GlassTabs, GlassInput, GlassSelect, GlassTable)
│   ├── modals/             # 弹窗组件目录
│   ├── WorkflowEditor/     # Agent 工作流可视化编辑器
│   ├── InputGroup.tsx      # [DEPRECATED] 请移除重复文件，使用 ui/InputGroup.tsx
│   ├── ConsoleLogger.tsx   # 日志控制台
│   └── ...
```

## 3. 核心架构模式 (Architecture Patterns)

### 3.1 API 通信层
- **位置**: `src/services/api.ts`
- **实现**:
    - **Base URL**: `import.meta.env.VITE_API_BASE_URL`
    - **Token 注入**: Request Interceptor 自动读取 `localStorage`
    - **错误处理**: Response Interceptor 统一捕获 401 并重定向至 `/login`
    - **Mock 支持**: 通过 `VITE_USE_MOCK` 环境变量切换

### 3.2 状态管理 (Zustand)
- **原则**:
    - UI 局部状态使用 `useState`
    - 跨组件/全局业务状态使用 `create()` 创建 Store
- **命名**: Hook 命名统一为 `use{StoreName}Store` (例如 `useUserStore`)

### 3.3 组件与样式
- **混合模式**:
    - **布局/容器**: 使用 Tailwind Utility Classes (如 `flex items-center p-4`)
    - **交互组件**: 使用 Ant Design (如 `<Button>`, `<Modal>`)，并通过 Tailwind 类名覆盖默认样式
    - **动效组件**: 使用 `<motion.div>` 包裹实现进入/退出动画

## 4. UI/UX 风格指南 (Style Guide)

遵循 **未来感 / 赛博朋克 / 高科技 (Futuristic High-Tech)** 设计语言。

### 🎨 配色方案 (Color Palette)
- **背景层**: 全局深色底色 `bg-slate-950` (#020617) 及 `bg-slate-900`。
- **容器层**: 广泛使用 **Glassmorphism (玻璃拟态)**。
  - 类名参考: `backdrop-blur-xl bg-slate-900/60 border border-slate-800/60 shadow-2xl`。
- **主色调 (AI 活动)**: 青色 `text-cyan-400` (#22d3ee) 用于高亮、进度条。
- **次色调 (专业/升级)**: 蓝色 `text-blue-500` 和紫色 `text-purple-500`。
- **状态色**:
  - 成功 (Approved): `text-green-400`
  - 警告 (Enterprise/Warning): `text-amber-400`
  - 错误 (Error): `text-red-400`
- **文字**: 高对比度白色 `text-white` (标题)，静默灰色 `text-slate-400` (副标题)。

### ✨ 视觉特效与微交互
- **渐变 (Gradients)**: 统一使用边框渐变或文字剪裁渐变 (`bg-clip-text`)。
- **动画 (Framer Motion)**:
  - 弹窗进入: `scale`, `opacity` 组合动效。
  - 页面切换: 滑动进入动效。
  - 按钮反馈: 点击时使用 `whileTap={{ scale: 0.98 }}`。
- **扫描光效 (Scanning Light)**: 在卡片悬停时显示顶部渐变扫描条。

### 🧩 Glass UI 组件库 (Glass Components)

为了避免全局 CSS 污染并保持样式统一，请使用以下封装组件替代原生 Ant Design 组件：

#### 基础 UI 组件
| 组件 | 替代组件 | 用途 |
|------|---------|------|
| `GlassInput` | `Input` | 毛玻璃背景输入框 |
| `GlassTextArea` | `Input.TextArea` | 毛玻璃背景文本域 |
| `GlassSelect` | `Select` | 统一的暗色下拉菜单 |
| `GlassTable` | `Table` | 透明背景数据表格 |
| `GlassDatePicker` | `DatePicker` | 深色主题日期选择器 |
| `GlassRangePicker` | `RangePicker` | 深色主题日期范围选择器 |
| `GlassTabs` | `Tabs` | 透明背景卡片式标签切换 |
| `GlassCard` | `Card` | 玻璃拟态卡片容器 |

#### 弹窗组件
| 组件 | 用途 |
|------|------|
| `GlassModal` | 详情展示弹窗（替代 Drawer） |
| `ConfirmModal` | 确认操作弹窗（删除、停止等危险操作） |

#### 功能弹窗组件
| 组件 | 用途 |
|------|------|
| `CreateProjectModal` | 创建项目弹窗 |
| `RechargeModal` | 积分充值弹窗 |
| `BillingModal` | 账单管理弹窗 |
| `TierComparisonModal` | 套餐对比弹窗 |
| `AgentConfigModal` | Agent 配置弹窗 |
| `GlobalSettingsModal` | 全局设置弹窗 |
| `QuotaLimitModal` | 配额限制提示弹窗 |

#### 功能组件
| 组件 | 用途 |
|------|------|
| `ConsoleLogger` | 控制台日志显示组件 |
| `ConfigSelector` | 配置选择器 |
| `SkillSelector` | 技能选择器 |
| `WorkflowEditor` | 工作流可视化编辑器 |
| `AICopilot` | AI 助手组件 |
| `MarkdownEditor` | Markdown 编辑器 |

> **注意**: 详情展示类场景（如日志详情、任务详情）应使用 `GlassModal` 而非 `Drawer`，以保持 UI 风格统一。

**组件目录结构**:
```text
src/
├── components/
│   ├── ui/                    # Glass UI 基础组件
│   │   ├── GlassInput.tsx
│   │   ├── GlassSelect.tsx
│   │   ├── GlassTable.tsx
│   │   ├── GlassTabs.tsx
│   │   ├── GlassModal.tsx
│   │   ├── GlassCard.tsx
│   │   └── GlassDatePicker.tsx
│   ├── modals/                # 功能弹窗组件
│   │   ├── ConfirmModal.tsx
│   │   ├── CreateProjectModal.tsx
│   │   ├── RechargeModal.tsx
│   │   ├── BillingModal.tsx
│   │   └── ...
│   └── ...
```

**使用示例**:
```tsx
import { GlassTabs } from '../ui/GlassTabs';
import { GlassInput } from '../ui/GlassInput';
import { GlassSelect } from '../ui/GlassSelect';
import { GlassDatePicker } from '../ui/GlassDatePicker';
import { GlassCard } from '../ui/GlassCard';
import { ConfirmModal } from '../modals/ConfirmModal';

<GlassTabs items={...} />
<GlassInput placeholder="搜索..." />
<GlassSelect options={...} />
<GlassDatePicker onChange={...} />
<GlassCard>内容</GlassCard>

<ConfirmModal
  open={showModal}
  onCancel={() => setShowModal(false)}
  onConfirm={handleConfirm}
  title="确认操作"
  content="确定要执行此操作吗？"
/>
```

**Drawer → GlassModal 迁移指南**:

| Drawer 属性 | GlassModal 属性 | 说明 |
|-------------|-----------------|------|
| `visible` | `open` | 控制显示状态 |
| `onClose` | `onCancel` | 关闭回调 |
| `placement` | - | 移除，Modal 默认居中 |
| `width` | `width` | 保持不变 |
| - | `footer={null}` | 隐藏默认按钮（详情展示场景） |

```tsx
// Before (Drawer)
<Drawer
  title="详情"
  placement="right"
  width={700}
  open={visible}
  onClose={handleClose}
>
  {content}
</Drawer>

// After (GlassModal)
<GlassModal
  title="详情"
  width={700}
  open={visible}
  onCancel={handleClose}
  footer={null}
>
  {content}
</GlassModal>
```

### 🐛 Glass 组件常见问题

#### 输入框双重边框

**症状**: GlassInput 组件显示两层边框

**原因**: `ant-input-affix-wrapper` 本身有边框，内部的 `ant-input` 也有边框

**修复**: 为 affix-wrapper 内部的 input 移除边框

```css
.glass-input-wrapper .ant-input-affix-wrapper .ant-input {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}
```

#### 占位符颜色看不清

**症状**: 占位符文字颜色太暗，难以辨认

**修复**: 使用 slate-500 (#64748b)

```css
.glass-input-wrapper .ant-input::placeholder,
.glass-select-wrapper .ant-select-selection-placeholder {
  color: #64748b !important;
}
```

### 🔧 WorkflowEditor 组件

**用途**: Agent 工作流可视化编辑器，支持拖拽排序、双模式编辑。

**目录结构**:
```text
WorkflowEditor/
├── index.tsx              # 主组件（工具栏 + 画布 + 配置面板）
├── WorkflowCanvas.tsx     # 画布区域（拖拽排序）
├── StepNode.tsx           # 步骤节点卡片
├── StepConfigPanel.tsx    # 右侧配置面板
├── SkillSelector.tsx      # Skill 选择器（按分类分组）
├── types.ts               # 类型定义
└── utils.ts               # 工具函数（JSON 转换、验证）
```

**核心功能**:
- 可视化/JSON 双模式编辑，支持切换
- 拖拽排序步骤（使用 `@dnd-kit/core`）
- 支持 Sequential/Loop 两种工作流类型
- 步骤配置：Skill 选择、输入参数、输出键、条件、失败策略
- 变量引用自动补全（`${context.xxx}`, `${step_id.xxx}`）

**使用示例**:
```tsx
import WorkflowEditor, { WorkflowConfig, SkillInfo } from '../components/WorkflowEditor';

const [workflow, setWorkflow] = useState<WorkflowConfig>({
  type: 'sequential',
  steps: [],
});

<WorkflowEditor
  value={workflow}
  onChange={setWorkflow}
  availableSkills={skills}
/>
```

**依赖**: `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`

**使用位置**: `src/pages/admin/Agents/AgentEditor.tsx`

### ⌨️ 排版 (Typography)
- **UI 文本**: `Inter`, `Noto Sans SC` (苹方/雅黑回退)。
- **技术文本**: 代码、日志、Token 计数统一使用 **`JetBrains Mono`**。

## 5. 核心功能逻辑

### 🏰 路由与视图管理 (Routing)
**强烈推荐使用 React Router** (`react-router-dom`) 进行页面导航：
- `/login` -> 登录页
- `/dashboard` -> 项目管理
- `/workspace/:projectId` -> 剧本工作台
*注：不再建议使用 `currentView` 手动管理状态，以支持浏览器历史记录和 URL 分享。*

### 🔒 类型安全 (Type Safety)
- **OpenAPI 集成**: 建议使用 `openapi-typescript` 等工具，根据后端生成的 OpenAPI Schema (`swagger.json`) 自动生成前端 TypeScript 类型，确保前后端类型严格同步。

### 💎 会员等级与配额 (User Tiers)
- **配置源**: `TIER_LIMITS` 等业务规则应优先从后端 API (`/api/v1/config` 或 `/user/quota`) 获取，而非仅在前端硬编码，以确保安全性和动态更新。

## 6. 错误处理与性能优化 (Error Handling & Performance)

### 🛡️ 错误边界 (Error Boundary)

**问题**: React 组件渲染错误会导致整个应用崩溃（白屏/黑屏）

**解决方案**: 使用错误边界包裹关键组件

```tsx
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('组件渲染错误:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Alert
          message="组件加载失败"
          description={this.state.error?.message || '未知错误'}
          type="error"
          showIcon
        />
      );
    }
    return this.props.children;
  }
}

// 使用
<ErrorBoundary>
  <YourComponent />
</ErrorBoundary>
```

**适用场景**:
- 标签页内容
- 动态加载的组件
- 第三方组件集成

### ⚡ 标签页懒加载 (Tabs Lazy Loading)

**问题**: GlassTabs 的 `items` 中直接包含 `children: <Component />` 会导致所有标签页组件立即渲染

**错误示例**:
```tsx
// ❌ 错误：所有组件立即渲染
const tabItems = [
  { key: 'tab1', label: 'Tab 1', children: <Tab1Component /> },
  { key: 'tab2', label: 'Tab 2', children: <Tab2Component /> },
];
```

**正确示例**:
```tsx
// ✅ 正确：按需渲染
const [activeTab, setActiveTab] = useState('tab1');

const renderTabContent = () => {
  switch (activeTab) {
    case 'tab1': return <Tab1Component />;
    case 'tab2': return <Tab2Component />;
    default: return null;
  }
};

const tabItems = [
  { key: 'tab1', label: 'Tab 1' },  // 不包含 children
  { key: 'tab2', label: 'Tab 2' },
];

return (
  <>
    <GlassTabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
    <ErrorBoundary key={activeTab}>
      {renderTabContent()}
    </ErrorBoundary>
  </>
);
```

**性能提升**:
- 减少初始渲染工作量（5 个组件 → 1 个组件）
- 降低内存占用
- 加快页面加载速度

**参考实现**: `frontend/src/pages/admin/ModelManagement.tsx`

### 🔍 常见错误排查

| 症状 | 可能原因 | 解决方案 |
|------|---------|---------|
| 标签页黑屏 | 子组件渲染错误 | 添加错误边界 + 检查控制台 |
| 页面加载慢 | 所有标签页提前渲染 | 实现懒加载 |
| 组件导入错误 | 缺少必要的导入 | 检查 TypeScript 编译错误 |
| API 调用失败 | 后端未启动或路径错误 | 检查网络面板 + 后端日志 |

## 7. AI 工作流集成 (AI Integration)

### 🤖 模拟流程 (Simulation)
目前 `Workspace.tsx` 使用 Mock 函数模拟 AI 处理链：
1. **Tokenization** (分词分析)
2. **RAG Retrieval** (知识库检索)
3. **AI Inference** (大模型推理)

### 📜 日志系统 (ConsoleLogger)
向控制台发送日志的规范格式：
```typescript
{ id: string, timestamp: string, type: 'info'|'thinking'|'success'|'error', message: string }
```

## 9. 状态管理最佳实践 (State Management Best Practices)

### 9.1 乐观更新模式 (Optimistic Update)

**问题**: 调用 API 启动任务后，按钮状态没有立即更新，用户体验不佳

**解决方案**: 在 API 调用成功后，立即更新本地状态，不等待后端轮询

```tsx
// ✅ 正确：乐观更新
const handleStartTask = async () => {
  try {
    const res = await api.startTask(taskId);
    setTaskId(res.data.task_id);

    // 立即更新本地状态，使 UI 响应更快
    if (selectedItem && selectedItem.id === taskId) {
      setSelectedItem({
        ...selectedItem,
        status: 'processing'  // 乐观更新状态
      });
    }
  } catch (err) {
    // 失败时恢复原状态
    setSelectedItem(originalItem);
    message.error('启动失败');
  }
};

// ❌ 错误：仅依赖轮询更新状态
const handleStartTask = async () => {
  const res = await api.startTask(taskId);
  setTaskId(res.data.task_id);
  // 按钮状态要等轮询才能更新，用户体验差
};
```

**适用场景**:
- 启动/停止任务按钮
- 状态切换操作
- 任何需要即时反馈的交互

### 9.2 按钮禁用条件设计

**问题**: 按钮禁用条件过于严格，导致用户无法操作

**最佳实践**: 明确列出所有需要启用按钮的状态

```tsx
// ✅ 正确：明确列出可操作的状态
disabled={
  !!taskId ||                    // 有任务正在执行
  isRunning ||                   // 批量任务运行中
  items.filter(i =>
    i.status === 'pending' ||
    i.status === 'failed'        // 包含失败状态，允许重试
  ).length === 0
}

// ❌ 错误：只考虑 pending 状态
disabled={items.filter(i => i.status === 'pending').length === 0}
// 问题：failed 状态的项目无法重试
```

---

## 10. 流式数据处理 (Streaming Data)

### 10.1 追加模式 vs 覆盖模式

**问题**: 处理 WebSocket 流式数据时，使用覆盖模式会导致数据不连续

**场景**: System Console raw 模式下，LLM 返回的 JSON 片段需要连续追加显示

**错误示例**（覆盖模式）:
```tsx
// ❌ 错误：累积到中间状态，然后用完整内容覆盖
const [streamContent, setStreamContent] = useState('');

// onStreamChunk 回调中只做累积
onStreamChunk: (chunk) => {
  setStreamContent(prev => prev + chunk);  // 只累积
},

// useEffect 中覆盖更新
useEffect(() => {
  if (streamContent) {
    updateStreamLog(streamContent);  // 每次都用完整内容覆盖旧内容
  }
}, [streamContent]);
```

**正确示例**（追加模式）:
```tsx
// ✅ 正确：直接追加内容到日志
onStreamChunk: (stepName, chunk) => {
  appendStreamLog(chunk);  // 直接追加，不经过中间状态
},
```

**`appendStreamLog` 实现** (`useConsoleLogger.ts`):
```tsx
const appendStreamLog = useCallback((chunk: string) => {
  setLogs(prev => {
    const lastIndex = prev.length - 1;

    if (lastIndex >= 0 && prev[lastIndex].type === 'stream') {
      // 追加内容到最后一个流式日志
      const updated = [...prev];
      updated[lastIndex] = {
        ...updated[lastIndex],
        message: updated[lastIndex].message + chunk
      };
      return updated;
    } else {
      // 创建新的流式日志
      return [...prev, {
        id: `stream-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString(),
        type: 'stream',
        message: chunk
      }];
    }
  });
}, []);
```

**为什么追加模式更好**:
1. **实时性**: 每个片段立即显示，无需等待累积
2. **减少状态**: 不需要额外的 `streamContent` 中间状态
3. **避免覆盖**: 不会因 React 状态更新时机问题导致内容丢失

### 10.2 回调 vs useEffect

**推荐**: 在回调中直接处理，而非依赖 useEffect 累积

| 方式 | 优点 | 缺点 |
|------|------|------|
| **回调直接处理** | 实时性高，状态少 | 需要确保回调稳定性 |
| **useEffect 累积** | 逻辑集中 | 增加中间状态，可能有覆盖问题 |

---

## 11. 长时间操作的用户反馈规范

### 11.1 核心原则

**问题**: 后端操作（如停止任务、批量处理）可能需要较长时间，前端如果没有即时反馈，用户会感到困惑

**解决方案**: 立即显示操作状态，提供清晰的进度反馈

### 11.2 长时间操作的处理模式

#### 模式一：确认对话框 + Loading 状态

**适用场景**: 不可逆操作或需要用户确认的操作（如停止任务）

```tsx
// 状态定义
const [isStopping, setIsStopping] = useState(false);

// 处理函数
const handleStopTask = async () => {
  // 1. 弹出确认对话框
  Modal.confirm({
    title: '确认停止',
    content: '确定要停止当前拆解任务吗？停止后已排队的后续任务也将被取消。',
    okText: '确认停止',
    okType: 'danger',
    onOk: async () => {
      // 2. 设置 loading 状态
      setIsStopping(true);
      try {
        const res = await api.stopTask(taskId);

        // 3. 显示操作结果消息
        const { cancelled_count, token_deducted } = res.data;
        let successMsg = res.data.message || '已停止拆解任务';
        if (token_deducted > 0) {
          successMsg += `（扣除 ${token_deducted} 积分）`;
        }
        message.success(successMsg);

        // 4. 清理状态并刷新
        setTaskId(null);
        fetchBatches();
      } catch (err) {
        message.error('停止任务失败');
      } finally {
        setIsStopping(false);
      }
    }
  });
};

// 按钮 UI
<button
  onClick={handleStopTask}
  disabled={isStopping}
  className="..."
>
  {isStopping ? (
    <>
      <Loader2 size={14} className="animate-spin" />
      停止中...
    </>
  ) : (
    <>
      <X size={14} />
      停止拆解
    </>
  )}
</button>
```

#### 模式二：即时消息 + 后台处理

**适用场景**: 可逆操作或不需要用户确认的操作

```tsx
const handleRefresh = async () => {
  // 1. 立即显示 loading 消息
  const hide = message.loading('正在刷新...', 0);

  try {
    await fetchBatches();
  } finally {
    // 2. 操作完成后隐藏 loading
    hide();
    // 3. 显示成功消息
    message.success('刷新完成');
  }
};
```

### 11.3 后端响应设计

**后端应返回详细的操作结果信息**，便于前端展示：

```json
{
  "task_id": "xxx",
  "status": "cancelled",
  "cancelled_count": 3,
  "message": "已停止任务（含 2 个后续排队任务），已扣除 Token 费用 50 积分",
  "token_deducted": 50
}
```

### 11.4 Loading 状态命名规范

| 操作类型 | 状态变量 | 显示文案 |
|---------|---------|---------|
| 停止任务 | `isStopping` | "停止中..." |
| 删除操作 | `isDeleting` | "删除中..." |
| 保存操作 | `isSaving` | "保存中..." |
| 上传操作 | `isUploading` | "上传中..." |
| 批量处理 | `isProcessing` | "处理中..." |

### 11.5 通用确认弹窗组件 (ConfirmModal)

**组件位置**: `frontend/src/components/modals/ConfirmModal.tsx`

**解决的问题**: 统一所有危险操作的确认弹窗样式，避免使用 `window.confirm` 和分散的 Modal.confirm

**组件特性**:
- 支持四种图标类型: `warning`, `success`, `info`, `danger`
- 支持三种确认按钮: `primary`, `danger`, `success`
- 自动居中显示，毛玻璃遮罩背景
- 统一的 Glassmorphism 风格

**Props 定义**:
```typescript
interface ConfirmModalProps {
  open: boolean;                    // 控制弹窗显示
  onCancel: () => void;            // 取消回调
  onConfirm: () => void;           // 确认回调
  title?: React.ReactNode;         // 弹窗标题
  content?: React.ReactNode;        // 弹窗内容（支持 JSX）
  confirmText?: string;            // 确认按钮文字
  cancelText?: string;             // 取消按钮文字
  confirmType?: 'primary' | 'danger' | 'success';  // 确认按钮类型
  iconType?: 'warning' | 'success' | 'info' | 'danger';  // 图标类型
  loading?: boolean;               // 加载状态
  width?: number;                  // 弹窗宽度
}
```

**使用示例**:

```tsx
// 1. 在组件中导入
import ConfirmModal from '../../../components/modals/ConfirmModal';

// 2. 添加状态
const [deleteModalOpen, setDeleteModalOpen] = useState(false);
const [deletingId, setDeletingId] = useState<string | null>(null);
const [isDeleting, setIsDeleting] = useState(false);

// 3. 处理删除点击
const handleDeleteClick = (e: React.MouseEvent, id: string) => {
  e.stopPropagation();
  setDeletingId(id);
  setDeleteModalOpen(true);
};

// 4. 执行删除
const handleConfirmDelete = async () => {
  if (!deletingId) return;
  setIsDeleting(true);
  try {
    await api.delete(deletingId);
    message.success('删除成功');
    setDeleteModalOpen(false);
    fetchData();
  } finally {
    setIsDeleting(false);
  }
};

// 5. 在 JSX 中添加弹窗
<ConfirmModal
  open={deleteModalOpen}
  onCancel={() => {
    setDeleteModalOpen(false);
    setDeletingId(null);
  }}
  onConfirm={handleConfirmDelete}
  title="确认删除"
  content={
    <div className="text-left">
      <p className="text-slate-300 mb-3">
        确定要删除该项目吗？此操作不可撤销。
      </p>
      <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3">
        <div className="flex gap-2 items-start">
          <Trash2 size={14} className="text-red-400 mt-0.5" />
          <p className="text-xs text-red-300">
            删除后数据将无法恢复。
          </p>
        </div>
      </div>
    </div>
  }
  confirmText="确认删除"
  confirmType="danger"
  iconType="danger"
  loading={isDeleting}
/>
```

**适用场景**:
- ⚠️ 危险操作确认（删除、停止、取消）
- ⚠️ 不可逆操作确认
- ⚠️ 需要用户明确确认的操作

**图标与按钮类型对应**:
| 操作类型 | iconType | confirmType | 说明 |
|---------|----------|-------------|------|
| 删除 | `danger` | `danger` | 红色警告 |
| 停止 | `danger` | `danger` | 红色警告 |
| 成功提示 | `success` | `success` | 绿色确认 |
| 普通确认 | `info` | `primary` | 蓝色默认 |

### 10.7 禁止的行为

```tsx
// ❌ 错误：没有任何反馈
const handleStopTask = async () => {
  await api.stopTask(taskId);
  fetchBatches();
};

// ❌ 错误：没有禁用按钮，用户可以重复点击
const handleStopTask = async () => {
  await api.stopTask(taskId);
  message.success('已停止');
};

// ❌ 错误：只有文字提示，没有 loading 动画
const handleStopTask = async () => {
  message.loading('正在停止...');
  await api.stopTask(taskId);
  message.destroy();
};
```

---

## 12. ⚠️ 铁律：禁止擅自修改 UI/UX

### 12.1 绝对禁止的行为

除非用户**明确请求**，否则**严禁**修改：
- 样式 (CSS, Tailwind classes)
- 图标 (Lucide, Ant Design Icons)
- 布局 (组件结构、位置)
- 字段名称或显示逻辑
- 路由架构 (React Router 结构)

### 12.2 如果认为需要修改
1. **停止**
2. **询问**: "这个改动会影响 UI/UX，您同意吗？"
3. **等待明确许可**

### 12.3 违反后果
- 历史教训：一次"顺手优化"导致所有子页面乱套
- 教训：设计风格是用户的选择，不应被 AI 擅自改变

### 12.4 验证流程
任何前端代码修改后：
1. **手动打开所有页面**检查是否正常
2. **检查路由跳转**是否正常
3. **检查弹窗**能否正确打开/关闭

> **记住**: 保护用户的设计，比"优化"它更重要。

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

- **GlassTabs**: 替代 `Tabs`，提供透明背景卡片式切换。
- **GlassInput / GlassTextArea**: 替代 `Input` / `Input.TextArea`，提供毛玻璃背景与发光边框。
- **GlassSelect**: 替代 `Select`，解决 Dropdown 挂载点样式问题，提供统一的暗色下拉菜单。
- **GlassTable**: 替代 `Table`，提供透明背景数据表格。
- **GlassModal**: 替代 `Modal` 和 `Drawer`，提供磨砂玻璃背景弹窗。
- **GlassRangePicker**: 替代 `RangePicker`，提供深色主题日期范围选择器。

> **注意**: 详情展示类场景（如日志详情、任务详情）应使用 `GlassModal` 而非 `Drawer`，以保持 UI 风格统一。

**使用示例**:
```tsx
import { GlassTabs } from '../ui/GlassTabs';
import { GlassInput } from '../ui/GlassInput';
import { GlassSelect } from '../ui/GlassSelect';
import { GlassRangePicker } from '../ui/GlassDatePicker';

<GlassTabs items={...} />
<GlassInput placeholder="搜索..." />
<GlassSelect options={...} />
<GlassRangePicker onChange={...} />
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

---

## 8. ⚠️ 铁律：禁止擅自修改 UI/UX

### 8.1 绝对禁止的行为
除非用户**明确请求**，否则**严禁**修改：
- 样式 (CSS, Tailwind classes)
- 图标 (Lucide, Ant Design Icons)
- 布局 (组件结构、位置)
- 字段名称或显示逻辑
- 路由架构 (React Router 结构)

### 8.2 如果认为需要修改
1. **停止**
2. **询问**: "这个改动会影响 UI/UX，您同意吗？"
3. **等待明确许可**

### 8.3 违反后果
- 历史教训：一次"顺手优化"导致所有子页面乱套
- 教训：设计风格是用户的选择，不应被 AI 擅自改变

### 8.4 验证流程
任何前端代码修改后：
1. **手动打开所有页面**检查是否正常
2. **检查路由跳转**是否正常
3. **检查弹窗**能否正确打开/关闭

> **记住**: 保护用户的设计，比"优化"它更重要。

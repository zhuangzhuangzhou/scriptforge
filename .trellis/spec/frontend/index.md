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
│   ├── ui/                 # 基础 UI 组件 (InputGroup.tsx 应统一至此处)
│   ├── modals/             # 弹窗组件目录
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

## 6. AI 工作流集成 (AI Integration)

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

## 7. ⚠️ 铁律：禁止擅自修改 UI/UX

### 7.1 绝对禁止的行为
除非用户**明确请求**，否则**严禁**修改：
- 样式 (CSS, Tailwind classes)
- 图标 (Lucide, Ant Design Icons)
- 布局 (组件结构、位置)
- 字段名称或显示逻辑
- 路由架构 (React Router 结构)

### 7.2 如果认为需要修改
1. **停止**
2. **询问**: "这个改动会影响 UI/UX，您同意吗？"
3. **等待明确许可**

### 7.3 违反后果
- 历史教训：一次"顺手优化"导致所有子页面乱套
- 教训：设计风格是用户的选择，不应被 AI 擅自改变

### 7.4 验证流程
任何前端代码修改后：
1. **手动打开所有页面**检查是否正常
2. **检查路由跳转**是否正常
3. **检查弹窗**能否正确打开/关闭

> **记住**: 保护用户的设计，比"优化"它更重要。

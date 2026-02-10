# AI ScriptFlow 前端开发指南 (Frontend Development Guide)

## 1. 项目架构 (Project Structure)

本项目基于 React 18+, TypeScript 和 Tailwind CSS 构建。采用视图状态 (ViewState) 管理与路由守卫相结合的架构。

```text
src/
├── components/
│   ├── ui/
│   │   └── InputGroup.tsx      # 带发光动效的定制输入组件
│   ├── modals/
│   │   ├── CreateProjectModal.tsx  # 带等级权限校验的项目创建窗口
│   │   ├── AgentConfigModal.tsx    # 智能体参数微调
│   │   ├── GlobalSettingsModal.tsx # 模型与分词策略配置
│   │   ├── BillingModal.tsx        # 账单明细
│   │   └── RechargeModal.tsx       # 计划升级 (Tier Management)
│   ├── AICopilot.tsx           # 右侧悬浮 AI 助手 (上下文感知)
│   ├── ConsoleLogger.tsx       # 底部实时日志控制台 (思考过程展示)
│   └── MainLayout.tsx          # 统一应用外壳
├── pages/
│   ├── auth/
│   │   ├── Login.tsx           # 玻璃拟态登录页
│   │   └── Register.tsx        # 注册页
│   └── user/
│       ├── Dashboard.tsx       # 项目管理网格
│       └── Workspace.tsx       # 集成工作台 (Workflow 核心)
└── context/
    └── AuthContext.tsx         # 全局认证状态
```

## 2. UI/UX 风格指南 (Style Guide)

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

## 3. 核心功能逻辑

### 🏰 视图管理 (View State)
在 `App.tsx` 中通过 `currentView` 维护：
- `LOGIN` -> `DASHBOARD` -> `WORKSPACE` (路由跳转与组件挂载)。

### 💎 会员等级与配额 (User Tiers)
权限控制逻辑在 `TIER_LIMITS` 常量中定义：
- **FREE**: 1项目上限，3章批次处理。
- **CREATOR**: 5项目上限，6章批次处理。
- **STUDIO**: 20项目上限，12章批次处理，解锁“自定义 Skill”。
- **ENTERPRISE**: 无限额度，解锁“自定义模型 API”。

## 4. AI 工作流集成 (AI Integration)

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

## 5. 开发最佳实践
- **性能**: 使用 `AnimatePresence` 处理组件卸载动画；使用 `useRef` 管理日志和对话的自动滚动。
- **扩展性**: 添加新图标请从 `lucide-react` 导入。
- **响应式**: 布局应同时支持移动端 (`flex-col`) 和桌面端 (`flex-row`)。

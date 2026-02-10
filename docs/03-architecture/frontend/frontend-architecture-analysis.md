# AI ScriptFlow 前端架构与功能全面分析

> 生成时间：2026-02-08
> 分析范围：页面结构、组件体系、用户流程、UI 模式

---

## 📱 页面清单与功能

### 核心业务页面

#### **Dashboard (仪表盘)**
- **路径**: `/dashboard`
- **文件**: `frontend/src/pages/user/Dashboard.tsx`
- **核心功能**:
  - 项目列表展示（卡片式布局）
  - 创建新项目（弹窗）
  - 项目快捷操作（编辑、删除）
  - 项目状态可视化（draft, uploaded, ready, parsing, scripting, completed）
  - 随机图标分配系统（15种风格）
- **特色**:
  - 响应式卡片布局
  - Framer Motion 动画
  - 用户协议/隐私政策弹窗
  - 配额限制检查

#### **Workspace (项目工作台)**
- **路径**: `/workspace/:projectId`
- **文件**: `frontend/src/pages/user/Workspace.tsx`
- **核心功能**:
  - **6个主要Tab**:
    - `CONFIG`: 项目配置（名称、类型、描述、批次大小）
    - `SOURCE`: 小说原文管理（上传、拆分、章节浏览）
    - `AGENTS`: AI Agent 配置（4个预设 Agent）
    - `SKILLS`: AI Skill 选择器
    - `PLOT`: 剧情拆解（批次管理、任务启动）
    - `SCRIPT`: 剧本生成（剧集列表、内容预览）
  - 实时日志控制台（ConsoleLogger）
  - AI Copilot 对话窗口
- **特色**:
  - 统一侧边栏导航
  - 实时状态同步
  - WebSocket 进度推送
  - Mock 数据模拟完整工作流

#### **PlotBreakdown (剧情拆解页)**
- **路径**: `/plot-breakdown/:projectId`
- **文件**: `frontend/src/pages/user/PlotBreakdown.tsx`
- **核心功能**:
  - 批次时间轴展示
  - 启动单批次拆解
  - Skill 选择器集成
  - 状态监控（pending, processing, completed, failed）
- **特色**:
  - Ant Design Timeline 组件
  - 实时状态刷新

#### **SkillsManagement (技能管理)**
- **路径**: `/skills`
- **文件**: `frontend/src/pages/user/SkillsManagement.tsx`
- **核心功能**:
  - 查看所有 Skill（系统 + 用户自定义）
  - 创建/编辑 Skill
  - Skill 分类（breakdown, script, analysis）
  - 模板驱动 Skill 编辑器
- **特色**:
  - Glass UI 风格
  - 代码编辑器集成
  - 权限管理（public/private/shared）

#### **ScriptGeneration (剧本生成页)**
- **路径**: `/script-generation/:projectId`
- **文件**: `frontend/src/pages/user/ScriptGeneration.tsx`
- **核心功能**:
  - 基于 PlotBreakdown 生成剧本
  - 剧集列表展示
  - 剧本内容预览
  - 质量检查报告
- **特色**:
  - Markdown 渲染
  - 实时生成进度

---

### 管理后台页面

#### **Admin Dashboard**
- **路径**: `/admin/dashboard`
- **文件**: `frontend/src/pages/admin/Dashboard.tsx`
- **核心功能**:
  - 系统概览
  - 用户统计
  - 项目统计
  - 实时监控

#### **User Management**
- **路径**: `/admin/users`
- **文件**: `frontend/src/pages/admin/UserManagement.tsx`
- **核心功能**:
  - 用户列表
  - 用户编辑（等级、配额、权限）
  - 账户状态管理

#### **AI Configuration**
- **路径**: 通过 MainLayout 顶部 Bot 图标触发弹窗
- **文件**: `frontend/src/components/modals/AIConfigurationModal.tsx`
- **核心功能**:
  - AI 配置管理（系统默认 + 用户自定义）
  - Tab 切换（我的配置 / 系统默认配置）
  - 配置分类（adapt_method, prompt_template, quality_rule）
  - 克隆系统配置为用户自定义
- **特色**:
  - Glass UI 弹窗
  - JSONB 配置编辑器
  - 实时预览

---

## 🎨 UI 组件库

### Glass UI 组件系统

#### **GlassTabs**
- **路径**: `frontend/src/components/ui/GlassTabs.tsx`
- **用途**: 磨砂玻璃风格的 Tab 切换组件
- **特色**:
  - 透明背景 + backdrop-blur
  - 激活状态高亮（cyan-400）
  - 支持 Ant Design TabsProps

#### **GlassInput / GlassTextArea**
- **路径**: `frontend/src/components/ui/GlassInput.tsx`
- **用途**: 输入框组件
- **特色**:
  - 半透明背景（slate-950/50）
  - 聚焦发光效果（cyan-500 glow）
  - 统一边框样式

#### **GlassSelect**
- **路径**: `frontend/src/components/ui/GlassSelect.tsx`
- **用途**: 下拉选择器
- **特色**:
  - 解决 Dropdown Portal 样式问题
  - 统一下拉菜单暗色主题
  - 动态生成 className

#### **GlassTable**
- **路径**: `frontend/src/components/ui/GlassTable.tsx`
- **用途**: 数据表格
- **特色**:
  - 透明背景
  - Hover 高亮
  - 分页器样式统一

#### **GlassModal**
- **路径**: `frontend/src/components/ui/GlassModal.tsx`
- **用途**: 弹窗容器
- **特色**:
  - 磨砂玻璃背景（slate-900/90 + blur-xl）
  - 统一边框与阴影
  - 支持嵌套 Modal（z-index 管理）

#### **GlassCard**
- **路径**: `frontend/src/components/ui/GlassCard.tsx`
- **用途**: 卡片容器
- **特色**:
  - 统一内边距与边框
  - Hover 动画

---

### 业务组件

#### **ConsoleLogger**
- **路径**: `frontend/src/components/ConsoleLogger.tsx`
- **用途**: 实时日志输出控制台
- **特色**:
  - 日志类型分类（info, thinking, success, error）
  - 自动滚动到底部
  - 时间戳显示

#### **AICopilot**
- **路径**: `frontend/src/components/AICopilot.tsx`
- **用途**: AI 对话助手
- **特色**:
  - 对话历史记录
  - Markdown 渲染
  - 流式输出模拟

#### **SkillSelector**
- **路径**: `frontend/src/components/SkillSelector.tsx`
- **用途**: Skill 选择器（用于 Breakdown/Script 配置）
- **特色**:
  - 多选支持
  - 按分类筛选
  - 实时预览

#### **MainLayout**
- **路径**: `frontend/src/components/MainLayout.tsx`
- **用途**: 全局布局容器
- **核心功能**:
  - 顶部导航栏
  - 用户信息展示
  - 积分/配额显示
  - 全局设置入口
  - AI 配置入口（Bot 图标）
  - 管理后台入口（Admin Badge）
- **特色**:
  - 响应式布局
  - 悬浮弹窗管理
  - 用户头像生成（Dicebear API）

---

### 弹窗组件

#### **CreateProjectModal**
- **路径**: `frontend/src/components/modals/CreateProjectModal.tsx`
- **用途**: 创建新项目
- **字段**: name, novel_type, description, batch_size, chapter_split_rule

#### **RechargeModal**
- **路径**: `frontend/src/components/modals/RechargeModal.tsx`
- **用途**: 充值/升级会员

#### **TierComparisonModal**
- **路径**: `frontend/src/components/modals/TierComparisonModal.tsx`
- **用途**: 会员等级对比

#### **BillingModal**
- **路径**: `frontend/src/components/modals/BillingModal.tsx`
- **用途**: 账单与消费记录

#### **GlobalSettingsModal**
- **路径**: `frontend/src/components/modals/GlobalSettingsModal.tsx`
- **用途**: 全局系统设置

#### **AgentConfigModal**
- **路径**: `frontend/src/components/modals/AgentConfigModal.tsx`
- **用途**: Agent 配置编辑器

---

## 🔄 用户流程

### 完整工作流

```
1. 登录注册
   ↓
2. Dashboard - 创建项目
   ↓
3. Workspace - CONFIG Tab
   - 配置项目基本信息
   - 保存项目设置
   ↓
4. Workspace - SOURCE Tab
   - 上传小说 TXT 文件
   - 执行章节拆分
   - 浏览章节列表
   ↓
5. Workspace - AGENTS/SKILLS Tab
   - 配置 AI Agent
   - 选择 Skill
   ↓
6. Workspace - PLOT Tab
   - 创建批次（按 batch_size 分组）
   - 启动剧情拆解
   - 监控任务进度
   - 查看 PlotBreakdown 结果
   ↓
7. Workspace - SCRIPT Tab
   - 启动剧本生成
   - 查看剧集列表
   - 预览剧本内容
   - 下载/导出剧本
```

### 快捷操作流程

```
Dashboard 卡片菜单：
- 编辑项目 → Workspace CONFIG
- 查看详情 → Workspace 概览
- 删除项目 → 确认弹窗
```

---

## 🎨 交互模式

### 1. 弹窗管理模式
- **全局弹窗**: AI 配置、充值、账单、设置
- **页面级弹窗**: 创建项目、Agent 配置
- **嵌套弹窗**: AI 配置编辑 → 配置详情编辑（z-index: 1050 → 1060）

### 2. 实时反馈模式
- **WebSocket 推送**: 任务进度、状态变更
- **ConsoleLogger**: 日志流式输出
- **Progress Bar**: 上传进度、处理进度

### 3. 状态可视化模式
- **项目状态**: draft (草稿), uploaded (已上传), ready (就绪), parsing (解析中), scripting (生成中), completed (完成)
- **批次状态**: pending (待处理), processing (处理中), completed (完成), failed (失败)
- **任务状态**: queued (排队), running (运行中), completed (完成), failed (失败)

### 4. 数据加载模式
- **初始加载**: Skeleton 占位符
- **分页加载**: Ant Design Pagination
- **无限滚动**: 章节列表

---

## 🛠️ 技术架构

### 状态管理
- **全局状态**: AuthContext (用户信息、登录状态)
- **本地状态**: useState (页面级数据)
- **路由参数**: useParams (projectId)
- **导航**: useNavigate (React Router)

### API 通信
- **服务层**: `frontend/src/services/api.ts`
- **拦截器**: Token 自动注入、401 重定向
- **Mock 支持**: `USE_MOCK` 环境变量切换
- **API 模块**:
  - `projectApi`: 项目管理
  - `breakdownApi`: 剧情拆解
  - `scriptApi`: 剧本生成
  - `configService`: AI 配置

### 样式系统
- **主框架**: TailwindCSS
- **组件库**: Ant Design 5.x
- **动画**: Framer Motion
- **主题**: 暗色赛博朋克风格
  - 背景：slate-950, slate-900
  - 主色：cyan-400, cyan-500
  - 强调：blue-500, purple-500
  - 成功：green-400
  - 错误：red-400

### 路由架构
```tsx
<Route path="/login" element={<Login />} />
<Route path="/register" element={<Register />} />

<Route element={<MainLayout />}>
  <Route element={<ProtectedRoute />}>
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/workspace/:projectId" element={<Workspace />} />
    <Route path="/skills" element={<SkillsManagement />} />

    <Route element={<AdminRoute />}>
      <Route path="/admin/dashboard" element={<AdminDashboard />} />
      <Route path="/admin/users" element={<UserManagement />} />
    </Route>
  </Route>
</Route>

<Route path="/" element={<Navigate to="/dashboard" replace />} />
```

---

## 🔍 发现的相关功能

### 已实现功能
1. **项目管理**: 创建、列表、详情、删除
2. **章节管理**: 上传、拆分、浏览、搜索
3. **剧情拆解**: 批次管理、任务启动、进度监控
4. **剧本生成**: 基于 PlotBreakdown 生成剧集
5. **Skill 管理**: 查看、创建、编辑、选择
6. **Agent 配置**: 预设 Agent、自定义配置
7. **AI 配置中心**: 系统配置、用户覆盖、分类管理
8. **用户管理**: 登录、注册、权限控制
9. **配额系统**: 项目数、剧集数、积分消耗

### 待完善功能
1. **批量操作**: 批量启动拆解、批量生成剧本
2. **导出功能**: 剧本导出为 Word/PDF
3. **实时协作**: 多用户协作编辑
4. **版本管理**: Script 版本历史、回滚
5. **质量检查可视化**: OWR 质检结果展示
6. **Pipeline 可视化**: 工作流编排界面

---

## 📌 架构洞察

### 1. 模块化设计
- 页面组件独立（Dashboard, Workspace）
- UI 组件封装（Glass UI 系列）
- 业务逻辑分离（services/）

### 2. 统一设计语言
- Glass UI 风格贯穿全局
- 一致的色彩系统（slate + cyan）
- 统一的动画效果（Framer Motion）

### 3. 渐进式增强
- Mock 数据支持开发调试
- 分阶段功能实现（CONFIG → SOURCE → PLOT → SCRIPT）
- 向后兼容（支持旧版 Ant Design 组件）

### 4. 用户体验优化
- 实时反馈（日志、进度条）
- 悬浮提示（Tooltip）
- 错误处理（Message 提示）
- Loading 状态（Skeleton）

### 5. 性能优化
- 懒加载（React.lazy）
- 分页查询
- 虚拟滚动（长列表）
- 图片懒加载

---

## 🎯 核心发现

1. **双模式交互**: Dashboard 卡片模式 + Workspace Tab 模式
2. **三层弹窗架构**: 页面级 → 全局级 → 嵌套级
3. **四阶段工作流**: 配置 → 上传 → 拆解 → 生成
4. **六大功能模块**: CONFIG, SOURCE, AGENTS, SKILLS, PLOT, SCRIPT
5. **统一 UI 系统**: Glass UI 组件库保证视觉一致性

前端架构清晰，功能完整，UI 体系成熟，支持完整的网文改编工作流。

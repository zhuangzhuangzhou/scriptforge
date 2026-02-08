# Workspace 组件文档

## 概述

Workspace 是项目工作区的主容器组件，已从原始的 2,506 行单文件重构为模块化的多组件架构。

### 重构成果

- **代码减少**：从 2,506 行减少到 1,607 行（主容器）
- **组件拆分**：6 个标签页独立为单独的组件
- **Hooks 提取**：3 个核心 Custom Hooks
- **可维护性**：每个标签页独立管理，易于维护和测试

## 目录结构

```
Workspace/
├── index.tsx                    # 主容器（1607 行）
├── PlotTab/                     # 剧情拆解标签页
│   ├── index.tsx               # PlotTab 主容器
│   ├── BatchList.tsx           # 批次列表组件
│   ├── BatchCard.tsx           # 批次卡片组件
│   ├── BreakdownDetail.tsx     # 拆解详情组件
│   └── hooks/                  # 自定义 Hooks
│       ├── index.ts
│       ├── useBreakdownPolling.ts
│       ├── useBatchProgress.ts
│       └── useBreakdownQueue.ts
├── ConfigTab/                   # 项目配置标签页
│   └── index.tsx
├── SourceTab/                   # 小说原文标签页
│   └── index.tsx
├── ScriptTab/                   # 剧本生成标签页
│   └── index.tsx
├── AgentsTab/                   # 智能体标签页
│   └── index.tsx
└── SkillsTab/                   # 技能库标签页
    └── index.tsx
```

## 主要组件

### 1. Workspace/index.tsx（主容器）

**职责**：
- 管理全局状态（项目信息、标签页切换、模态框等）
- 协调各标签页组件
- 处理全局操作（文件上传、项目启动等）
- 管理 Console Logger 和 AI Copilot

**核心状态**：
- `activeTab`: 当前激活的标签页
- `project`: 项目信息
- `formData`: 表单数据
- `showConsole`: Console 显示状态
- `showCopilot`: Copilot 显示状态

### 2. PlotTab（剧情拆解）

**职责**：
- 管理批次列表和拆解任务
- 处理单个/循环/批量拆解
- 显示拆解进度和结果

**子组件**：
- `BatchList`: 批次列表
- `BatchCard`: 批次卡片
- `BreakdownDetail`: 拆解详情展示

**Hooks**：
- `useBreakdownPolling`: 拆解任务轮询
- `useBatchProgress`: 批量进度管理
- `useBreakdownQueue`: 队列管理


### 3. ConfigTab（项目配置）

**职责**：
- 项目基础信息编辑
- 小说源文件管理
- 批次配置和模型选择

### 4. SourceTab（小说原文）

**职责**：
- 章节列表展示（支持无限滚动）
- 章节内容查看
- 章节搜索和管理

### 5. ScriptTab（剧本生成）

**职责**：
- 剧集列表展示
- 剧本内容编辑
- 质检报告查看

### 6. AgentsTab（智能体）

**职责**：
- 智能体列表展示
- 智能体配置管理

### 7. SkillsTab（技能库）

**职责**：
- 技能列表展示
- 技能启用/禁用管理


## 使用指南

### 如何添加新的标签页

1. 在 `Workspace/` 目录下创建新的标签页目录
2. 创建 `index.tsx` 作为标签页主组件
3. 在 `Workspace/index.tsx` 中导入新组件
4. 在 `renderContent()` 函数中添加新的 case

示例：
```typescript
// 1. 导入组件
import NewTab from './NewTab';

// 2. 在 renderContent() 中添加
case 'NEW':
    return <NewTab {...props} />;
```

### 如何创建 Custom Hook

1. 在对应标签页的 `hooks/` 目录下创建新文件
2. 导出 Hook 函数
3. 在 `hooks/index.ts` 中导出

示例：
```typescript
// useMyHook.ts
export const useMyHook = () => {
  // Hook 逻辑
  return { /* ... */ };
};

// hooks/index.ts
export { useMyHook } from './useMyHook';
```


## 开发指南

### 组件拆分原则

1. **单一职责**：每个组件只负责一个功能
2. **Props 传递**：通过 Props 传递数据和回调函数
3. **状态提升**：共享状态放在父组件中
4. **Hooks 封装**：复杂逻辑封装为 Custom Hooks

### 代码规范

1. **命名规范**：
   - 组件：PascalCase（如 `BatchList`）
   - Hooks：camelCase，以 `use` 开头（如 `useBreakdownPolling`）
   - 文件：与组件/Hook 名称一致

2. **类型定义**：
   - 所有 Props 必须定义 TypeScript 接口
   - 避免使用 `any` 类型

3. **注释规范**：
   - 复杂逻辑添加注释说明
   - 组件顶部添加职责说明

## 注意事项

⚠️ **重要提醒**：

1. **UI 样式不变**：重构过程中不得修改任何 UI 样式
2. **功能保持一致**：所有功能必须与原版本完全一致
3. **向后兼容**：确保不影响现有功能


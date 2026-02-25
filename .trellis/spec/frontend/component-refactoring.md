# 前端组件重构规范

## 概述

本文档记录大型组件重构的最佳实践，基于 Workspace.tsx 重构经验总结。

## 何时需要重构

### 重构信号

| 指标 | 阈值 | 说明 |
|------|------|------|
| 文件行数 | > 500 行 | 单文件过大，难以维护 |
| 状态变量 | > 15 个 | 状态管理混乱 |
| useEffect | > 5 个 | 副作用过多 |
| 处理函数 | > 10 个 | 逻辑过于复杂 |

### 典型场景

1. **多标签页组件**：包含多个独立功能模块
2. **复杂表单**：多步骤、多字段的表单
3. **数据密集型页面**：大量数据展示和交互
4. **日志/控制台组件**：包含多种渲染逻辑和格式化处理

---

## 重构步骤

### 步骤 1: 提取常量配置

```typescript
// ❌ 重构前: 配置散落在代码各处
const LogItem = ({ log }) => {
  const getColor = () => {
    if (log.type === 'error') return 'text-red-500';
    if (log.type === 'success') return 'text-green-500';
    // ...
  };
};

// ✅ 重构后: 集中配置
const LOG_TYPE_CONFIG: Record<string, { color: string; icon: ReactNode }> = {
  error: { color: 'text-red-500', icon: <CloseCircleOutlined /> },
  success: { color: 'text-green-500', icon: <CheckCircleOutlined /> },
  // ...
};

const LogItem = ({ log }) => {
  const config = LOG_TYPE_CONFIG[log.type] || LOG_TYPE_CONFIG.info;
  return <span className={config.color}>{config.icon}</span>;
};
```

### 步骤 2: 提取子组件

```typescript
// ❌ 重构前: 所有渲染逻辑在一个组件中
const ConsoleLogger = () => {
  // 600+ 行代码
  return (
    <div>
      {/* 状态信息渲染 */}
      {/* 日志列表渲染 */}
      {/* 格式化内容渲染 */}
      {/* 统计面板渲染 */}
    </div>
  );
};

// ✅ 重构后: 拆分为独立子组件
const StatusInfo = ({ progress, currentStep }) => { /* ... */ };
const LogItem = ({ log, isFormatMode }) => { /* ... */ };
const FormattedContent = ({ content }) => { /* ... */ };
const LLMStatsPanel = ({ stats }) => { /* ... */ };

const ConsoleLogger = () => {
  return (
    <div>
      <StatusInfo progress={progress} currentStep={currentStep} />
      {logs.map(log => <LogItem key={log.id} log={log} />)}
      <LLMStatsPanel stats={llmStats} />
    </div>
  );
};
```

### 步骤 3: 统一类型定义

```typescript
// ❌ 错误: 重复定义类型
// ConsoleLogger.tsx
interface LogEntry {
  id: string;
  type: string;
  message: string;
}

// useConsoleLogger.ts
export interface LogEntry {
  id: string;
  type: string;
  message: string;
}

// ✅ 正确: 从单一来源导入
// ConsoleLogger.tsx
import type { LogEntry, LLMCallStats } from '../hooks/useConsoleLogger';
```

### 步骤 4: 使用 useMemo 优化

```typescript
// ❌ 重构前: 每次渲染都重新计算
const filteredLogs = logs.filter(log => isKeyContent(log));

// ✅ 重构后: 缓存计算结果
const filteredLogs = useMemo(
  () => logs.filter(log => isKeyContent(log)),
  [logs]
);
```

---

## 常见重构错误

### 错误 1: 变量名拼写错误

```typescript
// ❌ 错误: 变量名拼写错误
for (let i = 0; i < text.length; i++) {
  if (text[i] === '[') {
    last.index = i;  // 应该是 lastIndex
  }
}

// ✅ 正确
let lastIndex = -1;
for (let i = 0; i < text.length; i++) {
  if (text[i] === '[') {
    lastIndex = i;
  }
}
```

### 错误 2: 遗漏变量声明

```typescript
// ❌ 错误: 遗漏 let 声明
const formatText = (text: string) => {
   = text;  // 语法错误
  // ...
};

// ✅ 正确
const formatText = (text: string) => {
  let result = text;
  // ...
};
```

---

## 重构检查清单

- [ ] 常量配置是否提取到文件顶部？
- [ ] 子组件是否独立且职责单一？
- [ ] 类型定义是否统一（无重复）？
- [ ] 是否使用 useMemo/useCallback 优化性能？
- [ ] 变量命名是否正确（无拼写错误）？
- [ ] 是否删除了未使用的代码？

---

## 更新日志

| 日期 | 更新内容 | 作者 |
|------|----------|------|
| 2026-02-25 | 补充: 重构步骤、常见错误、检查清单 (基于 ConsoleLogger 重构) | Claude Opus 4.6 |
| 2026-02-08 | 初始版本: 基于 Workspace.tsx 重构经验 | Claude Opus 4.6 |

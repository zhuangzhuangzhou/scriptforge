# Script Tab 布局重构记录

## 重构日期
2026-02-25

## 重构目标
将 Script Tab 的页面布局按照 Plot Tab 的布局结构进行重构，以保持整个 Workspace 的视觉一致性和用户体验统一性。

## 重构成果

### 1. 新增组件

| 组件 | 文件 | 说明 |
|------|------|------|
| EpisodeCard | `EpisodeCard.tsx` | 剧集卡片组件（对标 BatchCard） |
| EpisodeList | `EpisodeList.tsx` | 剧集列表组件（对标 BatchList） |
| ScriptDetail | `ScriptDetail.tsx` | 剧本详情组件（对标 BreakdownDetail） |

### 2. 布局变更

#### 整体结构
```tsx
<div className="h-full flex gap-0 overflow-hidden bg-slate-950">
  {/* 左侧栏：剧集列表 (w-80) */}
  <EpisodeList />

  {/* 右侧主内容区：flex-1 */}
  <div className="flex-1 flex flex-col bg-slate-900/50 relative overflow-hidden">
    <div className="flex-1 overflow-y-auto p-0">
      <ScriptDetail />
    </div>
  </div>
</div>
```

#### 关键变更
- **移除顶部工具栏**: 操作按钮移到内容区标题栏
- **左侧栏宽度统一**: 从 `w-72` 改为 `w-80` (320px)
- **简化左侧栏**: 只保留进度统计和剧集列表
- **扁平化内容区**: 移除多余的嵌套容器
- **移除底部状态栏**: 编辑模式的操作栏保留但样式调整

### 3. 样式对照

| 元素 | Plot Tab | Script Tab（重构后） |
|------|----------|---------------------|
| 左侧栏宽度 | `w-80` | `w-80` ✓ |
| 左侧栏背景 | `bg-slate-900` | `bg-slate-900` ✓ |
| 左侧栏边框 | `border-r border-slate-800` | `border-r border-slate-800` ✓ |
| 主容器背景 | `bg-slate-950` | `bg-slate-950` ✓ |
| 内容区背景 | `bg-slate-900/50` | `bg-slate-900/50` ✓ |
| 内容区内边距 | `p-4` | `p-4` ✓ |
| 卡片样式 | `bg-slate-800/50 border border-slate-700/50 rounded-xl p-4` | 同左 ✓ |
| 卡片间距 | `space-y-4` | `space-y-4` ✓ |

### 4. 功能保留

所有原有功能均正常工作：
- ✓ 剧集选择
- ✓ 单集生成
- ✓ 批量生成
- ✓ 编辑功能
- ✓ 导出功能
- ✓ 历史查看
- ✓ 质检报告查看
- ✓ Console Logger 集成

### 5. 类型修复

修复了以下类型错误：
- `EpisodeScript` 类型定义统一
- `ScriptQAReport` 与 `QAReport` 类型转换
- ConsoleLogger 日志类型补全
- ScriptViewModal 接口参数调整

## 备份文件

原始文件已备份为 `index_backup.tsx`

## 验证方式

1. **编译检查**: ✓ 通过 TypeScript 编译
2. **视觉一致性**: 布局结构与 Plot Tab 完全一致
3. **功能完整性**: 所有原有功能正常工作

## 技术亮点

1. **组件化拆分**: 将单文件拆分为 3 个独立组件，提升可维护性
2. **类型安全**: 修复所有 TypeScript 类型错误
3. **视觉统一**: 与 Plot Tab 保持完全一致的布局和样式
4. **代码复用**: 复用 Plot Tab 的 QAReportModal 组件

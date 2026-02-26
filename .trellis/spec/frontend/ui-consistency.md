# UI 一致性和布局规范

## 概述

本文档记录了在 Script Tab 重构过程中学到的 UI 一致性原则和布局模式。

---

## 核心原则

### 1. 跨 Tab 视觉一致性

**问题**: 不同功能模块（Plot Tab、Script Tab）使用不同的布局结构，导致用户体验不一致。

**解决方案**: 建立统一的布局模式，在所有类似功能中复用。

**示例**:
```tsx
// 统一的左右布局模式
<div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
  <div className="flex items-center justify-between gap-6">
    {/* 左侧：主要信息 */}
    <div className="flex items-center gap-6">
      {/* 信息项 */}
    </div>

    {/* 右侧：次要信息（如质检） */}
    {condition && (
      <>
        <div className="w-px h-12 bg-slate-700/50"></div>
        <div className="flex items-center gap-4">
          {/* 次要信息 */}
        </div>
      </>
    )}
  </div>
</div>
```

**为什么**:
- 降低用户学习成本
- 提升整体产品质感
- 便于维护和扩展

---

## 布局模式

### 模式 1: 信息卡片左右分栏

**适用场景**: 需要展示主要信息和次要信息，且次要信息可能不存在

**结构**:
```
┌────────────────────────────────────────────────┐
│ 主信息1 │ 主信息2 │ 主信息3 ║ 次要信息 + 操作 │
└────────────────────────────────────────────────┘
```

**实现要点**:
1. 使用 `flex items-center justify-between` 实现左右布局
2. 使用 `w-px h-12 bg-slate-700/50` 创建垂直分隔线
3. 次要信息用条件渲染包裹（`{condition && <> ... </>}`）
4. 左侧信息项之间也用分隔线分隔

**代码示例**:
```tsx
{/* 剧本信息卡片（左右结构） */}
<div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
  <div className="flex items-center justify-between gap-6">
    {/* 左侧：字数统计 */}
    <div className="flex items-center gap-6">
      <div className="text-center">
        <p className="text-xs text-slate-400 mb-1">总字数</p>
        <p className="text-2xl font-bold text-white">{wordCount}</p>
      </div>
      <div className="w-px h-10 bg-slate-700/50"></div>
      {/* 更多信息项 */}
    </div>

    {/* 右侧：质检信息 */}
    {qaStatus && (
      <>
        <div className="w-px h-12 bg-slate-700/50"></div>
        <div className="flex items-center gap-4">
          {/* 质检内容 */}
        </div>
      </>
    )}
  </div>
</div>
```

---

### 模式 2: 编辑模式操作栏位置

**问题**: 底部固定操作栏占用空间，且用户需要滚动到底部才能操作。

**解决方案**: 将编辑操作移到右上角，与标题栏对齐。

**对比**:

❌ **不推荐 - 底部固定栏**:
```tsx
<div className="flex-1 flex flex-col">
  <div className="flex-1 overflow-y-auto">
    {/* 内容 */}
  </div>
  {/* 底部固定栏 - 占用空间 */}
  <div className="sticky bottom-0 border-t p-4">
    <button>取消</button>
    <button>保存</button>
  </div>
</div>
```

✅ **推荐 - 右上角操作**:
```tsx
<div className="flex items-center justify-between">
  <h2>标题</h2>
  <div className="flex items-center gap-2">
    {editMode && (
      <>
        {/* 编辑提示 */}
        <div className="text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-1.5">
          <AlertCircle size={14} />
          <span>有未保存的更改</span>
        </div>
        {/* 操作按钮 */}
        <button>取消</button>
        <button>保存</button>
      </>
    )}
  </div>
</div>
```

**优势**:
- 释放底部空间，内容区域更大
- 操作按钮始终可见，无需滚动
- 视觉焦点集中在顶部

---

## 按钮配色策略

### 原则: 功能区分用色彩

**问题**: 不同 Tab 的相似功能使用相同配色，用户难以区分当前位置。

**解决方案**: 为不同功能模块设计独特的配色方案。

**示例**:

| Tab | 全部操作 | 继续操作 | 重新操作-|---------|---------|---------|
| **Plot Tab** | 紫色→靛蓝 | 青绿→青色 | 蓝色→青色 |
| **Script Tab** | 靛蓝→紫色 | 翡翠绿→绿色 | 天空蓝→蓝色 |

**配色选择原则**:
1. **色系区分**: Plot Tab 用冷色调，Script Tab 用不同的冷色调组合
2. **渐变方向**: 可以使用镜像渐变（如 Plot 是紫→靛蓝，Script 是靛蓝→紫）
3. **避免过于鲜艳**: 使用 `-600` 级别的颜色，避免 `-500` 或更亮的颜色
4. **保持一致性**: 同一 Tab 内的按钮配色要形成统一的色彩体系

**代码示例**:
```tsx
// Script Tab 按钮配色
<button className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500">
  全部生成
</button>
<button className="bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500">
  继续生成
</button>
<button className="bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500">
  重新生成
</button>
```

---

## 编辑功能实现

### 双向数据同步

**场景**: 编辑四段式结构时，需要同步更新完整剧本。

**问题**: 用户编辑四段式结构后，切换到完整剧本视图发现内容没有更新。

**解决方案**: 在编辑四段式时，自动拼接生成完整剧本。

**实现**:
```tsx
const handleStructureChange = (key: keyof ScriptStructure, content: string) => {
  if (!editedStructure) return;

  const wordCount = content.length;
  const updatedStructure = {
    ...editedStructure,
    [key]: { content, word_count: wordCount }
  };

  setEditedStructure(updatedStructure);

  // 同步更新完整剧本：将四段式内容拼接
  const fullScript = [
    `【起】开场冲突\n${updatedStructure.opening.content}\n`,
    `【承】推进发展\n${updatedStructure.development.content}\n`,
    `【转】反转高潮\n${updatedStructure.climax.content}\n`,
    `【钩】悬念结尾\n${updatedStructure.hook.content}`
  ].join('\n');

  setEditedFullScript(fullScript);
  setHasUnsavedChanges(true);
};
```

**关键点**:
1. 每次编辑四段式时立即更新完整剧本
2. 使用标记（【起】【承】【转】【钩】）分隔段落
3. 保持数据一致性，避免两个视图显示不同内容

---

## 历史版本管理

### 按钮横排显示

**问题**: 竖排的图标+文字按钮占用空间大，且不易识别。

**解决方案**: 改为横排显示，图标和文字在同一行。

**对比**:

❌ **竖排**:
```tsx
<button className="flex flex-col items-center">
  <Eye className="w-3 h-3" />
  <span>查看</span>
</button>
```

✅ **横排**:
```tsx
<button className="flex items-center gap-1">
  <Eye className="w-3 h-3" />
  查看
</button>
```

### 版本回滚功能

**需求**: 允许用户将历史版本设置为当前版本。

**实现要点**:
1. 只在非当前版本显示"设为当前"按钮
2. 操作时显示加载状态
3. 成功后刷新数据并更新 UI

**代码示例**:
```tsx
{!item.is_current && (
  <button
    onClick={() => handleSetCurrent(item.script_id)}
    disabled={settingCurre== item.script_id}
    className="flex items-center gap-1 px-2 py-1 text-[10px] text-green-400 hover:bg-green-500/10 rounded"
  >
    {settingCurrent === item.script_id ? (
      <Loader2 className="w-3 h-3 animate-spin" />
    ) : (
      <CheckCircle className="w-3 h-3" />
    )}
    设为当前
  </button>
)}
```

---

## 常见错误

### 错误 1: 修改布局时破坏原有功能

**症状**: 重构布局后，用户反馈"页面都弄换了"。

**原因**: 在修改布局时，不小心改变了原有的信息展示方式（如从 4 列网格改为左右布局）。

**预防**:
1. 修改前先询问用户具体需求
2. 逐步修改，每次只改一个部分
3. 修改后及时确认是否符合预期

### 错误 2: 编辑功能缺少输入框

**症状**: 进入编辑模式后，内容无法编辑。

**原因**: 只添加了编辑模式的状态管理，但忘记在 UI 中添加 `<textarea>` 输入框。

**修复x
{editMode ? (
  <textarea
    value={content}
    onChange={(e) => handleChange(e.target.value)}
    className="w-full min-h-[120px] bg-slate-900/50 text-slate-300 p-3 rounded-lg border border-slate-700"
  />
) : (
  <p className="text-slate-300">{content}</p>
)}
```

### 错误 3: 数据同步不及时

**症状**: 编辑四段式结构后，完整剧本视图没有更新。

**原因**: 只更新了四段式的状态，忘记同步更新完整剧本的状态。

**修复**: 在 `handleStructureChange` 中同时更新 `editedFullScript`。

---

## Pattern: 使用项目定义的 UI 组件

### 问题
直接使用 Ant Design 原生组件，导致样式不统一，需要每次手动配置深色主题。

### 场景
```typescript
// ❌ 错误：直接使用 Ant Design Table
import { Table } from 'antd';

<Table
  dataSource={data}
  columns={columns}
  className="custom-dark-table"  // 需要手动添加样式
/>
```

### 解决方案：使用 GlassTable

```typescript
// ✅ 正确：使用项目定义的 GlassTable
import { GlassTable } from '../../../components/ui/GlassTable';

<GlassTable
  dataSource={data}
  columns={columns}
  // 自动应用磨砂玻璃质感和深色主题
/>
```

### 为什么这样做？

1. **统一视觉风格** - GlassTable 提供了磨砂玻璃质感，符合项目设计规范
2. **避免重复配置** - 不需要每次都写 `className="custom-dark-table"`
3. **易于维护** - 样式集中管理，修改一处即可全局生效
4. **深色主题自动配置** - 使用 ConfigProvider 自动应用深色算法

### GlassTable 特性

- 透明背景（`colorBgContainer: 'transparent'`）
- 深色表头（`headerBg: '#0f172a'`）
- 统一边框色（`borderColor: '#1e293b'`）
- 悬停效果（`rowHoverBg: 'rgba(30, 41, 59, 0.5)'`）

### 适用场景

| 组件 | 使用场景 | 导入路径 |
|------|----------|----------|
| **GlassTable** | 所有表格展示 | `components/ui/GlassTable` |
| **GlassInput** | 所有输入框 | `components/ui/GlassInput` |
| **GlassSelect** | 所有下拉选择 | `components/ui/GlassSelect` |
| **GlassModal** | 所有模态框 | `components/ui/GlassModal` |
| **GlassDatePicker** | 所有日期选择 | `components/ui/GlassDatePicker` |
| **其他 UI 组件** | 检查 `components/ui/` 目录 | 优先使用项目组件 |

### GlassSelect 使用方法

**错误写法** (使用 Option 子组件):
```typescript
import { Select } from 'antd';
const { Option } = Select;

<Select placeholder="类型" onChange={handleChange}>
  <Option value="system">系统通知</Option>
  <Option value="maintenance">维护公告</Option>
</Select>
```

**正确写法** (使用 options 属性):
```typescript
import { GlassSelect } from '../../../components/ui/GlassSelect';

<GlassSelect
  placeholder="类型"
  allowClear
  onChange={handleChange}
  options={[
    { value: 'system', label: '系统通知' },
    { value: 'maintenance', label: '维护公告' },
  ]}
/>
```

### GlassInput 子组件支持

**问题**: 直接使用 `const { Search } = GlassInput;` 会导致页面空白

**原因**: GlassInput 组件没有导出 Search 和 TextArea 子组件

**解决方案**: 使用 `Object.assign` 为 GlassInput 添加子组件

```typescript
// ✅ 正确：GlassInput 组件实现
export const GlassInput: React.FC<InputProps> & {
  Search: typeof Input.Search;
  TextArea: typeof Input.TextArea;
} = Object.assign(
  (props: InputProps) => {
    return (
      <div className="glass-input-wrapper">
        <style>{GLASS_INPUT_STYLES}</style>
        <Input {...props} />
      </div>
    );
  },
  {
    Search: (props: any) => {
      return (
        <div className="glass-input-wrapper">
          <style>{GLASS_INPUT_STYLES}</style>
          <Input.Search {...props} />
        </div>
      );
    },
    TextArea: (props: TextAreaProps) => {
      return (
        <div className="glass-input-wrapper">
          <style>{GLASS_INPUT_STYLES}</style>
          <Input.TextArea {...props} />
        </div>
      );
    },
  }
);
```

**使用方式**:
```typescript
import { GlassInput } from '../../../components/ui/GlassInput';

const { Search } = GlassInput;  // ✅ 现在可以正常使用

<Search placeholder="搜索" onSearch={handleSearch} />
<GlassInput.TextArea rows={4} placeholder="输入内容" />
```

---

## Pattern: 表格序号列标准实现（可选）

### 适用场景

序号列**不是必须的**，但在以下场景中推荐使用：
- 需要用户快速定位特定行（如"第 5 行有问题"）
- 数据量较大（> 20 行），需要视觉锚点
- 需要在讨论中引用特定行
- 表格宽度充足，不影响其他重要列的显示

### 不推荐使用序号列的场景

- 表格只有少量数据（< 10 行）
- 已有其他明确的标识列（如任务 ID、编号等）
- 表格宽度受限，需要节省空间
- 移动端或小屏幕设备

### 问题
表格缺少序号列，用户难以快速定位和引用特定行。

### 解决方案

```typescript
const columns = [
  {
    title: '序号',
    key: 'index',
    width: 70,
    fixed: 'left' as const,  // 固定在左侧
    render: (_: any, __: any, index: number) => (
      <span className="font-mono text-slate-400">{index + 1}</span>
    ),
  },
  // ... 其他列
];
```

### 实现要点

1. **固定位置** - 使用 `fixed: 'left'` 固定在左侧，滚动时始终可见
2. **宽度适中** - 70px 足够显示 2-3 位数字
3. **等宽字体** - 使用 `font-mono` 确保数字对齐
4. **颜色区分** - 使用 `text-slate-400` 与数据列区分
5. **从 1 开始** - `index + 1` 符合用户习惯

### 完整示例

```typescript
import { GlassTable } from '../../../components/ui/GlassTable';

const TaskManagement = () => {
  const columns = [
    {
      title: '序号',
      key: 'index',
      width: 70,
      fixed: 'left' as const,
      render: (_: any, __: any, index: number) => (
        <span className="font-mono text-slate-400">{index + 1}</span>
      ),
    },
    {
      title: '任务ID',
      dataIndex: 'id',
      key: 'id',
      width: 120,
      render: (id: string) => (
        <Tooltip title={id}>
          <span className="font-mono text-xs text-slate-300">{id.slice(0, 8)}...</span>
        </Tooltip>
      ),
    },
    // ... 其他列
    {
      title: '操作',
      key: 'actions',
      width: 100,
      fixed: 'right' as const,  // 操作列固定在右侧
      render: (_: any, record: Task) => (
        <Button onClick={() => handleAction(record)}>操作</Button>
      ),
    },
  ];

  return (
    <GlassTable
      dataSource={tasks}
      columns={columns}
      rowKey="id"
      scroll={{ x: 1400 }}  // 启用横向滚动
    />
  );
};
```

### 为什么这样做？

- **快速定位** - 用户可以说"第 5 行有问题"
- **视觉锚点** - 序号提供视觉参考，便于浏览
- **固定显示** - 滚动时序号始终可见
- **专业感** - 符合数据表格的标准实践

**注意**: 序号列是可选的，根据实际需求决定是否添加。

---

## Pattern: 共享常量提取

### 问题

同一个常量（如 `tierNames`）在多个文件中重复定义，导致：
- 修改时需要同步多处
- 容易遗漏，造成不一致
- 代码冗余

### 场景

```typescript
// ❌ 错误：在多个文件中重复定义
// MainLayout.tsx
const tierNames = { FREE: '免费版', CREATOR: '创作者版', ... };

// RedeemCodes/index.tsx
const tierNames = { FREE: '免费版', CREATOR: '创作者版', ... };

// TierComparisonModal.tsx
const tierNames = { FREE: '免费版', CREATOR: '创作者版', ... };
```

### 解决方案

提取到 `constants/` 目录：

```typescript
// ✅ 正确：frontend/src/constants/tier.ts
import { UserTier } from '../types';

export const TIER_NAMES: Record<UserTier | string, string> = {
  FREE: '免费版',
  CREATOR: '创作者版',
  STUDIO: '工作室版',
  ENTERPRISE: '企业版',
};

export const TIER_COLORS: Record<UserTier, string> = {
  FREE: 'from-slate-500 to-slate-700',
  CREATOR: 'from-blue-500 to-cyan-500',
  STUDIO: 'from-purple-500 to-pink-500',
  ENTERPRISE: 'from-amber-500 to-orange-500',
};
```

### 使用方式

```typescript
import { TIER_NAMES, TIER_COLORS } from '../constants/tier';

// 在组件中使用
<span>{TIER_NAMES[userTier]}</span>
```

### 常见需要提取的常量

| 常量类型 | 建议文件 |
|---------|---------|
| 用户等级相关 | `constants/tier.ts` |
| 任务状态相关 | `constants/status.ts` |
| 颜色主题相关 | `constants/colors.ts` |
| API 端点相关 | `constants/api.ts` |

---

## Pattern: 管理员 Dashboard 菜单入口

### 问题

新增管理功能后，用户在管理后台找不到入口。

### 原因

管理员 Dashboard (`/admin/dashboard`) 使用卡片式导航，不是侧边栏菜单。新功能需要手动添加卡片。

### 解决方案

在 `pages/admin/Dashboard.tsx` 中添加卡片：

```tsx
// 1. 导入图标
import { GiftOutlined } from '@ant-design/icons';

// 2. 在 <Row> 中添加卡片
<Col xs={24} sm={12} md={8} lg={6}>
  <Card
    hoverable
    className="bg-slate-800 border-slate-700 cursor-pointer group"
    onClick={() => navigate('/admin/redeem-codes')}
  >
    <div className="flex flex-col items-center justify-center py-4">
      <div className="p-3 rounded-full bg-emerald-500/10 mb-3 group-hover:bg-emerald-500/20 transition-colors">
        <GiftOutlined className="text-2xl text-emerald-500" />
      </div>
      <span className="text-slate-200 font-medium">兑换码管理</span>
      <span className="text-slate-500 text-xs mt-1">创建和管理兑换码</span>
    </div>
  </Card>
</Col>
```

### 检查清单

新增管理功能时：
- [ ] 在 `App.tsx` 添加路由
- [ ] 在 `Dashboard.tsx` 添加卡片入口
- [ ] 使用合适的图标和配色

---

## Pattern: Tailwind 动态类名处理

### 问题

Tailwind JIT 编译器在构建时扫描静态类名，模板字符串中的动态类名不会被识别：

```typescript
// ❌ 错误：动态类名不会被编译
const color = 'blue';
<div className={`bg-${color}-500/10 text-${color}-500`}>

// 构建后这些类不存在，样式不生效
```

### 解决方案：颜色映射表

预定义完整的类名字符串：

```typescript
// ✅ 正确：使用映射表
const colorClasses: Record<string, { bg: string; text: string }> = {
  blue: { bg: 'bg-blue-500/10', text: 'text-blue-500' },
  cyan: { bg: 'bg-cyan-500/10', text: 'text-cyan-500' },
  purple: { bg: 'bg-purple-500/10', text: 'text-purple-500' },
  // ... 其他颜色
};

// 使用
const colors = colorClasses[color] || colorClasses.blue;
<div className={`${colors.bg} ${colors.text}`}>
```

### 适用场景

- 数据驱动的卡片/按钮渲染（如 Dashboard 快速操作）
- 状态指示器（不同状态不同颜色）
- 标签/徽章组件

### 为什么这样做？

1. **构建时可见** - 所有类名都是完整字符串，Tailwind 能正确扫描
2. **类型安全** - TypeScript 可以检查颜色键是否存在
3. **易于维护** - 新增颜色只需在映射表中添加一行

---

## 检查清单

在实现 UI 功能时，使用此清单确保质量：

- [ ] 是否与其他类似功能保持视觉一致性？
- [ ] 按钮配色是否与其他模块有区分度？
- [ ] 编辑模式是否提供了实际的输入框？
- [ ] 编辑不同视图时，数据是否保持同步？
- [ ] 操作按钮位置是否合理（避免底部固定栏）？
- [ ] 历史版本管理是否支持回滚？
- [ ] 按钮文字是否横排显示（易读性）？
- [ ] 是否使用了项目定义的 UI 组件（GlassTable、GlassModal 等）？
- [ ] 表格是否需要序号列？（可选，根据实际需求决定）
- [ ] 重复使用的常量是否提取到 `constants/` 目录？
- [ ] 管理功能是否在 Dashboard 添加了卡片入口？
- [ ] 动态颜色是否使用映射表而非模板字符串？

---

## 更新日志

- 2026-02-26: 新增：Tailwind 动态类名处理模式（基于 Dashboard 重构经验）
- 2026-02-26: 新增：共享常量提取规范、管理员 Dashboard 菜单入口规范
- 2026-02-25: 新增：GlassTable 使用规范、表格序号列标准实现
- 2026-02-25: 创建文档，记录 Script Tab 重构中的 UI 一致性经验

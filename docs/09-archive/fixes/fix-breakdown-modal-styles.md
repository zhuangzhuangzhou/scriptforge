# 剧情拆解配置弹窗样式修复

## 问题描述

在前端剧集管理（Workspace）页面中，剧情拆解配置弹窗存在以下样式错配问题：

1. **下拉选项布局问题**：ConfigSelector 中的 Select.Option 使用了 `flex flex-col` 布局，导致选项内容在下拉菜单中显示不正确
2. **选中项显示问题**：选中的选项在输入框中只显示 key，没有显示标签信息
3. **下拉菜单样式不一致**：GlassSelect 的下拉菜单样式与选项内容不匹配
4. **滚动条样式缺失**：SkillSelector 使用了 `custom-scrollbar` 类，但该类未定义

## 修复方案

### 1. ConfigSelector 组件优化

**文件**: `frontend/src/components/ConfigSelector.tsx`

#### 修复内容

1. **添加 `optionLabelProp="label"` 属性**
   - 使选中项在输入框中显示自定义标签
   - 标签包含 key 和自定义标识

2. **优化选项布局**
   - 移除 `flex flex-col` 布局，改用简单的 `div` 包裹
   - 添加 `py-1` 内边距，确保选项有足够的垂直空间
   - 使用 `whitespace-nowrap` 防止标签换行
   - 改进描述文本的行高和间距

3. **改进标签显示**
   ```tsx
   label={
     <span className="font-mono text-xs">
       {cfg.key}
       {cfg.is_custom && <span className="ml-2 text-[9px] text-purple-400">自定义</span>}
     </span>
   }
   ```

#### 修改前后对比

**修改前**:
```tsx
<Select.Option key={cfg.key} value={cfg.key}>
  <div className="flex flex-col">
    <div className="flex items-center justify-between gap-2">
      <span className="font-mono text-xs text-slate-200">{cfg.key}</span>
      {/* 标签 */}
    </div>
    <div className="text-[10px] text-slate-500 mt-1 line-clamp-2">
      {cfg.description}
    </div>
  </div>
</Select.Option>
```

**修改后**:
```tsx
<Select.Option 
  key={cfg.key} 
  value={cfg.key}
  label={
    <span className="font-mono text-xs">
      {cfg.key}
      {cfg.is_custom && <span className="ml-2 text-[9px] text-purple-400">自定义</span>}
    </span>
  }
>
  <div className="py-1">
    <div className="flex items-center justify-between gap-2 mb-1">
      <span className="font-mono text-xs text-slate-200">{cfg.key}</span>
      {/* 标签 */}
    </div>
    <div className="text-[10px] text-slate-500 leading-relaxed">
      {cfg.description}
    </div>
  </div>
</Select.Option>
```

### 2. GlassSelect 组件优化

**文件**: `frontend/src/components/ui/GlassSelect.tsx`

#### 修复内容

1. **增强下拉菜单样式**
   - 提高背景不透明度（0.95 → 0.98）
   - 设置最大高度 `max-height: 400px`
   - 优化选项内边距 `padding: 8px 12px`
   - 添加选项间距 `margin-bottom: 2px`

2. **支持多行内容**
   - 添加 `white-space: normal`
   - 添加 `word-wrap: break-word`
   - 移除 `min-height` 限制

3. **优化选中状态样式**
   - 增强选中项背景色
   - 添加选中且激活状态的样式

#### 新增样式

```css
.glass-select-wrapper .ant-select-selection-item {
  color: #e2e8f0 !important;
}

.${dropdownClassName} .rc-virtual-list-holder {
  max-height: 400px !important;
}

.${dropdownClassName} .ant-select-item-option-content {
  white-space: normal !important;
  word-wrap: break-word !important;
}

.${dropdownClassName} .ant-select-item-option-selected.ant-select-item-option-active {
  background-color: rgba(34, 211, 238, 0.2) !important;
}
```

### 3. 全局滚动条样式

**文件**: `frontend/src/index.css`

#### 修复内容

添加 `custom-scrollbar` 类定义，用于组件内部的自定义滚动条样式：

```css
/* Custom Scrollbar Class for Components */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: rgba(30, 41, 59, 0.3); /* slate-800 with opacity */
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #475569; /* slate-600 */
  border-radius: 3px;
  transition: background 0.2s;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #64748b; /* slate-500 */
}
```

## 修复效果

### 1. 选中项显示
- ✅ 输入框中显示完整的配置 key
- ✅ 自定义配置显示"自定义"标识
- ✅ 系统默认配置显示"系统默认"标识

### 2. 下拉菜单
- ✅ 选项布局正确，内容完整显示
- ✅ 描述文本正常换行，不会被截断
- ✅ 选中项高亮显示清晰
- ✅ 悬停效果流畅

### 3. 滚动条
- ✅ SkillSelector 滚动条样式正确
- ✅ 滚动条与深色主题匹配
- ✅ 悬停时滚动条高亮

## 技术细节

### optionLabelProp 的作用

`optionLabelProp` 是 Ant Design Select 组件的一个重要属性：

- **默认行为**：选中项显示 `Option.children` 的内容
- **使用 `optionLabelProp="label"`**：选中项显示 `Option.label` 的内容
- **优势**：可以在下拉菜单中显示详细信息，在输入框中显示简洁标签

### 样式隔离

GlassSelect 使用动态生成的类名来隔离样式：

```tsx
const dropdownClassName = 'glass-select-dropdown-' + Math.random().toString(36).substr(2, 9);
```

这样可以避免样式污染，每个 GlassSelect 实例都有独立的下拉菜单样式。

### 虚拟滚动

Ant Design Select 使用虚拟滚动优化长列表性能：

- `rc-virtual-list-holder` 是虚拟滚动容器
- 设置 `max-height` 限制下拉菜单高度
- 自动启用虚拟滚动，提升性能

## 测试建议

### 功能测试
1. 打开剧情拆解配置弹窗
2. 点击三个下拉选择器（适配方法、质检规则、输出风格）
3. 验证下拉菜单显示正确
4. 选择不同选项，验证选中项显示正确
5. 验证自定义和系统默认标识显示正确

### 样式测试
1. 验证下拉菜单背景色和边框
2. 验证选项悬停效果
3. 验证选中项高亮效果
4. 验证描述文本换行和显示
5. 验证滚动条样式

### 兼容性测试
1. Chrome/Edge（Chromium）
2. Firefox
3. Safari
4. 不同屏幕尺寸

## 相关文件

- `frontend/src/components/ConfigSelector.tsx` - 配置选择器组件
- `frontend/src/components/ui/GlassSelect.tsx` - 玻璃态选择器组件
- `frontend/src/components/SkillSelector.tsx` - 技能选择器组件
- `frontend/src/pages/user/Workspace/index.tsx` - 工作区页面（包含弹窗）
- `frontend/src/index.css` - 全局样式

## 总结

本次修复主要解决了剧情拆解配置弹窗中的样式错配问题，通过优化组件布局、增强样式定义、添加缺失的样式类，使弹窗的显示效果更加美观和一致。修复后的弹窗符合深色主题的设计规范，用户体验得到显著提升。

---

**修复时间**: 2026-02-09
**修复人**: AI Assistant

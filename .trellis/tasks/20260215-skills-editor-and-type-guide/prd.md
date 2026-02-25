# Skills编辑样式改造与类型指南分类

## Goal

1. 将 /admin/skills 页面的编辑器改为与 /admin/resources 编辑页面相同的双栏布局样式
2. 将 /admin/resources 中 adapt_method_type_xxx 的数据单独拉出来成为新分类「类型指南」

## Requirements

### 任务1：Skills 编辑器样式改造

**当前状态**：
- SkillEditor 使用传统垂直 Form 布局
- MonacoEditor 编辑 prompt_template
- 多个 JSON 编辑器垂直排列

**目标状态**（参考 ResourceEditorModal）：
- 双栏布局：左侧 MarkdownEditor（flex-1），右侧配置面板（w-80）
- 右上角保存按钮
- 右侧面板使用 `bg-slate-900/50 rounded-xl border border-slate-800/50` 样式
- Modal 宽度 90vw，内容高度 `calc(85vh - 120px)`

**需要修改的文件**：
- `frontend/src/pages/admin/Skills/SkillEditor.tsx` - 重构为双栏布局
- `frontend/src/pages/admin/Skills/index.tsx` - 调整 GlassModal 宽度

### 任务2：新增「类型指南」分类

**当前状态**：
- adapt_method_type_xxx 资源的 category 为 "methodology"
- 共 6 个资源：xuanhuan, dushi, yanqing, xuanyi, kehuan, chongsheng

**目标状态**：
- 新增分类 `type_guide`（类型指南）
- 将 6 个 adapt_method_type_xxx 资源移动到新分类

**需要修改的文件**：

后端：
- `backend/app/core/init_ai_resources.py` - 修改 category 为 "type_guide"
- `backend/app/api/v1/ai_resources.py` - RESOURCE_CATEGORIES 添加 type_guide

前端：
- `frontend/src/pages/admin/Resources/index.tsx` - categoryMap、categoryColorMap、tabItems 添加 type_guide
- `frontend/src/pages/admin/Resources/ResourceEditorModal.tsx` - 分类下拉选项添加 type_guide

## Acceptance Criteria

- [ ] Skills 编辑器使用双栏布局（左侧 MarkdownEditor，右侧配置面板）
- [ ] Skills 编辑器 Modal 宽度为 90vw
- [ ] Resources 页面新增「类型指南」Tab
- [ ] 6 个 adapt_method_type_xxx 资源显示在「类型指南」分类下
- [ ] 所有页面正常加载，无控制台错误
- [ ] lint 和 typecheck 通过

## Technical Notes

- 不需要数据库迁移：category 字段为 String(50)，新增分类值不需要修改表结构
- SkillEditor 的 JSON Schema 编辑器（input_schema, output_schema, model_config）放在右侧配置面板
- 参考 ResourceEditorModal 的样式和布局结构

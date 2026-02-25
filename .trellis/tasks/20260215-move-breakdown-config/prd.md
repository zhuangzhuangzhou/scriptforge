# 将拆解配置移动到技能库 Tab

## 目标
优化用户体验，将拆解任务启动前的配置操作从独立的弹窗移动到技能库(Skills) Tab 中，使配置与技能管理在同一界面完成。

## 需求
1. **移除独立配置弹窗**：点击"开始拆解/重新拆解"按钮时，不再弹出配置窗口
2. **配置迁移到 SkillsTab**：将原弹窗中的配置项（AI技能选择、改编方法、质检规则）移动到 SkillsTab 中
3. **保存功能**：SkillsTab 右上角添加"保存"按钮，用于保存拆解相关配置
4. **保持功能完整性**：配置保存后，点击"开始拆解"按钮应直接使用已保存的配置启动任务

## 验收标准
- [x] 点击"开始拆解"按钮不再弹出配置弹窗，直接使用已保存配置
- [x] SkillsTab 中显示 AI 技能选择器（SkillSelector）
- [x] SkillsTab 中显示改编方法与质检规则配置（ConfigSelector）
- [x] SkillsTab 右上角有"保存"按钮
- [x] 保存后配置持久化到 localStorage
- [x] 重新拆解时也能使用保存的配置
- [x] 前端代码符合项目规范（无 lint 错误）

## 技术说明
### 原配置弹窗包含的配置项
1. **积分说明提示**
2. **AI 技能选择器** (`SkillSelector` 组件)
3. **改编方法与质检规则** (`ConfigSelector` 组件)

### 存储方案
配置可以存储在：
- `localStorage`（简单快速，前端独享）
- 后端 API（多设备同步，需要后端支持）

**建议**：先使用 localStorage 实现，后续如需多设备同步再对接后端 API

## 相关文件
- `frontend/src/pages/user/Workspace/index.tsx` - 主组件，移除弹窗调用
- `frontend/src/pages/user/Workspace/SkillsTab/index.tsx` - 添加配置项和保存按钮

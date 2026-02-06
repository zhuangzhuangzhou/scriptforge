# 修复项目详情页对接与功能缺失

## 目标
修复项目详情页（Workspace.tsx）与后端的对接问题，确保所有项目信息、统计数据和配置项能够正确显示并保存，同时将 Mock 数据逐步替换为真实接口数据。

## 需求
1. **API 一致性修复**:
   - 修复 `api.ts` 中 Mock 数据的字段名，由 `camelCase` 统一为 `snake_case` (如 `total_chapters`)。
   - 确保 `getProject` 返回值结构始终为 `{ data: ... }`。
2. **状态与表单绑定**:
   - 在 `Workspace.tsx` 中完善 `formData`，包含 `breakdown_model` 和 `script_model`。
   - 将 UI 中的模型选择下拉框与 `formData` 绑定。
3. **功能增强**:
   - 在配置页增加“删除项目”功能（对应 `projectApi.deleteProject`）。
   - 接入批次数据：在 `Workspace` 中调用 `projectApi.getBatches` 替换 `mockPlots` 和 `mockEpisodes`。
4. **统计数据校准**:
   - 确保 `total_chapters`, `total_words`, `processed_chapters`, `status` 正确从 API 响应映射到 UI。

## 验收标准
- [ ] 项目详情页正确显示后端返回的名称、简介和统计数据（不显示 0 或 未知）。
- [ ] 修改项目设置（名称、简介、批次大小、模型）后点击保存，页面刷新后设置依然保留。
- [ ] 能够成功触发删除项目操作并跳转回仪表盘。
- [ ] 分集大纲（Plot）和剧本生成（Script）列表数据来源于接口（如有数据）。

## 技术说明
- 修改文件：`frontend/src/services/api.ts`, `frontend/src/pages/user/Workspace.tsx`
- 遵循 `.trellis/spec/frontend/` 规范。

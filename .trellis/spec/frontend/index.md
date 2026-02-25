# Frontend 开发规范索引

本目录包含前端开发的所有规范和最佳实践。

## 规范文件

| 文件 | 状态 | 描述 |
|------|------|------|
| [performance-optimization.md](./performance-optimization.md) | ✅ 完成 | 性能优化和缓存策略 |
| [api-integration.md](./api-integration.md) | ✅ 完成 | API 集成最佳实践 |
| [react-hooks-patterns.md](./react-hooks-patterns.md) | ✅ 完成 | React Hooks 最佳实践和常见陷阱 |
| [component-refactoring.md](./component-refactoring.md) | ✅ 完成 | 大型组件重构规范 |
| [ui-consistency.md](./ui-consistency.md) | ✅ 完成 | UI 一致性和布局规范 |

## 快速参考

### 性能优化
- 使用 useRef 缓存映射关系避免重复查询
- 一次性加载数据并缓存，后续操作直接使用
- 避免在 useEffect 中重复调用相同的 API

### API 集成
- 检查网络请求，识别重复调用
- 使用缓存减少不必要的网络请求
- 合理使用 useCallback 和 useMemo

### React Hooks
- 避免异步回调中的闭包陷阱
- 直接调用 API 获取最新数据，不依赖闭包变量
- Custom Hook 回调参数应包含所有必要信息
- 正确管理 useEffect 依赖数组
- 使用清理函数避免内存泄漏
- **双数据源合并**: WebSocket + HTTP 轮询时，使用 `effectiveProgress = wsProgress > 0 ? wsProgress : progress`

### 组件重构
- 文件超过 500 行时考虑重构
- 提取常量配置到文件顶部
- 拆分子组件，保持职责单一
- 统一类型定义，避免重复
- 使用 useMemo/useCallback 优化性能

### UI 一致性
- **必须使用项目定义的 UI 组件**（GlassTable、GlassModal、GlassSelect 等）
- 跨 Tab 保持视觉一致性，使用统一的布局模式
- 信息卡片使用左右分栏布局（主信息 + 次要信息）
- 编辑操作放在右上角，避免底部固定栏
- 不同功能模块使用不同配色方案以区分
- 编辑模式需要双向数据同步（四段式 ↔ 完整剧本）
- 历史版本按钮横排显示，支持版本回滚
- 表格必须添加序号列（固定在左侧）

## 更新日志

- 2026-02-25: UI 一致性规范更新 - 添加项目组件使用规范和表格序号列标准
- 2026-02-25: 添加 UI 一致性规范，记录 Script Tab 重构经验
- 2026-02-25: 更新组件重构规范，添加双数据源合并模式
- 2026-02-22: 创建规范索引，添加性能优化和 API 集成规范

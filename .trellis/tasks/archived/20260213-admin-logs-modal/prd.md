# 日志详情改为弹窗显示

## Goal
将 admin/logs 路径下的日志查看详情从抽屉式（Drawer）显示改为弹窗式（Modal）显示，遵循项目 Glass UI 规范。

## Requirements

1. **TaskDetailDrawer.tsx** 改造
   - 将 Drawer 组件改为 GlassModal 组件
   - 组件重命名为 TaskDetailModal
   - 保持原有功能和数据展示

2. **LLMLogsTab.tsx** 改造
   - 将内联 Drawer 改为 GlassModal
   - 保持原有功能和数据展示

3. **index.tsx** 调用调整
   - 调整 TaskDetailModal 的调用方式
   - 状态变量名从 `drawerVisible` 改为 `modalVisible`

## Acceptance Criteria

- [ ] TaskDetailDrawer.tsx 改为 TaskDetailModal，使用 GlassModal
- [ ] LLMLogsTab.tsx 中的 Drawer 改为 GlassModal
- [ ] index.tsx 中的调用参数相应调整
- [ ] 样式保持一致（深色主题）
- [ ] 运行 lint 检查无错误
- [ ] TypeScript 编译无错误

## Technical Notes

GlassModal 使用方式：
```tsx
<GlassModal
  title="标题"
  open={modalVisible}
  onCancel={handleClose}
  width={800}
>
  {/* 内容 */}
</GlassModal>
```

注意：
- Drawer 的 `placement="right"` 在 Modal 中不需要
- Drawer 的 `onClose` 对应 Modal 的 `onCancel`
- Drawer 的 `open` 对应 Modal 的 `open`（不是 `visible`）
- Modal 默认 `centered` 居中显示

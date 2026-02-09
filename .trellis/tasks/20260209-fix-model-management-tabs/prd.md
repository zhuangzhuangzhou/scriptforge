# 修复模型管理页面标签页黑屏问题

## 目标
修复 `/admin/models` 页面中多个标签页点击后出现黑屏的问题。

## 问题描述
- **页面路径**: `/admin/models`
- **问题现象**: 点击标签页后页面显示黑屏
- **影响范围**: 模型管理页面的所有标签页（提供商管理、模型配置、凭证管理、计费规则、系统配置）

## 可能原因
1. **组件渲染错误**: 子组件内部有未捕获的异常
2. **API 调用失败**: 数据加载失败导致组件崩溃
3. **样式问题**: CSS 导致内容不可见（背景色、z-index 等）
4. **路由问题**: 组件未正确加载
5. **依赖缺失**: 缺少必要的 UI 组件或服务

## 需要检查的文件
- `frontend/src/pages/admin/ModelManagement.tsx` - 主组件
- `frontend/src/pages/admin/ModelManagement/ProviderManagement.tsx`
- `frontend/src/pages/admin/ModelManagement/ModelConfiguration.tsx`
- `frontend/src/pages/admin/ModelManagement/CredentialManagement.tsx`
- `frontend/src/pages/admin/ModelManagement/PricingManagement.tsx`
- `frontend/src/pages/admin/ModelManagement/SystemConfiguration.tsx`
- `frontend/src/components/ui/GlassTabs.tsx`
- `frontend/src/services/modelManagementApi.ts`

## 修复步骤
1. 在浏览器开发者工具中检查控制台错误
2. 检查每个子组件是否有渲染错误
3. 验证 API 服务是否正确配置
4. 检查样式是否导致内容不可见
5. 添加错误边界（Error Boundary）防止组件崩溃
6. 添加加载状态和错误提示

## 验收标准
- [ ] 所有标签页可以正常切换
- [ ] 每个标签页内容正常显示
- [ ] 无控制台错误
- [ ] 有适当的加载状态提示
- [ ] 有错误处理和用户友好的错误提示

## 技术要点
- 使用 React Error Boundary 捕获组件错误
- 确保 API 调用有正确的错误处理
- 验证 GlassTabs 组件的正确使用
- 检查样式冲突

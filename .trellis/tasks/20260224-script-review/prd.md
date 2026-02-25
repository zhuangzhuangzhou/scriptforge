# Script 页面代码审查任务

## 目标

对 Script 页面的前后端功能进行全面代码审查，识别功能缺陷、性能问题和代码质量问题。

## 审查范围

### 前端文件
- `frontend/src/pages/user/ScriptGeneration.tsx` - 剧本生成页面
- `frontend/src/pages/user/Workspace/ScriptTab/index.tsx` - 工作区剧本标签页
- `frontend/src/types.ts` - 类型定义
- `frontend/src/services/api.ts` - API 服务

### 后端文件
- `backend/app/api/v1/scripts.py` - API 端点
- `backend/app/models/script.py` - 数据模型
- `backend/app/tasks/script_tasks.py` - Celery 任务

## 审查维度

### 1. 功能完整性
- [ ] API 端点是否完整覆盖所有功能
- [ ] 错误处理是否完善
- [ ] 边界条件是否处理

### 2. 代码质量
- [ ] 代码结构是否清晰
- [ ] 命名是否规范
- [ ] 是否有重复代码

### 3. 性能问题
- [ ] 是否有重复的 API 调用
- [ ] 是否有不必要的渲染
- [ ] 数据缓存是否合理

### 4. 类型安全
- [ ] TypeScript 类型是否完整
- [ ] Pydantic 模型是否正确定义

### 5. 前后端一致性
- [ ] API 请求/响应格式是否匹配
- [ ] 错误处理是否一致

## 验收标准

- [ ] 生成完整的代码审查报告
- [ ] 列出所有发现的问题（按严重程度分类）
- [ ] 提供具体的修复建议
- [ ] 识别代码中的亮点和最佳实践

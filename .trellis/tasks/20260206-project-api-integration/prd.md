# 完善 Project 接口对接

## Goal
完善 project 相关的前后端 API 对接，补充缺失接口并验证现有实现。

## Requirements

### 1. 补充对接 Batches 接口
- 后端已有 `GET /projects/{project_id}/batches` 接口
- 前端需要在 `ProjectDetail.tsx` 中调用此接口
- 在 `services/api.ts` 中添加对应的 API 方法
- 在项目详情页展示批次列表

### 2. 实现项目日志接口
- 后端实现 `GET /projects/{project_id}/logs` 接口
  - 返回项目相关的日志记录
  - 支持分页和筛选
- 前端已有调用 `logsApi.getLogs`，需确保对接正确
- 在项目详情页能够查看日志

### 3. 验证现有接口
- 使用 Python 脚本验证所有 project 相关接口：
  - POST /projects (创建)
  - GET /projects (列表)
  - GET /projects/{id} (详情)
  - PUT /projects/{id} (更新)
  - DELETE /projects/{id} (删除)
  - POST /projects/{id}/upload (上传)
- 确保前端调用与后端实现匹配

## Acceptance Criteria

- [ ] 后端实现 logs 接口，通过 API 测试验证
- [ ] 前端成功对接 batches 接口
- [ ] 前端成功对接 logs 接口
- [ ] 所有现有 project 接口验证通过
- [ ] 代码通过 lint 和 typecheck
- [ ] 无 console 错误

## Technical Notes

### 后端
- 参考 `backend/app/api/v1/projects.py` 的现有实现
- 日志接口可能需要新建 Log 模型或使用现有日志系统
- 遵循异步模式 (AsyncSession)

### 前端
- 在 `services/api.ts` 中添加方法
- 在 `ProjectDetail.tsx` 中集成显示
- 保持现有 UI 风格，不修改样式
- 支持 Mock 模式开发

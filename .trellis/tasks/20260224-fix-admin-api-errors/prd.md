# 管理端 API 错误修复

## 目标
修复管理端 4 个 API 接口的错误,确保管理后台功能正常运行。

## 问题清单

### 1. `/admin/tasks/stuck` 接口报错
**位置**: `backend/app/api/v1/admin_core.py:1136-1214`

**问题**:
- 使用了 `selectinload(AITask.user)` 但 `AITask` 模型没有 `user` 关系字段
- 应该通过 `Project` 表关联 `User`

**修复方案**:
- 删除 `selectinload(AITask.user)`
- 参考 `/admin/tasks/running` 接口的正确实现（第 476 行）

### 2. `/admin/logs/stats?period=week` 接口报错
**位置**: `backend/app/api/v1/admin_core.py:655-730`

**问题**:
- 第 662 行使用了 `datetime.now(timezone.utc)` 但缺少 `timezone` 导入

**修复方案**:
- 在文件顶部添加 `timezone` 导入: `from datetime import datetime, timedelta, timezone`

### 3. `/admin/llm-logs?skip=0&limit=10` 没有数据
**位置**: `backend/app/api/v1/admin_core.py:891-994`

**问题**:
- 接口逻辑正常,可能是数据库表 `llm_call_logs` 为空或数据被清理
- 需要检查表是否存在数据

**修复方案**:
- 创建检查脚本验证表结构和数据
- 如果表为空,这是正常情况（没有 LLM 调用记录）

### 4. `/v1/admin/api-logs?skip=0&limit=10` 接口报错
**位置**: `backend/app/api/v1/admin_core.py:735-821`

**问题**:
- 第 804、810 行使用了 `getattr(log, 'request_body', None)` 和 `getattr(log, 'response_body', None)`
- 说明 `APILog` 模型可能没有这两个字段或字段名不匹配

**修复方案**:
- 检查 `APILog` 模型定义
- 根据实际字段名修改代码

### 5. `/admin/analytics` 接口问题（附加发现）
**位置**: `backend/app/api/v1/admin_analytics.py:22`

**问题**:
- 缺少 `timezone` 导入

**修复方案**:
- 添加 `timezone` 导入

## 验收标准

- [ ] `/admin/tasks/stuck` 接口正常返回卡住的任务列表
- [ ] `/admin/logs/stats?period=week` 接口正常返回统计数据
- [ ] `/admin/llm-logs?skip=0&limit=10` 接口正常返回（即使数据为空）
- [ ] `/v1/admin/api-logs?skip=0&limit=10` 接口正常返回 API 日志
- [ ] 所有修复通过 Python 脚本验证
- [ ] 代码符合后端开发规范

## 技术要点

1. **导入规范**: 确保所有使用的模块都正确导入
2. **ORM 关系**: 正确使用 SQLAlchemy 的关系加载（`selectinload`）
3. **模型字段**: 确保访问的字段在模型中存在
4. **错误处理**: 遵循后端规范的错误处理模式
5. **API 测试**: 修复后必须用 curl 或 Python 脚本验证

## 相关文件

- `backend/app/api/v1/admin_core.py` - 主要修复文件
- `backend/app/api/v1/admin_analytics.py` - 附加修复
- `backend/app/models/ai_task.py` - 检查模型定义
- `backend/app/models/api_log.py` - 检查模型定义

# 剧集拆解系统待优化项

> 创建日期：2026-02-12

## 优先级说明

- 🔴 高优先级 - 可能导致数据/资金问题
- 🟡 中优先级 - 影响用户体验或代码质量
- 🟢 低优先级 - 技术债务清理

---

## TODO 列表

### 🔴 高优先级

- [ ] **积分双重扣费风险**
  - 文件：`backend/app/api/v1/breakdown.py:159-160` + `backend/app/tasks/breakdown_tasks.py:131-132`
  - 问题：API 层预扣积分，任务完成后又调用 `consume_credits_for_task_sync` 扣费
  - 方案：确认 `consume_credits_for_task_sync` 是否有幂等检查，或改为只在一处扣费

- [ ] **批量任务失败时积分未回滚**
  - 文件：`backend/app/api/v1/breakdown.py:583-635`
  - 问题：批量启动时，中间批次失败，已预扣的积分没有回滚
  - 方案：使用 savepoint 或为每个批次单独处理事务

### 🟡 中优先级

- [ ] **质检循环缺少最大重试限制**
  - 文件：`backend/app/tasks/breakdown_tasks.py` (`_execute_breakdown_sync`)
  - 问题：Agent 执行拆解时，质检失败后的重试没有上限控制
  - 方案：在 Agent 定义或任务配置中添加 `max_qa_retries` 参数

- [ ] **并发控制参数未生效**
  - 文件：`backend/app/api/v1/breakdown.py:55`
  - 问题：`BatchStartRequest.concurrent_limit` 字段定义了但未使用
  - 方案：实现基于 Redis 的并发控制，或使用 Celery 的 rate_limit

- [ ] **JSON 解析正则匹配问题**
  - 文件：`backend/app/tasks/breakdown_tasks.py:1747`
  - 问题：`(\[.*\]|\{.*\})` 贪婪匹配可能匹配错误
  - 方案：改用非贪婪匹配 `(\[.*?\]|\{.*?\})` 或更精确的解析

### 🟢 低优先级

- [ ] **清理废弃的兼容字段**
  - 文件：`backend/app/api/v1/breakdown.py:20-38`
  - 问题：`BreakdownStartRequest` 有过多兼容字段（`adapt_method_key`、`quality_rule_key` 等）
  - 方案：设置迁移截止日期，逐步移除废弃字段

- [ ] **统一错误信息解析方式**
  - 文件：`backend/app/api/v1/breakdown.py:1279`
  - 问题：使用 `eval()` 解析错误信息，存在安全隐患
  - 方案：统一使用 `json.loads()` 解析

---

## 已完成

- [x] 系统架构分析 (2026-02-12)
- [x] 数据格式文档化 (2026-02-12)

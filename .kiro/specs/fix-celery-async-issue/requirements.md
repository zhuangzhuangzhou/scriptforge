# 修复 Celery 异步任务执行问题 - 需求文档

## 1. 问题概述

### 1.1 当前问题
- **症状**: 所有拆解任务一直处于 `queued` 状态，无法执行
- **根本原因**: SQLAlchemy 异步引擎与 Celery worker 的同步上下文不兼容
- **错误信息**: `greenlet_spawn has not been called; can't call await_only() here`

### 1.2 技术背景
- Celery worker 在同步上下文中运行
- FastAPI 使用异步 SQLAlchemy (asyncpg)
- `asyncio.run()` 和 `asyncio.new_event_loop()` 都无法解决 greenlet 上下文问题
- `nest_asyncio` 与 `uvloop` 冲突，无法使用

## 2. 用户故事

### 2.1 作为系统管理员
我希望 Celery 任务能够稳定执行，这样用户提交的拆解任务可以正常处理。

**验收标准**:
- Celery worker 启动后不会崩溃
- 任务可以从 `queued` 状态转换到 `running` 状态
- 任务可以成功完成或失败（带有明确的错误信息）

### 2.2 作为开发者
我希望有一个清晰的数据库访问模式，这样在 Celery 任务中可以安全地访问数据库。

**验收标准**:
- 有明确的同步数据库会话创建方法
- 代码简单易懂，易于维护
- 不会出现 greenlet 或事件循环相关的错误

### 2.3 作为用户
我希望提交的拆解任务能够被处理，这样我可以看到拆解结果。

**验收标准**:
- 提交任务后，任务状态会在合理时间内更新
- 可以通过 API 查看任务进度
- 任务失败时有清晰的错误提示

## 3. 功能需求

### 3.1 创建同步数据库引擎
- 创建一个专门用于 Celery 任务的同步数据库引擎
- 使用 `psycopg2` 而不是 `asyncpg`
- 配置合适的连接池参数

### 3.2 重写 Celery 任务为同步版本
- 将 `run_breakdown_task` 改为完全同步的实现
- 移除所有 `async/await` 关键字
- 使用同步的数据库会话

### 3.3 创建同步版本的辅助函数
- 同步版本的 `update_task_progress`
- 同步版本的 `get_adapter`
- 同步版本的 `PipelineExecutor`（如果需要）

### 3.4 保持 API 端点的异步实现
- FastAPI 端点继续使用异步 SQLAlchemy
- 只有 Celery 任务使用同步版本
- 两套代码共存，互不干扰

## 4. 非功能需求

### 4.1 性能
- 同步数据库操作不应显著影响任务执行速度
- 连接池应该能够处理并发任务

### 4.2 可维护性
- 代码结构清晰，易于理解
- 同步和异步代码有明确的分界
- 有充分的注释说明为什么需要两套实现

### 4.3 兼容性
- 不影响现有的 FastAPI 异步端点
- 不影响现有的数据库模型定义
- 向后兼容现有的任务配置

## 5. 约束条件

### 5.1 技术约束
- 必须使用 SQLAlchemy ORM（不能直接使用原始 SQL）
- 必须保持现有的数据库模型定义
- 不能修改 Celery 的核心配置

### 5.2 时间约束
- 需要尽快修复，因为影响核心功能
- 修复应该是渐进式的，可以分步实施

## 6. 成功标准

### 6.1 功能验证
- [ ] Celery worker 可以成功启动
- [ ] 可以提交新的拆解任务
- [ ] 任务状态可以正常更新（queued → running → completed/failed）
- [ ] 任务失败时有清晰的错误信息
- [ ] 任务成功时可以查看结果

### 6.2 稳定性验证
- [ ] Worker 运行 24 小时不崩溃
- [ ] 可以连续处理 10 个任务不出错
- [ ] 数据库连接池不会耗尽

### 6.3 代码质量
- [ ] 代码通过 lint 检查
- [ ] 有充分的注释
- [ ] 有清晰的文档说明架构决策

## 7. 风险和缓解措施

### 7.1 风险：维护两套代码
- **影响**: 增加维护成本
- **缓解**: 
  - 创建清晰的代码组织结构
  - 编写详细的文档
  - 考虑未来统一为同步或异步

### 7.2 风险：性能下降
- **影响**: 任务执行变慢
- **缓解**:
  - 优化数据库查询
  - 使用合适的连接池配置
  - 监控任务执行时间

### 7.3 风险：数据一致性问题
- **影响**: 同步和异步代码可能产生不一致的结果
- **缓解**:
  - 使用相同的数据库模型
  - 使用事务确保一致性
  - 编写集成测试

## 8. 依赖项

### 8.1 Python 包
- `psycopg2-binary`: PostgreSQL 同步驱动
- `sqlalchemy`: ORM（已安装）
- `celery`: 任务队列（已安装）

### 8.2 系统组件
- PostgreSQL 数据库（已运行）
- Redis（已运行）
- Celery worker（需要重启）

## 9. 时间线

### 阶段 1: 准备工作（30 分钟）
- 安装 `psycopg2-binary`
- 创建同步数据库引擎
- 编写测试脚本

### 阶段 2: 核心实现（1-2 小时）
- 重写 `run_breakdown_task` 为同步版本
- 创建同步辅助函数
- 更新相关导入

### 阶段 3: 测试和验证（30 分钟）
- 重启 Celery worker
- 提交测试任务
- 验证任务执行流程

### 阶段 4: 文档和清理（30 分钟）
- 更新文档
- 清理旧代码
- 添加注释

## 10. 参考资料

- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html)
- `docs/CELERY_ASYNC_FINAL_FIX.md` - 详细的技术分析
- `docs/TASK_LIFECYCLE_EXPLANATION.md` - 任务生命周期说明

---

**创建时间**: 2026-02-10
**优先级**: P0 (Critical)
**估计工作量**: 2-3 小时

# 修复 Breakdown Worker 执行逻辑 - 实现任务

## 概述

本任务列表将修复 breakdown worker 的核心问题，并新增实时流式输出功能。主要包括：

1. 实现 Redis 日志发布服务
2. 重构 worker 支持流式输出
3. 新增 WebSocket 实时日志端点
4. 完善测试覆盖

**注意**：配额回滚功能和安全的 JSON 解析已经在现有代码中实现，无需重复开发。

## 任务列表

- [-] 1. 实现 Redis 日志发布服务
  - 创建 `backend/app/core/redis_log_publisher.py` 文件
  - 实现 `RedisLogPublisher` 类（同步版本）
  - 实现 `publish_step_start()`, `publish_stream_chunk()`, `publish_step_end()`, `publish_error()` 方法
  - 使用同步 Redis 客户端（`redis.Redis`）
  - 频道命名规范：`breakdown:logs:{task_id}`
  - 发布失败时静默处理，不中断任务执行
  - 所有消息使用统一的 JSON 格式（包含 type, task_id, timestamp, step_name, content, metadata 字段）
  - _Requirements: 3.4.2, 3.4.3_

- [ ] 1.1 编写 Redis 日志发布的单元测试
  - 测试消息格式正确性（验证所有必需字段存在）
  - 测试发布成功场景
  - 测试 Redis 不可用时的降级处理
  - 使用 mock Redis 客户端
  - _Requirements: 3.4.2_

- [x] 2. 重构拆解技能函数支持流式输出
  - 修改 `backend/app/tasks/breakdown_tasks.py` 中的拆解函数
  - 为每个拆解函数添加 `log_publisher` 和 `task_id` 参数：
    - `_extract_conflicts_sync()`
    - `_identify_plot_hooks_sync()`
    - `_analyze_characters_sync()`
    - `_identify_scenes_sync()`
    - `_extract_emotions_sync()`
  - 使用 `model_adapter.stream_generate()` 替代 `generate()`
  - 在步骤开始时发布 `step_start` 消息
  - 在流式生成过程中实时发布 `stream_chunk` 消息
  - 在步骤结束时发布 `step_end` 消息（包含结果统计）
  - 异常时发布 `error` 消息
  - _Requirements: 3.4.1, 3.4.4, 3.1.2_

- [x] 3. 更新主 worker 任务函数
  - 修改 `run_breakdown_task()` 函数
  - 初始化 `RedisLogPublisher` 实例（从环境变量读取 Redis URL）
  - 将 `log_publisher` 和 `task_id` 传递给所有拆解技能函数
  - 在 `_execute_breakdown_sync()` 函数中传递 log_publisher
  - 确保异常处理中也能发布错误消息
  - _Requirements: 3.4.1, 3.4.3_

- [ ]* 3.1 编写 worker 流式输出的单元测试
  - 测试每个拆解函数正确发布消息
  - 测试消息顺序（start -> chunks -> end）
  - 测试异常时发布 error 消息
  - 使用 mock Redis publisher 和 model adapter
  - _Requirements: 3.4.1, 3.4.4_

- [x] 4. 实现 WebSocket 实时日志端点
  - 在 `backend/app/api/v1/` 目录下创建 `websocket.py` 文件（如果不存在）
  - 实现 `websocket_breakdown_logs(websocket: WebSocket, task_id: str)` 函数
  - 订阅 Redis 频道 `breakdown:logs:{task_id}`
  - 接收消息并转发到前端
  - 检测任务完成状态（status 为 completed 或 failed）并关闭连接
  - 正确处理 WebSocket 断开和异常
  - 使用异步 Redis 客户端（`redis.asyncio.Redis`）
  - _Requirements: 3.4.1, 3.4.3_

- [x] 5. 更新路由注册
  - 在 `backend/app/api/v1/router.py` 中导入 websocket 模块
  - 注册 WebSocket 端点路由
  - 确保路由路径为 `/ws/breakdown-logs/{task_id}`
  - _Requirements: 3.4.3_

- [x] 6. Checkpoint - 运行基础测试
  - 运行单元测试：`pytest backend/tests/ -v`
  - 验证 Redis 日志发布服务正常工作
  - 验证 WebSocket 端点可以建立连接
  - 如有问题，询问用户

- [ ]* 7. 编写集成测试
  - [ ]* 7.1 编写完整拆解流程集成测试
    - 创建测试批次和章节数据
    - 提交拆解任务
    - 验证任务状态变化
    - 验证拆解结果保存到数据库
    - 验证配额正确消耗
    - _Requirements: 3.1.1, 3.1.2, 3.1.3, 3.1.4_
  
  - [ ]* 7.2 编写流式输出集成测试
    - 建立 WebSocket 连接
    - 提交拆解任务
    - 验证接收到 step_start 消息
    - 验证接收到 stream_chunk 消息
    - 验证接收到 step_end 消息
    - 验证消息顺序正确
    - 验证消息格式符合规范
    - _Requirements: 3.4.1, 3.4.2, 3.4.3, 3.4.4_
  
  - [ ]* 7.3 编写错误恢复集成测试
    - 模拟模型 API 失败
    - 验证任务状态为 "retrying"
    - 验证重试机制触发
    - 验证最终失败后配额回滚
    - 验证错误消息通过 WebSocket 推送
    - _Requirements: 3.2.1, 3.3.1, 3.4.3_

- [ ]* 8. 编写属性测试
  - [ ]* 8.1 属性测试：完整拆解流程正确性
    - **Property 1: 完整拆解流程正确性**
    - 使用 hypothesis 生成随机批次和章节数据
    - 验证 worker 能完成所有步骤
    - 运行 100+ 次迭代
    - **Validates: Requirements 3.1.1, 3.1.2, 3.1.3, 3.1.4**
  
  - [ ]* 8.2 属性测试：配额回滚一致性
    - **Property 2: 配额回滚一致性**
    - 生成随机失败场景
    - 验证配额总是被正确返还
    - 验证事务一致性
    - **Validates: Requirements 3.2.1, 3.2.2**
  
  - [ ]* 8.3 属性测试：错误信息完整性
    - **Property 3: 错误信息完整性**
    - 生成各种错误场景
    - 验证错误信息包含所有必需字段
    - 验证使用 JSON 格式存储
    - **Validates: Requirements 3.3.1, 3.3.2, 3.3.3**
  
  - [ ]* 8.4 属性测试：流式消息格式规范
    - **Property 4: 流式消息格式规范**
    - 生成随机任务执行
    - 验证所有消息符合格式规范
    - 验证消息可被 json.loads() 解析
    - 验证必需字段存在（type, task_id, timestamp, step_name）
    - **Validates: Requirements 3.4.2**
  
  - [ ]* 8.5 属性测试：流式推送完整性
    - **Property 5: 流式推送完整性**
    - 生成随机拆解任务
    - 验证每个步骤都有 start/chunks/end 消息
    - 验证消息顺序正确
    - **Validates: Requirements 3.4.1, 3.4.3, 3.4.4**
  
  - [ ]* 8.6 属性测试：JSON 解析安全性
    - **Property 6: JSON 解析安全性**
    - 生成各种格式的模型响应
    - 验证不使用 eval()
    - 验证解析失败时返回默认值
    - **Validates: Requirements 3.3.3**

- [x] 9. 代码审查和清理
  - 确保所有新增代码有类型提示
  - 添加必要的文档字符串
  - 检查日志记录是否完善
  - 运行 linting 工具（`flake8`, `black`）
  - 确保没有硬编码的配置值（使用环境变量）

- [x] 10. 最终 Checkpoint
  - 运行完整测试套件
  - 验证测试覆盖率达标（> 80%）
  - 验证所有 linting 检查通过
  - 手动测试 WebSocket 连接和流式输出
  - 询问用户是否有其他问题

## 注意事项

1. **标记为 `*` 的任务是可选的测试任务**，可以根据时间和优先级决定是否实现
2. 每个任务都引用了对应的需求编号，便于追溯
3. 建议按顺序执行任务，因为后续任务依赖前面的实现
4. Checkpoint 任务用于验证阶段性成果，确保质量
5. 属性测试使用 `hypothesis` 库，每个测试至少运行 100 次迭代
6. **配额回滚功能已实现**：`refund_episode_quota_sync()` 已存在于 `backend/app/core/quota.py`
7. **JSON 解析已安全**：`_parse_json_response_sync()` 已使用 `json.loads()`，不使用 `eval()`

## 已完成的功能

以下功能已在现有代码中实现，无需重复开发：

- ✅ 配额回滚逻辑（`refund_episode_quota_sync` 函数）
- ✅ 安全的 JSON 解析（`_parse_json_response_sync` 函数）
- ✅ 错误分类和处理（`classify_exception` 和错误处理函数）
- ✅ Celery 任务重试机制
- ✅ 数据库事务管理

## 测试命令

```bash
# 运行所有测试
pytest backend/tests/ -v

# 运行特定测试文件
pytest backend/tests/test_breakdown_worker.py -v

# 运行测试并生成覆盖率报告
pytest backend/tests/ --cov=app --cov-report=html

# 运行 linting
flake8 backend/app/
black backend/app/ --check

# 运行类型检查
mypy backend/app/
```

## 依赖库

确保安装以下 Python 库：

```bash
# 核心依赖
pip install redis hypothesis pytest pytest-cov pytest-asyncio

# WebSocket 支持
pip install websockets

# 异步 Redis 客户端
pip install redis[hiredis]
```

## 环境变量配置

需要在 `.env` 文件中配置以下变量：

```bash
# Redis 配置（用于 Celery 和 Pub/Sub）
REDIS_URL=redis://localhost:6379/0

# Celery 配置
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# 数据库配置
DATABASE_URL=postgresql://user:pass@localhost/dbname

# 模型配置
MODEL_TIMEOUT=120  # 模型调用超时时间（秒）
```

## 实现优先级

**P0 - 必须实现（核心功能）：**
- 任务 1: Redis 日志发布服务
- 任务 2: 重构拆解函数支持流式输出
- 任务 3: 更新主 worker 函数
- 任务 4: WebSocket 实时日志端点
- 任务 5: 更新路由注册

**P1 - 应该实现（质量保证）：**
- 任务 6: Checkpoint 测试
- 任务 9: 代码审查和清理
- 任务 10: 最终 Checkpoint

**P2 - 可选实现（完善测试）：**
- 任务 1.1, 3.1: 单元测试
- 任务 7: 集成测试
- 任务 8: 属性测试

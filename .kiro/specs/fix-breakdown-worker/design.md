# 修复 Breakdown Worker 执行逻辑 - 设计文档

## 1. 概述

本设计文档描述了如何修复 `breakdown/start` 接口及其 worker 执行逻辑中的问题，并新增实时流式输出功能。主要目标包括：

1. 修复配额回滚逻辑缺失的问题
2. 移除 `eval()` 安全漏洞，使用安全的 JSON 解析
3. 完善错误处理机制
4. **新增实时流式输出功能**，让用户通过前端 system console 实时看到大模型的拆解过程

### 1.1 核心改进

- **配额管理**：实现同步版本的配额回滚逻辑，确保任务失败时配额被正确返还
- **安全性**：移除所有 `eval()` 调用，使用 `json.loads()` 安全解析 JSON
- **错误处理**：区分可重试和不可重试错误，记录详细的错误堆栈
- **实时流式输出**：使用 Redis Pub/Sub + WebSocket 实现实时日志推送

### 1.2 技术栈

- **后端框架**：FastAPI + Celery
- **数据库**：PostgreSQL (同步 SQLAlchemy)
- **消息队列**：Redis (Celery broker + Pub/Sub)
- **实时通信**：WebSocket
- **AI 模型**：支持流式生成的模型适配器

## 2. 架构设计

### 2.1 整体架构

```mermaid
graph TB
    A[前端 System Console] -->|WebSocket| B[FastAPI WebSocket 端点]
    B -->|订阅| C[Redis Pub/Sub]
    D[Celery Worker] -->|发布消息| C
    D -->|读写| E[PostgreSQL]
    D -->|流式调用| F[AI 模型 API]
    F -->|流式响应| D
    G[FastAPI /breakdown/start] -->|提交任务| H[Celery Queue]
    H -->|分发| D
```


### 2.2 数据流

#### 2.2.1 任务提交流程

1. 用户通过前端提交拆解任务
2. FastAPI 接口验证权限和配额
3. 预扣配额，创建 AITask 记录
4. 提交 Celery 任务到队列
5. 返回 task_id 给前端

#### 2.2.2 任务执行流程（新增流式输出）

1. Celery worker 接收任务
2. 更新任务状态为 "running"
3. 加载章节数据
4. **对每个拆解技能**：
   - 发布 "step_start" 消息到 Redis
   - 调用模型适配器的 `stream_generate()` 方法
   - **实时发布每个流式 chunk 到 Redis**
   - 解析完整响应
   - 发布 "step_end" 消息到 Redis
5. 保存拆解结果到数据库
6. 更新任务状态为 "completed"

#### 2.2.3 实时推送流程

1. 前端建立 WebSocket 连接到 `/ws/breakdown-logs/{task_id}`
2. WebSocket 端点订阅 Redis 频道 `breakdown:logs:{task_id}`
3. Worker 发布消息到该频道
4. WebSocket 端点接收消息并推送给前端
5. 前端 system console 实时显示消息

### 2.3 消息格式规范

所有通过 Redis Pub/Sub 传递的消息使用统一的 JSON 格式：

```json
{
  "type": "step_start" | "stream_chunk" | "step_end" | "error" | "progress",
  "task_id": "uuid",
  "timestamp": "ISO 8601 timestamp",
  "step_name": "提取冲突" | "识别情节钩子" | ...,
  "content": "消息内容",
  "metadata": {
    "progress": 20,
    "total_steps": 5,
    "current_step": 1
  }
}
```

#### 消息类型说明

- **step_start**: 开始执行某个拆解技能
- **stream_chunk**: 模型返回的流式内容片段
- **step_end**: 完成某个拆解技能
- **error**: 错误信息
- **progress**: 进度更新

## 3. 组件和接口

### 3.1 配额服务（QuotaService）

#### 3.1.1 新增同步方法

```python
class QuotaService:
    def refund_episode_quota_sync(self, db: Session, user_id: str, amount: int = 1) -> None:
        """同步版本：返还剧集配额
        
        Args:
            db: 同步数据库会话
            user_id: 用户ID
            amount: 返还数量
        """
```

**职责**：
- 查询用户记录
- 增加用户的剧集配额
- 记录配额变更日志
- 提交事务


### 3.2 Redis 日志发布服务

#### 3.2.1 RedisLogPublisher

```python
class RedisLogPublisher:
    """Redis 日志发布器（同步版本）"""
    
    def __init__(self, redis_url: str):
        """初始化 Redis 连接"""
        
    def publish_log(self, task_id: str, message: dict) -> None:
        """发布日志消息到 Redis
        
        Args:
            task_id: 任务ID
            message: 消息字典（包含 type, content 等字段）
        """
        
    def publish_step_start(self, task_id: str, step_name: str, metadata: dict = None) -> None:
        """发布步骤开始消息"""
        
    def publish_stream_chunk(self, task_id: str, step_name: str, chunk: str) -> None:
        """发布流式内容片段"""
        
    def publish_step_end(self, task_id: str, step_name: str, result: dict = None) -> None:
        """发布步骤结束消息"""
        
    def publish_error(self, task_id: str, error_message: str, error_code: str = None) -> None:
        """发布错误消息"""
```

**设计要点**：
- 使用同步 Redis 客户端（`redis.Redis`）
- 频道命名：`breakdown:logs:{task_id}`
- 消息序列化为 JSON
- 发布失败不应中断任务执行（静默失败）

### 3.3 模型适配器增强

#### 3.3.1 流式生成方法

所有模型适配器已实现 `stream_generate()` 方法（继承自 `BaseModelAdapter`）：

```python
def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
    """流式生成文本
    
    Args:
        prompt: 提示词
        **kwargs: 额外参数
        
    Yields:
        str: 文本片段
    """
```

**使用示例**：

```python
for chunk in model_adapter.stream_generate(prompt):
    # 实时发布到 Redis
    log_publisher.publish_stream_chunk(task_id, step_name, chunk)
    # 累积完整响应
    full_response += chunk
```

### 3.4 Breakdown Worker 重构

#### 3.4.1 主任务函数

```python
@celery_app.task(**CELERY_TASK_CONFIG)
def run_breakdown_task(self, task_id: str, batch_id: str, project_id: str, user_id: str):
    """执行 Breakdown 任务（支持流式输出）"""
```

**改进点**：
1. 初始化 `RedisLogPublisher`
2. 在每个拆解步骤前后发布消息
3. 使用 `stream_generate()` 替代 `generate()`
4. 实时发布流式内容
5. 失败时调用配额回滚

#### 3.4.2 拆解技能函数重构

每个拆解技能函数（如 `_extract_conflicts_sync`）需要重构以支持流式输出：

```python
def _extract_conflicts_sync(
    chapters_text: str,
    model_adapter,
    task_config: dict,
    log_publisher: RedisLogPublisher,
    task_id: str
) -> list:
    """提取冲突（支持流式输出）"""
    
    step_name = "提取冲突"
    
    # 发布步骤开始
    log_publisher.publish_step_start(task_id, step_name)
    
    # 构建 prompt
    prompt = "..."
    
    # 流式调用模型
    full_response = ""
    try:
        for chunk in model_adapter.stream_generate(prompt):
            log_publisher.publish_stream_chunk(task_id, step_name, chunk)
            full_response += chunk
        
        # 解析结果
        result = _parse_json_response_sync(full_response, default=[])
        
        # 发布步骤结束
        log_publisher.publish_step_end(task_id, step_name, {"count": len(result)})
        
        return result
        
    except Exception as e:
        log_publisher.publish_error(task_id, str(e))
        raise
```


### 3.5 WebSocket 端点

#### 3.5.1 实时日志推送端点

```python
@router.websocket("/ws/breakdown-logs/{task_id}")
async def websocket_breakdown_logs(websocket: WebSocket, task_id: str):
    """WebSocket 端点：实时推送拆解日志
    
    功能：
    - 订阅 Redis 频道 breakdown:logs:{task_id}
    - 接收并转发所有日志消息到前端
    - 任务完成或失败时自动关闭连接
    """
```

**实现要点**：
1. 接受 WebSocket 连接
2. 创建 Redis Pub/Sub 订阅
3. 循环接收消息并转发
4. 检测任务结束状态
5. 清理资源

### 3.6 JSON 解析安全性

#### 3.6.1 安全解析函数

```python
def _parse_json_response_sync(response: str, default=None):
    """安全解析 JSON 响应
    
    Args:
        response: 模型返回的文本
        default: 解析失败时的默认值
        
    Returns:
        解析后的 Python 对象
        
    安全措施：
    - 使用 json.loads() 而不是 eval()
    - 支持提取 Markdown 代码块中的 JSON
    - 支持提取纯 JSON 数组/对象
    - 解析失败返回默认值，不抛出异常
    """
```

**实现逻辑**：
1. 尝试直接解析整个响应
2. 如果失败，尝试提取 ```json...``` 代码块
3. 如果失败，尝试提取任何 JSON 数组或对象
4. 如果全部失败，返回默认值

**禁止使用**：
- `eval()`
- `exec()`
- `compile()` + `eval()`

## 4. 数据模型

### 4.1 AITask 模型（现有）

```python
class AITask(Base):
    id: UUID
    project_id: UUID
    batch_id: UUID
    task_type: str  # "breakdown"
    status: str  # "queued", "running", "completed", "failed", "retrying"
    progress: int  # 0-100
    current_step: str  # 当前执行步骤
    error_message: str  # JSON 格式的错误信息
    retry_count: int
    config: dict  # 任务配置
    celery_task_id: str
    created_at: datetime
    updated_at: datetime
```

**改进**：
- `error_message` 字段存储 JSON 字符串（使用 `json.dumps()`）
- 不再使用 `eval()` 解析该字段

### 4.2 配额记录（现有）

用户配额存储在 `User` 模型中：

```python
class User(Base):
    id: UUID
    episodes_used: int  # 已使用的剧集数
    episodes_limit: int  # 剧集配额上限
```

### 4.3 Redis 消息格式

#### 4.3.1 步骤开始消息

```json
{
  "type": "step_start",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T10:30:00Z",
  "step_name": "提取冲突",
  "metadata": {
    "progress": 20,
    "total_steps": 5,
    "current_step": 1
  }
}
```

#### 4.3.2 流式内容片段

```json
{
  "type": "stream_chunk",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T10:30:01Z",
  "step_name": "提取冲突",
  "content": "[\n  {\n    \"type\": \"人物冲突\","
}
```

#### 4.3.3 步骤结束消息

```json
{
  "type": "step_end",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T10:30:15Z",
  "step_name": "提取冲突",
  "metadata": {
    "count": 3,
    "duration_ms": 15000
  }
}
```

#### 4.3.4 错误消息

```json
{
  "type": "error",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T10:30:20Z",
  "step_name": "提取冲突",
  "content": "模型 API 调用失败: Connection timeout",
  "metadata": {
    "error_code": "MODEL_API_ERROR",
    "retryable": true
  }
}
```


## 5. 正确性属性

*属性是一个特征或行为，应该在系统的所有有效执行中保持为真——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1：完整拆解流程正确性

*对于任何*有效的批次和章节数据，当提交拆解任务时，worker 应该能够：
1. 成功加载章节数据
2. 调用模型适配器的生成方法
3. 解析模型返回的结果
4. 将拆解结果保存到数据库

**验证：Requirements 3.1.1, 3.1.2, 3.1.3, 3.1.4**

### 属性 2：配额回滚一致性

*对于任何*失败的拆解任务，系统应该：
1. 检测到任务失败
2. 调用配额回滚函数
3. 将用户的剧集配额增加相应数量
4. 在数据库事务中完成配额返还

**验证：Requirements 3.2.1, 3.2.2**

### 属性 3：错误信息完整性

*对于任何*模型调用失败或任务执行错误，系统应该：
1. 捕获异常信息
2. 构造包含错误代码、消息、时间戳的错误对象
3. 使用 `json.dumps()` 序列化错误信息
4. 将序列化后的 JSON 字符串存储到 `AITask.error_message` 字段

**验证：Requirements 3.3.1, 3.3.2, 3.3.3**

### 属性 4：流式消息格式规范

*对于任何*发布到 Redis 的流式消息，消息应该：
1. 包含 `type` 字段（值为 step_start, stream_chunk, step_end, error 之一）
2. 包含 `task_id` 字段
3. 包含 `timestamp` 字段（ISO 8601 格式）
4. 包含 `step_name` 字段（对于拆解相关消息）
5. 能够被 `json.loads()` 成功解析

**验证：Requirements 3.4.2**

### 属性 5：流式推送完整性

*对于任何*拆解任务的执行，系统应该：
1. 在每个拆解步骤开始时发布 `step_start` 消息
2. 在模型流式生成过程中发布多个 `stream_chunk` 消息
3. 在每个拆解步骤结束时发布 `step_end` 消息
4. 所有消息都能通过 WebSocket 实时到达前端

**验证：Requirements 3.4.1, 3.4.3, 3.4.4**

### 属性 6：JSON 解析安全性

*对于任何*模型返回的文本响应，解析函数应该：
1. 不使用 `eval()` 或 `exec()`
2. 仅使用 `json.loads()` 进行解析
3. 解析失败时返回默认值而不是抛出异常
4. 能够处理包含 Markdown 代码块的响应

**验证：Requirements 3.3.3**

## 6. 错误处理

### 6.1 错误分类

#### 6.1.1 可重试错误（RetryableError）

- 网络超时
- 连接错误
- 模型 API 限流（429）
- 临时服务不可用（503）

**处理策略**：
- 更新任务状态为 "retrying"
- 记录重试次数
- 让 Celery 自动重试（最多 3 次）
- 使用指数退避策略

#### 6.1.2 配额不足错误（QuotaExceededError）

- 用户剧集配额已用尽
- 模型 token 配额不足

**处理策略**：
- 更新任务状态为 "failed"
- 回滚已消耗的配额
- 记录详细错误信息
- 不进行重试

#### 6.1.3 不可重试错误（AITaskException）

- 模型配置错误
- 数据不存在
- 权限不足
- JSON 解析失败（在多次尝试后）

**处理策略**：
- 更新任务状态为 "failed"
- 回滚已消耗的配额
- 记录详细错误信息
- 不进行重试

### 6.2 错误处理流程

```python
try:
    # 执行拆解逻辑
    result = _execute_breakdown_sync(...)
    
except RetryableError as e:
    # 可重试错误
    _handle_retryable_error_sync(db, task_id, batch_record, task_record, e)
    raise  # 让 Celery 处理重试
    
except QuotaExceededError as e:
    # 配额不足
    _handle_quota_exceeded_sync(db, task_id, batch_record, task_record, user_id, e)
    raise
    
except AITaskException as e:
    # 其他任务错误
    _handle_task_failure_sync(db, task_id, batch_record, task_record, user_id, e)
    raise
    
except Exception as e:
    # 未知错误：分类后处理
    classified_error = classify_exception(e)
    if isinstance(classified_error, RetryableError):
        _handle_retryable_error_sync(...)
        raise
    else:
        _handle_task_failure_sync(...)
        raise
```


### 6.3 配额回滚实现

```python
def _refund_quota_sync(db: Session, user_id: str, amount: int = 1):
    """回滚用户配额（同步版本）
    
    Args:
        db: 同步数据库会话
        user_id: 用户ID
        amount: 返还数量
    """
    try:
        # 查询用户
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            print(f"配额回滚失败: 用户不存在 {user_id}")
            return
        
        # 返还配额
        user.episodes_used = max(0, user.episodes_used - amount)
        
        # 记录日志
        print(f"配额回滚成功: 用户 {user_id} 返还 {amount} 集")
        
        # 提交事务
        db.commit()
        
    except Exception as e:
        # 配额回滚失败不应阻止错误传播
        print(f"配额回滚失败: {e}")
        db.rollback()
```

**设计要点**：
- 使用数据库事务保证原子性
- 回滚失败不应中断错误处理流程
- 记录详细的回滚日志
- 确保配额不会变成负数

### 6.4 错误信息序列化

所有错误信息使用 JSON 格式存储：

```python
error_info = {
    "code": error.code,
    "message": error.message,
    "timestamp": datetime.utcnow().isoformat(),
    "retry_count": task_record.retry_count,
    "stack_trace": traceback.format_exc()
}

# 安全序列化
error_json = json.dumps(error_info)

# 存储到数据库
update_task_progress_sync(
    db, task_id,
    status="failed",
    error_message=error_json
)
```

**禁止**：
```python
# ❌ 不安全的做法
error_message = str(error_dict)  # 使用 str() 可能导致格式问题
task.error_message = eval(error_string)  # 使用 eval() 存在安全风险
```

## 7. 测试策略

### 7.1 单元测试

#### 7.1.1 配额回滚测试

- 测试正常回滚场景
- 测试用户不存在场景
- 测试数据库事务回滚
- 测试并发回滚

#### 7.1.2 JSON 解析测试

- 测试纯 JSON 解析
- 测试 Markdown 代码块提取
- 测试格式错误的 JSON
- 测试空响应
- 测试特殊字符

#### 7.1.3 错误分类测试

- 测试网络错误分类
- 测试配额错误分类
- 测试模型错误分类
- 测试未知错误分类

#### 7.1.4 Redis 日志发布测试

- 测试消息格式
- 测试发布成功
- 测试发布失败（Redis 不可用）
- 测试消息序列化

### 7.2 集成测试

#### 7.2.1 完整拆解流程测试

- 创建测试批次和章节
- 提交拆解任务
- 验证任务状态变化
- 验证拆解结果保存
- 验证配额消耗

#### 7.2.2 流式输出测试

- 建立 WebSocket 连接
- 提交拆解任务
- 验证接收到 step_start 消息
- 验证接收到 stream_chunk 消息
- 验证接收到 step_end 消息
- 验证消息顺序正确

#### 7.2.3 错误恢复测试

- 模拟模型 API 失败
- 验证任务状态为 "retrying"
- 验证重试机制触发
- 验证最终失败后配额回滚

#### 7.2.4 并发测试

- 同时提交多个拆解任务
- 验证配额正确扣除
- 验证任务独立执行
- 验证流式消息不混淆

### 7.3 属性测试配置

所有属性测试使用 `pytest` + `hypothesis` 库：

- 每个测试运行 **最少 100 次迭代**
- 使用随机生成的测试数据
- 每个测试标记对应的设计属性

**标记格式**：
```python
@pytest.mark.property
@pytest.mark.feature("fix-breakdown-worker")
@pytest.mark.validates("Property 1: 完整拆解流程正确性")
def test_complete_breakdown_flow_property():
    """属性测试：完整拆解流程正确性"""
    # 测试实现
```

### 7.4 测试覆盖率目标

- 单元测试覆盖率：> 80%
- 核心函数覆盖率：100%
- 错误处理路径覆盖率：> 90%

## 8. 性能考虑

### 8.1 流式输出性能

- **批量发布**：累积多个小 chunk 后再发布，减少 Redis 操作
- **消息大小限制**：单个消息不超过 1MB
- **频道清理**：任务完成后清理 Redis 频道

### 8.2 数据库性能

- 使用连接池（已配置）
- 批量查询章节数据
- 减少不必要的 commit 操作
- 使用索引优化查询

### 8.3 模型调用性能

- 设置合理的超时时间（120 秒）
- 使用流式生成减少等待时间
- 实现请求重试机制

## 9. 安全性

### 9.1 代码注入防护

- **移除所有 `eval()` 调用**
- 使用 `json.loads()` 安全解析 JSON
- 验证所有外部输入
- 使用参数化查询防止 SQL 注入

### 9.2 权限验证

- 验证用户对批次的访问权限
- 验证用户配额
- 验证模型配置权限

### 9.3 数据验证

- 验证 task_id 格式（UUID）
- 验证 batch_id 存在性
- 验证章节数据完整性
- 验证模型返回数据格式

## 10. 部署和配置

### 10.1 环境变量

```bash
# Redis 配置
REDIS_URL=redis://localhost:6379/0

# Celery 配置
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# 数据库配置
DATABASE_URL=postgresql://user:pass@localhost/dbname

# 模型配置
MODEL_TIMEOUT=120  # 模型调用超时时间（秒）
```

### 10.2 Celery Worker 配置

```bash
# 启动 worker
celery -A app.core.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=100
```

### 10.3 Redis 配置

```bash
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

## 11. 监控和日志

### 11.1 日志级别

- **INFO**：任务开始、完成、步骤进度
- **WARNING**：重试、配额不足
- **ERROR**：任务失败、模型错误
- **DEBUG**：详细的执行信息

### 11.2 关键指标

- 任务成功率
- 平均执行时间
- 配额回滚次数
- 模型 API 调用失败率
- WebSocket 连接数

### 11.3 告警规则

- 任务失败率 > 10%
- 配额回滚次数异常增加
- Redis 连接失败
- 数据库连接池耗尽

## 12. 向后兼容性

### 12.1 API 兼容性

- `/breakdown/start` 接口签名不变
- 响应格式保持一致
- 错误码保持兼容

### 12.2 数据库兼容性

- 不修改现有表结构
- `error_message` 字段继续使用 TEXT 类型
- 新旧错误格式都能正确解析

### 12.3 前端兼容性

- 新增 WebSocket 端点不影响现有功能
- 前端可选择是否使用实时日志功能
- 降级方案：不连接 WebSocket 时使用轮询


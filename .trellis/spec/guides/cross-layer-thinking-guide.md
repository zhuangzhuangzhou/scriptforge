# 跨层数据流思考指南

## 概述

本文档通过实际案例,展示如何追踪和理解跨越多个架构层的数据流。

---

## 案例 1: WebSocket 批次自动切换

### 需求描述
当批次 N 拆解完成后,自动启动批次 N+1,并通知前端切换到新批次。

### 涉及的层次

```
Layer 1: 后端任务层 (Celery Task)
    ↓
Layer 2: 后端基础设施层 (Redis Pub/Sub)
    ↓
Layer 3: 后端 API 层 (WebSocket Endpoint)
    ↓
Layer 4: 前端 Hook 层 (useBreakdownLogs)
    ↓
Layer 5: 前端 UI 层 (Workspace Component)
```

### 完整数据流追踪

#### Layer 1: 后端任务层
**文件**: `backend/app/tasks/breakdown_tasks.py`

```python
def run_breakdown_task(task_id: str):
    """执行拆解任务"""
    # ... 执行拆解逻辑

    # 任务完成后,触发下一个批次
    _trigger_next_task_sync(
        completed_task_id=task_id,
        project_id=project_id,
        user_id=user_id
    )

def _trigger_next_task_sync(completed_task_id: str, ...):
    """触发下一个批次"""
    # 1. 查找下一个待拆解批次
    next_batch = db.query(Batch).filter(
        Batch.project_id == project_id,
        Batch.breakdown_status == 'pending'
    ).order_by(Batch.batch_number).first()

    # 2. 创建新任务
    new_task = BreakdownTask(
        batch_id=next_batch.id,
        status='queued'
    )
    db.add(new_task)

    # 3. 启动 Celery 任务
    run_breakdown_task.apply_async(args=[str(new_task.id)])

    # 4. 提交事务
    db.commit()

    # 5. 推送批次切换消息 (关键步骤)
    log_publisher.publish_batch_switch(
        old_task_id=completed_task_id,  # 旧任务 ID
        new_task_id=str(new_task.id),   # 新任务 ID
        new_batch_id=str(next_batch.id),
        new_batch_number=next_batch.batch_number
    )
```

**关键决策**:
- ✅ 在 `db.commit()` **之后**推送消息,确保数据一致性
- ✅ 使用 try-except 包裹推送逻辑,失败不影响主流程

#### Layer 2: 后端基础设施层
**文件**: `backend/app/core/redis_log_publisher.py`

```python
class RedisLogPublisher:
    def publish_batch_switch(
        self,
        old_task_id: str,
        new_task_id: str,
        new_batch_id: str,
        new_batch_number: int
    ) -> None:
        """发布批次切换消息"""
        # 1. 构建消息
        msg = self._build_message(
            message_type="batch_switch",
            task_id=old_task_id,  # 注意: 使用旧任务 ID
            content=f"批次 {new_batch_number} 已开始拆解",
            metadata={
                "new_task_id": new_task_id,
                "new_batch_id": new_batch_id,
                "new_batch_number": new_batch_number,
                "auto_switch": True
            }
        )

        # 2. 发送到 Redis
        self.publish_log(old_task_id, msg)
        # 实际频道: breakdown:logs:{old_task_id}
```

**关键决策**:
- ✅ 消息发送到**旧任务的频道**,因为前端正在监听旧任务
- ✅ 使用统一的 `_build_message` 方法,确保消息格式一致

#### Layer 3: 后端 API 层
**文件**: `backend/app/api/v1/websocket.py`

```python
@router.websocket("/ws/breakdown-logs/{task_id}")
async def websocket_breakdown_logs(websocket: WebSocket, task_id: str):
    """WebSocket 端点: 流式日志"""
    await websocket.accept()

    # 订阅 Redis 频道
    channel = f"breakdown:logs:{task_id}"
    pubsub = redis_client.pubsub()
    pubsub.subscribe(channel)

    # 转发消息到前端
    for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            await websocket.send_json(data)
```

**关键决策**:
- ✅ WebSocket 端点只负责转发,不做业务逻辑
- ✅ 频道命名: `breakdown:logs:{task_id}`

#### Layer 4: 前端 Hook 层
**文件**: `frontend/src/hooks/useBreakdownLogs.ts`

```typescript
export const useBreakdownLogs = (
  taskId: string | null,
  options: UseBreakdownLogsOptions = {}
) => {
  const { onBatchSwitch, ... } = options;

  const handleMessage = useCallback((data: StreamMessage) => {
    switch (data.type) {
      case 'batch_switch':
        // 提取新批次信息
        const { new_task_id, new_batch_id, new_batch_number } = data.metadata;

        // 触发回调
        onBatchSwitch?.({
          newTaskId: new_task_id,
          newBatchId: new_batch_id,
          newBatchNumber: new_batch_number
        });

        // 显示提示信息
        onInfo?.(`批次 ${new_batch_number} 已开始拆解，正在切换...`);
        break;
    }
  }, [onBatchSwitch, onInfo]);

  // 连接 WebSocket
  const { ... } = useWebSocket(
    `/api/v1/ws/breakdown-logs/${taskId}`,
    { onMessage: handleMessage }
  );
};
```

**关键决策**:
- ✅ Hook 提供 `onBatchSwitch` 回调接口,让上层组件处理业务逻辑
- ✅ 回调参数包含所有必要信息,避免闭包陷阱

#### Layer 5: 前端 UI 层
**文件**: `frontend/src/pages/user/Workspace/index.tsx`

```typescript
const Workspace = () => {
  const [batches, setBatches] = useState([]);
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [breakdownTaskId, setBreakdownTaskId] = useState(null);

  // 使用 Hook,提供回调处理
  useBreakdownLogs(breakdownTaskId, {
    onBatchSwitch: async (switchInfo) => {
      console.log('[Workspace] 收到批次切换消息:', switchInfo);

      try {
        // 1. 刷新批次列表 (直接调用 API,避免闭包陷阱)
        const res = await projectApi.getBatches(projectId!, 1, 20);
        const freshBatches = res.data?.items || [];
        setBatches(freshBatches);

        // 2. 切换到新批次
        const newBatch = freshBatches.find(
          (b: any) => b.id === switchInfo.newBatchId
        );

        if (newBatch) {
          setSelectedBatch(newBatch);
          setBreakdownTaskId(switchInfo.newTaskId);
          message.info(`已自动切换到批次 ${switchInfo.newBatchNumber}`);
        }
      } catch (err) {
        console.error('[Workspace] 批次切换失败:', err);
        message.error('批次切换失败');
      }
    }
  });
};
```

**关键决策**:
- ✅ 直接调用 API 获取最新批次列表,避免使用闭包变量 `batches`
- ✅ 完整的错误处理和用户提示

---

## 数据流分析方法

### 1. 自顶向下追踪

**适用场景**: 从用户操作开始,追踪到后端处理

**步骤**:
1. 用户点击按钮 → 触发事件处理函数
2. 调用 API → 发送 HTTP 请求
3. 后端路由 → 调用 Service 层
4. Service 层 → 操作数据库
5. 返回响应 → 更新前端 UI

### 2. 自底向上追踪

**适用场景**: 从后端事件开始,追踪到前端更新

**步骤**:
1. 后端任务完成 → 触发事件
2. 推送消息到 Redis → WebSocket 转发
3. 前端 Hook 接收 → 触发回调
4. 组件处理回调 → 更新 UI

### 3. 关键节点识别

**数据转换点**:
- 数据库模型 → API 响应格式
- WebSocket 消息 → Hook 回调参数
- Hook 状态 → 组件 Props

**错误处理点**:
- API 调用失败
- WebSocket 连接断开
- 数据验证失败

---

## 常见问题

### 问题 1: 数据不一致

**症状**: 前端显示的数据与后端不一致

**排查步骤**:
1. 检查后端是否正确更新数据库
2. 检查 API 是否返回最新数据
3. 检查前端是否正确更新 state
4. 检查是否有缓存问题

**案例**: 批次状态显示错误
```typescript
// ❌ 问题: 使用本地缓存的 batches
const batch = batches.find(b => b.id === batchId);

// ✅ 解决: 调用 API 获取最新数据
const res = await api.getBatch(batchId);
const batch = res.data;
```

### 问题 2: 消息丢失

**症状**: WebSocket 消息没有到达前端

**排查步骤**:
1. 检查后端是否成功推送消息 (查看日志)
2. 检查 Redis 频道名称是否一致
3. 检查 WebSocket 连接是否正常
4. 检查前端是否正确处理消息类型

**案例**: 频道名称不一致
```python
# 后端
redis.publish("breakdown:logs:task-1", msg)

# 前端
ws.connect("/ws/breakdown-logs/task-1")  # ✅ 正确
ws.connect("/ws/breakdown_logs/task-1")  # ❌ 错误: 下划线
```

### 问题 3: 时序问题

**症状**: 消息到达顺序错误,导致状态混乱

**排查步骤**:
1. 检查消息发送顺序
2. 检查是否有并发问题
3. 检查前端处理逻辑是否考虑时序

**案例**: task_complete 先于 batch_switch
```python
# ❌ 问题: 前端收到 task_complete 后关闭连接
publish_task_complete(task_id)
publish_batch_switch(...)  # 消息发送时连接已关闭

# ✅ 解决 1: 延迟关闭连接
setTimeout(() => ws.close(), 2000);

# ✅ 解决 2: 调整发送顺序
publish_batch_switch(...)
publish_task_complete(task_id)
```

---

## 调试技巧

### 1. 添加日志追踪

```python
# 后端: 每个关键步骤添加日志
logger.info(f"[Layer1] 任务完成: {task_id}")
logger.info(f"[Layer2] 推送消息到 Redis: {channel}")

# 前端: 每个关键步骤添加日志
console.log('[Layer4] 收到 WebSocket 消息:', data);
console.log('[Layer5] 触发回调:', switchInfo);
```

### 2. 使用唯一标识追踪

```python
# 生成追踪 ID
trace_id = str(uuid.uuid4())

# 在所有层传递
logger.info(f"[{trace_id}] Layer1: 开始处理")
redis.publish(channel, {"trace_id": trace_id, ...})
console.log(`[${trace_id}] Layer4: 收到消息`);
```

### 3. 绘制数据流图

```
[用户点击] → [handleClick] → [API.startBreakdown]
                                      ↓
                              [POST /api/breakdown]
                                      ↓
                              [BreakdownService.start]
                                      ↓
                              [Celery Task]
                                      ↓
                              [Redis Pub/Sub]
                                      ↓
                              [WebSocket]
                                      ↓
                              [useBreakdownLogs]
                                      ↓
                              [onBatchSwitch]
                                      ↓
                              [UI 更新]
```

---

## 最佳实践

### 1. 单向数据流

```
后端 → API → Hook → Component
     (不要反向依赖)
```

### 2. 明确的层次职责

| 层次 | 职责 | 不应该做 |
|------|------|----------|
| 后端任务层 | 业务逻辑、数据处理 | 不关心前端如何展示 |
| 基础设施层 | 消息推送、缓存 | 不包含业务逻辑 |
| API 层 | 数据转换、验证 | 不直接操作数据库 |
| Hook 层 | 状态管理、副作用 | 不包含 UI 逻辑 |
| UI 层 | 展示、交互 | 不直接调用底层 API |

### 3. 错误处理的层次传递

```typescript
// Layer 1: 捕获并记录
try {
    await processData();
} catch (err) {
    logger.error('处理失败', err);
    throw new ProcessError('数据处理失败');
}

// Layer 2: 转换为 API 错误
try {
    await service.process();
} catch (err) {
    throw new ApiError(500, '服务器错误');
}

// Layer 3: 展示给用户
try {
    await api.process();
} catch (err) {
    message.error('操作失败,请重试');
}
```

---

## 相关文档

- [后端 WebSocket 模式](../backend/websocket-patterns.md)
- [前端 React Hooks 模式](../frontend/react-hooks-patterns.md)
- [数据库事务管理](../backend/database-transactions.md)

---

## 更新日志

| 日期 | 更新内容 | 作者 |
|------|----------|------|
| 2026-02-23 | 初始版本: 跨层数据流思考指南 | Claude Opus 4.6 |

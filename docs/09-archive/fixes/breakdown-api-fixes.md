# /breakdown/start 接口修复总结

## 修复的问题

### 1. ✅ 添加重复提交检查

**修复内容**:
```python
# 检查是否已有任务在执行（防止重复提交）
existing_task_result = await db.execute(
    select(AITask).where(
        AITask.batch_id == request.batch_id,
        AITask.status.in_(["queued", "running"])
    )
)
existing_task = existing_task_result.scalar_one_or_none()

if existing_task:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"该批次已有任务在执行中，任务ID: {existing_task.id}"
    )
```

**影响**:
- ✅ 防止用户多次点击导致重复创建任务
- ✅ 防止配额被多次扣除
- ✅ 返回 409 Conflict 状态码，前端可以识别并提示用户

### 2. ✅ 使用数据库锁防止配额竞态条件

**修复内容**:
```python
async with db.begin():
    # 锁定用户记录，防止并发请求导致配额超支
    user_result = await db.execute(
        select(User).where(User.id == current_user.id).with_for_update()
    )
    locked_user = user_result.scalar_one()
    
    # 在锁内检查和消耗配额
    quota_service = QuotaService(db)
    quota = await quota_service.check_episode_quota(locked_user)
    if not quota["allowed"]:
        raise HTTPException(...)
    
    await quota_service.consume_episode_quota(locked_user)
    # ... 创建任务 ...
```

**影响**:
- ✅ 使用 `with_for_update()` 锁定用户记录
- ✅ 防止并发请求同时检查配额导致超支
- ✅ 配额检查和消耗在同一个事务中，保证原子性

### 3. ✅ 改进错误处理

**修复内容**:
```python
try:
    # ... 任务创建逻辑 ...
    
    # Celery 提交
    try:
        celery_task = run_breakdown_task.delay(...)
        task.celery_task_id = celery_task.id
    except Exception:
        # Celery 连接失败
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="任务队列服务不可用，请稍后重试"
        )

except HTTPException:
    # 重新抛出 HTTP 异常（包括配额不足、重复提交等）
    raise
except Exception as e:
    # 其他未预期的错误
    await db.rollback()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"任务创建失败: {str(e)}"
    )
```

**影响**:
- ✅ 区分不同类型的错误
- ✅ Celery 连接失败返回 503（服务不可用）
- ✅ 配额不足返回 403（禁止访问）
- ✅ 重复提交返回 409（冲突）
- ✅ 批次不存在返回 404（未找到）
- ✅ 其他错误返回 500（服务器错误）

### 4. ✅ 改进事务管理

**修复内容**:
```python
# 之前：使用 begin_nested()
async with db.begin_nested():
    # ...
await db.commit()

# 现在：使用 begin()
async with db.begin():
    # ...
# 事务自动提交
```

**影响**:
- ✅ 使用正确的事务管理方式
- ✅ 事务在 `async with` 块结束时自动提交
- ✅ 异常时自动回滚

## 修复的接口

1. ✅ `POST /breakdown/start` - 启动单个批次拆解
2. ✅ `POST /breakdown/start-all` - 批量启动所有未拆解批次
3. ✅ `POST /breakdown/continue/{project_id}` - 继续拆解
4. ✅ `POST /breakdown/batch-start` - 批量启动拆解（增强版）

## 测试建议

### 1. 测试重复提交检查

```bash
# 快速连续发送两次请求
curl -X POST "http://localhost:8000/api/v1/breakdown/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"batch_id": "xxx", ...}'

# 第二次应该返回 409 Conflict
```

### 2. 测试配额竞态条件

```bash
# 使用多个并发请求测试
for i in {1..10}; do
  curl -X POST "http://localhost:8000/api/v1/breakdown/start" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"batch_id": "xxx", ...}' &
done
wait

# 检查配额是否正确扣除（应该只扣除一次）
```

### 3. 测试错误处理

```bash
# 测试 Celery 不可用
# 停止 Celery worker
pkill -9 -f "celery.*worker"

# 发送请求，应该返回 503
curl -X POST "http://localhost:8000/api/v1/breakdown/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"batch_id": "xxx", ...}'

# 应该返回: {"detail": "任务队列服务不可用，请稍后重试"}
```

### 4. 测试配额不足

```bash
# 消耗所有配额后再次请求
# 应该返回 403
curl -X POST "http://localhost:8000/api/v1/breakdown/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"batch_id": "xxx", ...}'

# 应该返回: {"detail": "剧集配额已用尽，本月已使用 X/Y 集"}
```

## 性能影响

### 数据库锁的影响

**使用 `with_for_update()` 的性能影响**:
- ⚠️ 会锁定用户记录，阻塞其他并发请求
- ✅ 但锁定时间很短（只在事务内）
- ✅ 对于单用户的并发请求，这是必要的
- ✅ 不同用户之间不会相互影响

**优化建议**:
- 事务内的操作尽可能快
- 避免在事务内进行耗时操作（如 AI 调用）
- 只锁定必要的记录

## 向后兼容性

### API 响应格式

**保持不变**:
```json
{
  "task_id": "xxx",
  "status": "queued"
}
```

**新增错误响应**:
```json
// 409 Conflict - 重复提交
{
  "detail": "该批次已有任务在执行中，任务ID: xxx"
}

// 503 Service Unavailable - Celery 不可用
{
  "detail": "任务队列服务不可用，请稍后重试"
}
```

### 前端适配建议

```typescript
try {
  const response = await api.post('/breakdown/start', data);
  // 成功
} catch (error) {
  if (error.response?.status === 409) {
    // 重复提交，提示用户任务已在执行中
    message.warning('该批次已有任务在执行中');
  } else if (error.response?.status === 503) {
    // 服务不可用，提示用户稍后重试
    message.error('任务队列服务不可用，请稍后重试');
  } else if (error.response?.status === 403) {
    // 配额不足
    message.error('剧集配额已用尽');
  } else {
    // 其他错误
    message.error('任务创建失败');
  }
}
```

## 未修复的问题

### 配额消耗时机（按用户要求保持不变）

**当前逻辑**:
- 配额在任务启动时就被消耗（预扣）
- 任务失败时会退还配额

**优点**:
- 防止用户在任务执行期间超支配额
- 配额管理更严格

**缺点**:
- 如果退还逻辑有 bug，用户配额可能被错误扣除
- 任务失败时需要手动退还配额

**建议**: 确保所有失败场景都正确退还配额

## 总结

### 修复内容

1. ✅ 添加重复提交检查（防止多次创建任务）
2. ✅ 使用数据库锁防止配额竞态条件
3. ✅ 改进错误处理（区分不同错误类型）
4. ✅ 改进事务管理（使用正确的事务方式）

### 影响范围

- 4 个接口函数
- 约 200 行代码修改
- 无 API 破坏性变更
- 向后兼容

### 测试状态

- ✅ 代码语法检查通过
- ⏳ 需要进行功能测试
- ⏳ 需要进行并发测试
- ⏳ 需要进行错误场景测试

---

**修复时间**: 2026-02-10
**修复人员**: AI Assistant
**状态**: ✅ 已完成

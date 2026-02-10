# Breakdown API 接口问题分析

**日期**: 2026-02-10  
**状态**: 🔍 问题分析

---

## 发现的问题

### 1. 事务管理问题 ❌

**问题代码**:
```python
async with db.begin():
    # ... 创建任务 ...
    # ... 启动 Celery ...
    # 更新批次状态

# 事务自动提交
await db.refresh(task)  # ❌ 在事务外执行
```

**问题**:
- `async with db.begin()` 会在代码块结束时自动提交事务
- `await db.refresh(task)` 在事务外执行，可能导致数据不一致
- 如果 refresh 失败，事务已经提交，无法回滚

**正确做法**:
```python
# 不使用 async with db.begin()，手动管理事务
# ... 创建任务 ...
# ... 启动 Celery ...
# 更新批次状态

await db.commit()  # 手动提交
await db.refresh(task)  # 在提交后刷新
```

### 2. 配额回滚问题 ❌

**问题代码**:
```python
async with db.begin():
    # 消耗配额
    await quota_service.consume_episode_quota(locked_user)
    
    # 创建任务
    task = AITask(...)
    db.add(task)
    await db.flush()
    
    # 启动 Celery
    try:
        celery_task = run_breakdown_task.delay(...)
    except Exception:
        # ❌ 抛出异常会导致事务回滚
        # ❌ 但配额已经在数据库中消耗了
        raise HTTPException(...)
```

**问题**:
- Celery 启动失败时抛出异常
- 异常导致 `async with db.begin()` 自动回滚事务
- 配额消耗也被回滚了（这是对的）
- 但是如果在事务提交后 Celery 失败，配额就无法回滚

**正确做法**:
```python
# 先消耗配额
await quota_service.consume_episode_quota(locked_user)

# 创建任务
task = AITask(...)
db.add(task)
await db.flush()

# 启动 Celery
try:
    celery_task = run_breakdown_task.delay(...)
    task.celery_task_id = celery_task.id
except Exception:
    # Celery 失败，回滚整个事务（包括配额）
    await db.rollback()
    raise HTTPException(...)

# 更新批次状态
batch.breakdown_status = "queued"

# 提交事务
await db.commit()
await db.refresh(task)
```

### 3. 异常处理不完整 ❌

**问题代码**:
```python
try:
    async with db.begin():
        # ... 操作 ...
    
    await db.refresh(task)
    return {"task_id": str(task.id)}

except HTTPException:
    raise
except Exception as e:
    await db.rollback()  # ❌ 事务已经提交或回滚，这里无效
    raise HTTPException(...)
```

**问题**:
- `async with db.begin()` 已经自动提交或回滚
- 外层的 `await db.rollback()` 无效
- 异常处理逻辑混乱

**正确做法**:
```python
try:
    # ... 操作 ...
    await db.commit()
    await db.refresh(task)
    return {"task_id": str(task.id)}
except HTTPException:
    # HTTP 异常直接抛出
    raise
except Exception as e:
    # 其他异常，回滚并抛出
    await db.rollback()
    raise HTTPException(...)
```

### 4. 锁的使用问题 ⚠️

**当前代码**:
```python
async with db.begin():
    user_result = await db.execute(
        select(User).where(User.id == current_user.id).with_for_update()
    )
    locked_user = user_result.scalar_one()
```

**问题**:
- `with_for_update()` 在事务内有效
- 如果不使用 `async with db.begin()`，需要确保在同一个事务中

**正确做法**:
```python
# 在事务开始前锁定
user_result = await db.execute(
    select(User).where(User.id == current_user.id).with_for_update()
)
locked_user = user_result.scalar_one()

# 后续操作都在同一个事务中
# ...

await db.commit()
```

---

## 受影响的接口

1. ✅ `POST /breakdown/start` - 已修复
2. ❌ `POST /breakdown/start-all` - 需要修复
3. ❌ `POST /breakdown/continue/{project_id}` - 需要修复
4. ❌ `POST /breakdown/batch-start` - 需要修复

---

## 修复方案

### 统一的事务管理模式

```python
@router.post("/start")
async def start_breakdown(...):
    # 1. 验证数据（不需要事务）
    batch = ...
    project = ...
    
    # 2. 检查权限和配置（不需要事务）
    if not project.breakdown_model_id:
        raise HTTPException(...)
    
    # 3. 检查重复提交（不需要事务）
    existing_task = ...
    if existing_task:
        raise HTTPException(...)
    
    # 4. 锁定用户（开始事务）
    user_result = await db.execute(
        select(User).where(User.id == current_user.id).with_for_update()
    )
    locked_user = user_result.scalar_one()
    
    # 5. 检查配额
    quota_service = QuotaService(db)
    quota = await quota_service.check_episode_quota(locked_user)
    if not quota["allowed"]:
        raise HTTPException(...)
    
    # 6. 消耗配额
    await quota_service.consume_episode_quota(locked_user)
    
    # 7. 创建任务
    task = AITask(...)
    db.add(task)
    await db.flush()
    
    # 8. 启动 Celery
    try:
        celery_task = run_breakdown_task.delay(...)
        task.celery_task_id = celery_task.id
    except Exception:
        # Celery 失败，回滚事务
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="任务队列服务不可用，请稍后重试"
        )
    
    # 9. 更新批次状态
    batch.breakdown_status = "queued"
    
    # 10. 提交事务
    await db.commit()
    await db.refresh(task)
    
    # 11. 返回结果
    return {"task_id": str(task.id), "status": "queued"}
```

### 关键点

1. **不使用 `async with db.begin()`**
   - 手动管理事务更清晰
   - 避免自动提交导致的问题

2. **Celery 失败时回滚**
   - 捕获 Celery 异常
   - 调用 `await db.rollback()`
   - 配额和任务都会被回滚

3. **提交后刷新**
   - `await db.commit()` 提交事务
   - `await db.refresh(task)` 刷新对象

4. **锁的正确使用**
   - `with_for_update()` 在事务开始时使用
   - 确保后续操作在同一个事务中

---

## 测试场景

### 场景 1: 正常流程
1. 用户启动拆解
2. 配额检查通过
3. 任务创建成功
4. Celery 启动成功
5. 事务提交
6. 返回任务 ID

**预期结果**: ✅ 配额消耗，任务创建，批次状态更新

### 场景 2: 配额不足
1. 用户启动拆解
2. 配额检查失败
3. 抛出 403 异常

**预期结果**: ✅ 配额未消耗，任务未创建

### 场景 3: Celery 服务不可用
1. 用户启动拆解
2. 配额检查通过
3. 任务创建成功
4. Celery 启动失败
5. 回滚事务
6. 抛出 503 异常

**预期结果**: ✅ 配额未消耗，任务未创建，批次状态未变

### 场景 4: 重复提交
1. 用户启动拆解
2. 检测到已有任务在执行
3. 抛出 409 异常

**预期结果**: ✅ 配额未消耗，不创建新任务

### 场景 5: 并发请求
1. 两个请求同时启动同一批次
2. 第一个请求锁定用户
3. 第二个请求等待锁
4. 第一个请求完成后释放锁
5. 第二个请求检测到重复提交

**预期结果**: ✅ 只有一个任务被创建

---

## 修复优先级

1. **高优先级** - `POST /breakdown/start` ✅ 已修复
2. **高优先级** - `POST /breakdown/batch-start` ❌ 需要修复
3. **中优先级** - `POST /breakdown/start-all` ❌ 需要修复
4. **中优先级** - `POST /breakdown/continue/{project_id}` ❌ 需要修复

---

**分析完成时间**: 2026-02-10  
**分析人员**: AI Assistant

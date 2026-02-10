# Breakdown API 最终修复报告

**日期**: 2026-02-10  
**状态**: ✅ 全部完成

---

## 修复的问题

### 1. 缺少路由装饰器 ✅
**问题**: 三个端点函数定义了但没有注册到路由
- `start_all_breakdowns` - 缺少 `@router.post("/start-all")`
- `start_continue_breakdown` - 缺少 `@router.post("/continue/{project_id}")`
- `start_batch_breakdown` - 缺少 `@router.post("/batch-start")`

**影响**: 这些端点无法被访问，返回 404

**修复**: 添加了正确的路由装饰器

---

### 2. 批量操作的配额泄漏问题 ✅
**问题**: 在 `/start-all` 和 `/batch-start` 端点中，当 Celery 启动失败时：
1. 配额已经被消耗
2. 任务被标记为失败或记录到 failed_batches
3. 但配额没有被退还
4. 最终 `await db.commit()` 提交了所有配额消耗

**错误的流程**:
```python
for batch in batches:
    # 1. 先消耗配额
    await quota_service.consume_episode_quota(locked_user)
    
    # 2. 创建任务
    task = AITask(...)
    db.add(task)
    await db.flush()
    
    # 3. 启动 Celery
    try:
        celery_task = run_breakdown_task.delay(...)
    except Exception:
        # ❌ 配额已消耗但没有退还！
        failed_batches.append(str(batch.id))
        continue

# 4. 提交所有更改（包括失败批次的配额消耗）
await db.commit()
```

**正确的流程**:
```python
for batch in batches:
    # 1. 先创建任务（不消耗配额）
    task = AITask(...)
    db.add(task)
    await db.flush()
    
    # 2. 启动 Celery
    try:
        celery_task = run_breakdown_task.delay(...)
        task.celery_task_id = celery_task.id
        
        # 3. ✅ Celery 成功后才消耗配额
        await quota_service.consume_episode_quota(locked_user)
        
    except Exception:
        # 4. ✅ Celery 失败，删除任务记录，不消耗配额
        await db.delete(task)
        failed_batches.append(str(batch.id))
        continue
    
    # 5. 更新批次状态
    batch.breakdown_status = "queued"
    task_ids.append(str(task.id))

# 6. 提交所有更改（只包含成功批次的配额消耗）
await db.commit()
```

---

## 修复后的端点状态

### 1. POST /breakdown/start ✅
**状态**: 正确

**特点**:
- 单批次操作
- 使用手动事务管理
- Celery 失败时调用 `await db.rollback()` 回滚所有更改
- 成功时调用 `await db.commit()` 和 `await db.refresh(task)`

**流程**:
```python
# 1. 锁定用户
user = await db.execute(select(User).where(...).with_for_update())

# 2. 检查配额
quota = await quota_service.check_episode_quota(user)

# 3. 消耗配额（预扣）
await quota_service.consume_episode_quota(user)

# 4. 创建任务
task = AITask(...)
db.add(task)
await db.flush()

# 5. 启动 Celery
try:
    celery_task = run_breakdown_task.delay(...)
    task.celery_task_id = celery_task.id
except Exception:
    # ✅ 回滚配额和任务
    await db.rollback()
    raise HTTPException(503, "任务队列服务不可用")

# 6. 更新批次状态
batch.breakdown_status = "queued"

# 7. 提交事务
await db.commit()
await db.refresh(task)
```

---

### 2. POST /breakdown/continue/{project_id} ✅
**状态**: 正确

**特点**:
- 单批次操作（第一个 pending 批次）
- 与 `/start` 相同的事务管理模式
- Celery 失败时回滚所有更改

**流程**: 与 `/start` 相同

---

### 3. POST /breakdown/start-all ✅
**状态**: 已修复

**特点**:
- 批量操作（所有 pending 批次）
- 先创建任务，Celery 成功后才消耗配额
- Celery 失败时删除任务记录，不消耗配额
- 最终提交只包含成功批次的更改

**修复内容**:
1. ✅ 添加了 `@router.post("/start-all")` 装饰器
2. ✅ 调整了配额消耗时机：Celery 成功后才消耗
3. ✅ Celery 失败时删除任务记录：`await db.delete(task)`

**流程**:
```python
# 1. 锁定用户
user = await db.execute(select(User).where(...).with_for_update())

# 2. 检查配额
required_quota = len(batches)
quota = await quota_service.check_episode_quota(user)
if quota["remaining"] < required_quota:
    raise HTTPException(403, "配额不足")

# 3. 批量处理
task_ids = []
failed_batches = []

for batch in batches:
    try:
        # 3.1 创建任务（不消耗配额）
        task = AITask(...)
        db.add(task)
        await db.flush()
        
        # 3.2 启动 Celery
        try:
            celery_task = run_breakdown_task.delay(...)
            task.celery_task_id = celery_task.id
            
            # ✅ Celery 成功后才消耗配额
            await quota_service.consume_episode_quota(user)
            
        except Exception:
            # ✅ Celery 失败，删除任务记录
            await db.delete(task)
            failed_batches.append(str(batch.id))
            continue
        
        # 3.3 更新批次状态
        batch.breakdown_status = "queued"
        task_ids.append(str(task.id))
        
    except Exception:
        failed_batches.append(str(batch.id))
        continue

# 4. 提交事务（只包含成功批次）
await db.commit()

# 5. 返回结果
if failed_batches:
    return {
        "task_ids": task_ids,
        "total": len(task_ids),
        "failed": len(failed_batches),
        "message": f"成功启动 {len(task_ids)} 个任务，{len(failed_batches)} 个失败"
    }

return {"task_ids": task_ids, "total": len(task_ids)}
```

---

### 4. POST /breakdown/batch-start ✅
**状态**: 已修复

**特点**:
- 批量操作（所有 pending 或 failed 批次）
- 支持自定义配置参数
- 与 `/start-all` 相同的事务管理模式

**修复内容**:
1. ✅ 添加了 `@router.post("/batch-start")` 装饰器
2. ✅ 调整了配额消耗时机：Celery 成功后才消耗
3. ✅ Celery 失败时删除任务记录：`await db.delete(task)`

**流程**: 与 `/start-all` 相同，但支持自定义配置

---

## 关键设计决策

### 为什么单批次和批量操作使用不同的错误处理策略？

**单批次操作** (`/start`, `/continue`):
- 使用 `await db.rollback()` + 抛出异常
- 原因：只有一个批次，失败就应该立即返回错误
- 用户体验：明确知道操作失败，可以重试

**批量操作** (`/start-all`, `/batch-start`):
- 使用 `await db.delete(task)` + 继续处理
- 原因：多个批次，部分失败不应该影响其他批次
- 用户体验：知道哪些成功、哪些失败，可以针对性重试

### 为什么批量操作要先创建任务再消耗配额？

**原因**:
1. **避免配额泄漏**: Celery 失败时不需要退还配额
2. **简化错误处理**: 只需删除任务记录，不需要复杂的回滚逻辑
3. **保证一致性**: 配额消耗和任务创建要么都成功，要么都不成功

**权衡**:
- 优点：配额管理更安全，不会出现配额泄漏
- 缺点：任务记录会短暂存在（flush 后到 delete 前），但这个时间窗口很小

---

## 测试要点

### 单批次操作测试

**测试 `/start` 和 `/continue`**:

1. ✅ **正常流程**
   - 配额消耗
   - 任务创建
   - Celery 启动
   - 批次状态更新
   - 返回 task_id

2. ✅ **配额不足**
   - 返回 403
   - 配额未消耗
   - 任务未创建

3. ✅ **Celery 不可用**
   - 返回 503
   - 配额未消耗（已回滚）
   - 任务未创建（已回滚）

4. ✅ **重复提交**
   - 返回 409
   - 不创建新任务

5. ✅ **并发请求**
   - 使用 `with_for_update()` 锁定用户
   - 只有一个请求成功

### 批量操作测试

**测试 `/start-all` 和 `/batch-start`**:

1. ✅ **全部成功**
   - 所有批次的配额消耗
   - 所有任务创建
   - 所有 Celery 启动
   - 所有批次状态更新
   - 返回所有 task_ids

2. ✅ **部分 Celery 失败**
   - 成功批次：配额消耗，任务创建
   - 失败批次：配额未消耗，任务未创建
   - 返回成功和失败的统计

3. ✅ **配额不足**
   - 返回 403
   - 配额未消耗
   - 任务未创建

4. ✅ **全部 Celery 失败**
   - 配额未消耗
   - 任务未创建
   - 返回 failed 统计

---

## 相关文档

- [问题分析](./BREAKDOWN_API_ISSUES.md)
- [修复总结](./BREAKDOWN_API_FIX_SUMMARY.md)
- [Celery 修复](./CELERY_FIX_SUMMARY.md)

---

## 总结

所有 4 个 breakdown 端点现在都已正确实现：

1. ✅ **POST /breakdown/start** - 单批次启动
2. ✅ **POST /breakdown/continue/{project_id}** - 继续拆解
3. ✅ **POST /breakdown/start-all** - 批量启动所有 pending 批次
4. ✅ **POST /breakdown/batch-start** - 批量启动（支持自定义配置）

**关键改进**:
- ✅ 添加了缺失的路由装饰器
- ✅ 修复了批量操作的配额泄漏问题
- ✅ 统一了事务管理模式
- ✅ 改进了错误处理逻辑

**配额管理**:
- 单批次：预扣配额，失败时回滚
- 批量：Celery 成功后才消耗配额，失败时不消耗

**错误处理**:
- 单批次：失败立即返回错误
- 批量：部分失败继续处理，返回统计信息

---

**修复完成时间**: 2026-02-10  
**修复人员**: AI Assistant  
**状态**: ✅ 全部完成

# Breakdown API 修复总结

**日期**: 2026-02-10  
**状态**: ✅ 部分完成

---

## 修复的问题

### 核心问题
1. **事务管理不当** - 使用 `async with db.begin()` 导致事务自动提交，后续操作在事务外
2. **配额回滚失败** - Celery 启动失败时，配额无法正确回滚
3. **异常处理混乱** - 异常处理逻辑不清晰，回滚无效

### 修复方案
- 移除 `async with db.begin()`，改用手动事务管理
- Celery 失败时显式调用 `await db.rollback()`
- 成功时调用 `await db.commit()` 和 `await db.refresh()`

---

## 修复状态

### 1. POST /breakdown/start ✅
**状态**: 已修复

**修复内容**:
```python
# 移除 async with db.begin()
# 锁定用户
user_result = await db.execute(
    select(User).where(User.id == current_user.id).with_for_update()
)
locked_user = user_result.scalar_one()

# 检查配额
quota_service = QuotaService(db)
quota = await quota_service.check_episode_quota(locked_user)
if not quota["allowed"]:
    raise HTTPException(...)

# 消耗配额
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
    await db.rollback()  # 回滚配额和任务
    raise HTTPException(...)

# 更新批次状态
batch.breakdown_status = "queued"

# 提交事务
await db.commit()
await db.refresh(task)

return {"task_id": str(task.id), "status": "queued"}
```

### 2. POST /breakdown/start-all ❌
**状态**: 需要修复

**位置**: 第 496 行

**问题**:
```python
async with db.begin():
    # ... 批量创建任务 ...
    for batch in batches:
        # 消耗配额
        # 创建任务
        # 启动 Celery
```

**需要修复为**:
```python
# 锁定用户
user_result = await db.execute(
    select(User).where(User.id == current_user.id).with_for_update()
)
locked_user = user_result.scalar_one()

# 检查配额
quota_service = QuotaService(db)
required_quota = len(batches)
quota = await quota_service.check_episode_quota(locked_user)
if not quota["allowed"]:
    raise HTTPException(...)

task_ids = []
failed_batches = []

for batch in batches:
    try:
        # 消耗配额
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
            # Celery 失败，记录但继续
            failed_batches.append(str(batch.id))
            continue
        
        # 更新批次状态
        batch.breakdown_status = "queued"
        task_ids.append(str(task.id))
    except Exception:
        failed_batches.append(str(batch.id))
        continue

# 提交事务
await db.commit()

if failed_batches:
    return {
        "task_ids": task_ids,
        "total": len(task_ids),
        "failed": len(failed_batches),
        "message": f"成功启动 {len(task_ids)} 个任务，{len(failed_batches)} 个失败"
    }

return {"task_ids": task_ids, "total": len(task_ids)}
```

### 3. POST /breakdown/continue/{project_id} ❌
**状态**: 需要修复

**位置**: 第 656 行

**问题**: 与 `/start` 相同

**修复方案**: 与 `/start` 相同的模式

### 4. POST /breakdown/batch-start ❌
**状态**: 需要修复

**位置**: 第 897 行

**问题**: 与 `/start-all` 相同

**修复方案**: 与 `/start-all` 相同的模式

---

## 修复建议

### 立即修复
1. ✅ `POST /breakdown/start` - 已完成
2. ❌ `POST /breakdown/continue/{project_id}` - 高优先级，单批次操作
3. ❌ `POST /breakdown/batch-start` - 高优先级，批量操作
4. ❌ `POST /breakdown/start-all` - 中优先级，批量操作

### 修复步骤

对于每个接口：

1. **移除 `async with db.begin()`**
2. **移除外层的 try-except**
3. **在 Celery 启动失败时调用 `await db.rollback()`**
4. **在成功时调用 `await db.commit()` 和 `await db.refresh()`**
5. **确保锁在事务开始时获取**

### 测试要点

每个接口都需要测试：

1. **正常流程** - 配额消耗，任务创建，批次状态更新
2. **配额不足** - 返回 403，配额未消耗
3. **Celery 不可用** - 返回 503，配额未消耗，任务未创建
4. **重复提交** - 返回 409，不创建新任务
5. **并发请求** - 只有一个任务被创建

---

## 代码模板

### 单批次操作模板

```python
@router.post("/endpoint")
async def operation(...):
    # 1. 验证数据
    batch = ...
    project = ...
    
    # 2. 检查配置
    if not project.breakdown_model_id:
        raise HTTPException(...)
    
    # 3. 检查重复
    existing_task = ...
    if existing_task:
        raise HTTPException(...)
    
    # 4. 锁定用户
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
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="任务队列服务不可用"
        )
    
    # 9. 更新批次
    batch.breakdown_status = "queued"
    
    # 10. 提交
    await db.commit()
    await db.refresh(task)
    
    return {"task_id": str(task.id), "status": "queued"}
```

### 批量操作模板

```python
@router.post("/endpoint")
async def batch_operation(...):
    # 1. 验证数据
    project = ...
    batches = ...
    
    # 2. 检查配置
    if not project.breakdown_model_id:
        raise HTTPException(...)
    
    # 3. 检查重复
    existing_tasks = ...
    if existing_tasks:
        raise HTTPException(...)
    
    # 4. 锁定用户
    user_result = await db.execute(
        select(User).where(User.id == current_user.id).with_for_update()
    )
    locked_user = user_result.scalar_one()
    
    # 5. 检查配额
    quota_service = QuotaService(db)
    required_quota = len(batches)
    quota = await quota_service.check_episode_quota(locked_user)
    if not quota["allowed"]:
        raise HTTPException(...)
    if quota["remaining"] != -1 and quota["remaining"] < required_quota:
        raise HTTPException(...)
    
    # 6. 批量处理
    task_ids = []
    failed_batches = []
    
    for batch in batches:
        try:
            # 消耗配额
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
                failed_batches.append(str(batch.id))
                continue
            
            # 更新批次
            batch.breakdown_status = "queued"
            task_ids.append(str(task.id))
        except Exception:
            failed_batches.append(str(batch.id))
            continue
    
    # 7. 提交
    await db.commit()
    
    # 8. 返回结果
    if failed_batches:
        return {
            "task_ids": task_ids,
            "total": len(task_ids),
            "failed": len(failed_batches),
            "message": f"成功 {len(task_ids)} 个，失败 {len(failed_batches)} 个"
        }
    
    return {"task_ids": task_ids, "total": len(task_ids)}
```

---

## 相关文档

- [问题分析](./BREAKDOWN_API_ISSUES.md)
- [原始修复文档](./BREAKDOWN_API_FIXES.md)

---

**修复完成时间**: 2026-02-10 (部分)  
**修复人员**: AI Assistant  
**下一步**: 修复剩余 3 个接口

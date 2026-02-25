# 积分系统设计模式

## 核心原则

> **使用预扣模式防止并发超支，任务失败时自动退款**

## Pattern: 积分预扣模式（推荐）

### 问题

用户可能同时启动多个任务，如果只在任务完成后扣费，可能导致积分超支。

### 解决方案

**两阶段积分管理：**
1. **API 层**：检查积分 + 预扣积分
2. **Celery 层**：任务失败时退款

### 完整实现示例

#### 1. API 层（scripts.py）

```python
from app.core.quota import QuotaService

@router.post("/breakdown/{breakdown_id}/scripts/{episode_number}")
async def start_episode_script(
    breakdown_id: str,
    episode_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 步骤1: 检查积分是否足够
    quota_service = QuotaService(db)
    credits_check = await quota_service.check_credits(current_user, "script")
    if not credits_check["allowed"]:
        raise HTTPException(
            status_code=403,
            detail=f"积分不足: 需要 {credits_check['cost']}，余额 {credits_check['balance']}"
        )
    
    # 步骤2: 预扣积分
    consume_result = await quota_service.consume_credits(current_user, "script", "剧本生成")
    if not consume_result:
        raise HTTPException(status_code=403, detail="积分预扣失败，请重试")
    
    # 步骤3: 创建任务并启动 Celery
    task = AITask(
        project_id=breakdown.project_id,
        task_type="episode_script",
        status=TaskStatus.QUEUED,
        config={...}
    )
    db.add(task)
    await db.flush()
    
    celery_task = run_episode_script_task.delay(
        str(task.id), str(breakdown.id), episode_number, 
        str(breakdown.project_id), str(current_user.id)
    )
    task.celery_task_id = celery_task.id
    await db.commit()
    
    return {"task_id": str(task.id), "status": TaskStatus.QUEUED}
```

#### 2. Celery 层（script_tasks.py）

```python
from app.core.quota import refund_episode_quota_sync

@celery_app.task(**CELERY_TASK_CONFIG)
def run_episode_script_task(self, task_id, breakdown_id, episode_number, project_id, user_id):
    db = SyncSessionLocal()
    
    try:
        # 执行任务
        result = _execute_episode_script_sync(
            db, task_id, breakdown_id, episode_number, 
            project_id, model_adapter, task_config, log_publisher
        )
        
        # 任务成功：不处理（积分已预扣）
        update_task_progress_sync(db, task_id, status=TaskStatus.COMPLETED)
        db.commit()
        
        return {"status": TaskStatus.COMPLETED, "task_id": task_id, **result}
    
    except Exception as e:
        # 任务失败：自动退款
        update_task_progress_sync(db, task_id, status=TaskStatus.FAILED)
        
        try:
            refund_episode_quota_sync(db, user_id, 1, auto_commit=False)
            db.commit()
            logger.info(f"任务失败，已退还预扣积分: user_id={user_id}, task_id={task_id}")
        except Exception as refund_error:
            logger.error(f"退还积分失败: {refund_error}")
            db.rollback()
        
        raise
    
    finally:
        db.close()
```

### 优势

| 特性 | 预扣模式 | 后扣模式 |
|------|---------|---------|
| **防止并发超支** | ✅ 是 | ❌ 否 |
| **失败自动退款** | ✅ 是 | ❌ 不需要 |
| **用户体验** | ✅ 立即扣费，失败退款 | ⚠️ 延迟扣费 |
| **实现复杂度** | ⚠️ 需要退款逻辑 | ✅ 简单 |

## Anti-pattern: 后扣模式的问题

### 问题

```python
# ❌ 不推荐：只在任务完成后扣费
@router.post("/scripts/{episode_number}")
async def start_episode_script(...):
    # 只检查，不预扣
    credits_check = await quota_service.check_credits(current_user, "script")
    if not credits_check["allowed"]:
        raise HTTPException(status_code=403, detail="积分不足")
    
    # 创建任务（未扣费）
    task = AITask(...)
    await db.commit()
    
    # Celery 任务完成后才扣费
    return {"task_id": str(task.id)}
```

### 为什么不好

**并发超支场景：**
1. 用户余额 100 积分
2. 同时启动 3 个任务（每个 50 积分）
3. 所有任务都通过检查（因为还未扣费）
4. 3 个任务都启动成功
5. 任务完成后扣费：50 + 50 + 50 = 150 积分
6. **超支 50 积分！**

### 何时可以使用

仅在以下情况下可以使用后扣模式：
- 单用户系统（无并发问题）
- 任务执行时间很短（< 1秒）
- 可以接受超支风险

## Pattern: 批量任务的积分管理

### 问题

批量启动多个任务时，如何正确预扣积分？

### 解决方案

```python
@router.post("/breakdown/{breakdown_id}/scripts/batch")
async def start_batch_scripts(
    breakdown_id: str,
    request: BatchScriptRequest,  # episode_numbers: List[int]
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    quota_service = QuotaService(db)
    
    # 1. 计算总费用
    credits_check = await quota_service.check_credits(current_user, "script")
    required = len(request.episode_numbers)
    required_credits = required * credits_check["cost"]
    
    # 2. 检查余额
    if credits_check["balance"] < required_credits:
        raise HTTPException(
            status_code=403,
            detail=f"积分不足: 需要 {required_credits}，余额 {credits_check['balance']}"
        )
    
    # 3. 预扣所有积分
    for _ in range(required):
        consume_result = await quota_service.consume_credits(
            current_user, "script", "剧本生成"
        )
        if not consume_result:
            raise HTTPException(status_code=403, detail="积分预扣失败")
    
    # 4. 创建所有任务
    task_ids = []
    for ep_num in request.episode_numbers:
        task = AITask(...)
        db.add(task)
        await db.flush()
        
        celery_task = run_episode_script_task.delay(...)
        task.celery_task_id = celery_task.id
        task_ids.append(str(task.id))
    
    await db.commit()
    return {"task_ids": task_ids, "total": len(task_ids)}
```

## Common Mistake: 硬编码定价

### 症状

```python
# ❌ 错误：硬编码定价
required_credits = required * 50  # script 每次 50 积分
```

### 问题

1. 定价变更时需要修改多处代码
2. 与配置系统不一致
3. 难以维护

### 正确做法

```python
# ✅ 正确：使用统一定价
credits_check = await quota_service.check_credits(current_user, "script")
required_credits = required * credits_check["cost"]
```

## Pattern: 积分定价配置

### 环境变量配置

```bash
# .env 文件
CREDITS_BREAKDOWN=100    # 剧情拆解费用
CREDITS_SCRIPT=50        # 剧本生成费用
CREDITS_QA=30            # 质检费用
CREDITS_RETRY=50         # 重试费用

TOKEN_BILLING_ENABLED=false  # 是否启用 Token 计费
TOKEN_CREDITS_INPUT=1        # 输入 Token 费率（每 1K tokens）
TOKEN_CREDITS_OUTPUT=2       # 输出 Token 费率（每 1K tokens）
```

### 代码实现

```python
# app/core/credits.py

def _get_env_int(key: str, default: int) -> int:
    """从环境变量读取整数，失败时返回默认值"""
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        logger.warning(f"环境变量 {key} 无效，使用默认值 {default}")
        return default

# 基础费定价
CREDITS_PRICING = {
    "breakdown": _get_env_int("CREDITS_BREAKDOWN", 100),
    "script": _get_env_int("CREDITS_SCRIPT", 50),
    "qa": _get_env_int("CREDITS_QA", 30),
    "retry": _get_env_int("CREDITS_RETRY", 50),
}

# 统一配置结构
CREDITS_CONFIG = {
    "base": CREDITS_PRICING,
    "token": {
        "enabled": os.getenv("TOKEN_BILLING_ENABLED", "false").lower() == "true",
        "input_per_1k": _get_env_int("TOKEN_CREDITS_INPUT", 1),
        "output_per_1k": _get_env_int("TOKEN_CREDITS_OUTPUT", 2),
    }
}

# 简单的获取函数
async def get_credits_config(db: AsyncSession) -> dict:
    """获取积分配置（不查询数据库）"""
    return CREDITS_CONFIG
```

## Gotcha: 退款函数的事务管理

> **Warning**: 退款函数默认会自动提交事务，可能导致部分提交问题。

### 问题场景

```python
# ❌ 可能导致部分提交
try:
    update_task_status(db, task_id, "failed")
    refund_episode_quota_sync(db, user_id, 1)  # 默认 auto_commit=True
    # 如果这里抛出异常，任务状态已更新但未提交
    do_something_else(db)
    db.commit()
except Exception:
    db.rollback()  # 回滚失败，因为退款已经提交了
```

### 正确做法

```python
# ✅ 使用 auto_commit=False，统一管理事务
try:
    update_task_status(db, task_id, "failed")
    refund_episode_quota_sync(db, user_id, 1, auto_commit=False)
    do_something_else(db)
    db.commit()  # 统一提交
except Exception as e:
    logger.error(f"操作失败: {e}")
    db.rollback()  # 统一回滚
```

## 核心函数参考

### 异步版本（API 层）

```python
from app.core.quota import QuotaService

quota_service = QuotaService(db)

# 检查积分
credits_check = await quota_service.check_credits(user, "script")
# 返回: {allowed: bool, cost: int, balance: int, shortfall: int}

# 消费积分
result = await quota_service.consume_credits(user, "script", "描述")
# 返回: bool（成功/失败）
```

### 同步版本（Celery 层）

```python
from app.core.quota import refund_episode_quota_sync

# 退还积分
refund_episode_quota_sync(db, user_id, 1, auto_commit=False)
# 参数: db, user_id, amount, auto_commit
```

## 测试检查清单

实现积分系统时，确保测试以下场景：

- [ ] 积分不足时拒绝任务
- [ ] 积分足够时成功启动任务
- [ ] 任务成功完成后积分正确扣除
- [ ] 任务失败后积分自动退还
- [ ] 并发启动多个任务不会超支
- [ ] 批量任务的积分正确计算
- [ ] 定价配置可以通过环境变量修改

## 相关规范

- [database-transactions.md](./database-transactions.md) - 事务管理
- [error-handling.md](./error-handling.md) - 错误处理（待创建）

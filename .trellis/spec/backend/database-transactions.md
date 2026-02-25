# 数据库事务管理规范

## 核心原则

> **PostgreSQL 事务一旦失败，必须回滚后才能继续操作**

## Common Mistake: 事务中查询不存在的表

### 症状

```python
sqlalchemy.exc.DBAPIError: <class 'asyncpg.exceptions.InFailedSQLTransactionError'>: 
current transaction is aborted, commands ignored until end of transaction block
```

后续所有数据库操作都会失败，即使是正常的 INSERT/UPDATE 语句。

### 原因

PostgreSQL 的事务机制：
1. 事务中任何 SQL 语句失败
2. 整个事务进入 "aborted" 状态
3. 后续所有 SQL 操作被拒绝
4. 必须 ROLLBACK 或 COMMIT 才能恢复

### 真实案例

```python
# ❌ 错误示例
async def get_credits_config(db: AsyncSession) -> dict:
    try:
        # 查询已删除的表
        result = await db.execute(select(SystemConfig))
        # ...
    except Exception as e:
        logger.warning(f"查询失败: {e}")
        # 虽然捕获了异常，但事务已经 aborted
        return DEFAULT_CONFIG

# 后续在同一事务中的操作会失败
await db.flush()  # ❌ 抛出 InFailedSQLTransactionError
```

### 解决方案

**方案 1: 避免在事务中查询（推荐）**

```python
# ✅ 正确示例：配置使用环境变量
CREDITS_CONFIG = {
    "base": {
        "breakdown": int(os.getenv("CREDITS_BREAKDOWN", "100")),
        "script": int(os.getenv("CREDITS_SCRIPT", "50")),
    }
}

async def get_credits_config(db: AsyncSession) -> dict:
    # 直接返回配置，不查询数据库
    return CREDITS_CONFIG
```

**方案 2: 使用独立会话查询**

```python
# ✅ 如果必须查询，使用独立会话
async def get_credits_config() -> dict:
    async with AsyncSessionLocal() as independent_db:
        try:
            result = await independent_db.execute(select(SystemConfig))
            return parse_config(result)
        except Exception:
            return DEFAULT_CONFIG
```

**方案 3: 捕获异常后回滚（不推荐）**

```python
# ⚠️ 可行但不推荐：会影响调用方的事务
async def get_credits_config(db: AsyncSession) -> dict:
    try:
        result = await db.execute(select(SystemConfig))
        return parse_config(result)
    except Exception as e:
        logger.warning(f"查询失败: {e}")
        await db.rollback()  # 回滚事务
        return DEFAULT_CONFIG
```

## Pattern: 配置管理最佳实践

### 问题

配置数据应该存储在哪里？数据库 vs 环境变量 vs 代码常量？

### 解决方案

根据配置的特性选择存储方式：

| 配置类型 | 存储位置 | 原因 |
|---------|---------|------|
| **静态定价** | 环境变量 + 代码常量 | 很少变化，避免事务问题 |
| **用户数据** | 数据库 | 需要持久化和查询 |
| **运行时状态** | Redis/缓存 | 频繁读写，性能要求高 |
| **敏感信息** | 环境变量 + Secrets | 安全性要求 |

### 示例：积分定价配置

```python
# ✅ 推荐：环境变量 + 代码常量
CREDITS_PRICING = {
    "breakdown": int(os.getenv("CREDITS_BREAKDOWN", "100")),
    "script": int(os.getenv("CREDITS_SCRIPT", "50")),
    "qa": int(os.getenv("CREDITS_QA", "30")),
}

# 统一配置结构
CREDITS_CONFIG = {
    "base": CREDITS_PRICING,
    "token": {
        "enabled": os.getenv("TOKEN_BILLING_ENABLED", "false") == "true",
        "input_per_1k": int(os.getenv("TOKEN_CREDITS_INPUT", "1")),
    }
}

# 简单的获取函数，不查询数据库
async def get_credits_config(db: AsyncSession) -> dict:
    return CREDITS_CONFIG
```

## Gotcha: 数据库迁移删除表后的影响

> **Warning**: 当数据库迁移删除表后，所有查询该表的代码都会导致事务失败。
>
> 必须同步更新代码，移除对已删除表的所有引用。

### 检查清单

删除表后必须检查：

- [ ] 所有 `from app.models.xxx import XXX` 导入
- [ ] 所有 `select(XXX)` 或 `db.query(XXX)` 查询
- [ ] 所有外键关联
- [ ] 所有 Celery 任务中的同步查询

### 搜索命令

```bash
# 查找所有对某个模型的引用
grep -r "SystemConfig" --include="*.py" app/

# 查找所有数据库查询
grep -r "select(SystemConfig)" --include="*.py" app/
grep -r "db.query(SystemConfig)" --include="*.py" app/
```

## 防范措施

### 1. 配置管理策略

- 静态配置优先使用环境变量
- 避免在事务中查询配置表
- 使用缓存减少数据库查询

### 2. 代码审查检查点

- 新增数据库查询时，考虑表是否可能被删除
- 配置查询是否可以改为环境变量
- 是否需要独立会话

### 3. 迁移流程

1. 先更新代码移除对表的引用
2. 部署代码
3. 再执行删除表的迁移

## 相关资源

- [PostgreSQL 事务文档](https://www.postgresql.org/docs/current/tutorial-transactions.html)
- [SQLAlchemy 异步会话](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

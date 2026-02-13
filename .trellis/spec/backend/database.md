# 数据库设计和迁移规范

## 数据库迁移最佳实践

### 破坏性变更的处理

#### 模式：多阶段迁移

**问题**：直接修改字段类型或重命名字段可能导致数据丢失或应用中断。

**解决方案**：使用多阶段迁移策略。

**示例：字段重命名**

```python
# ❌ 错误：直接重命名
def upgrade():
    op.alter_column('users', 'old_name', new_column_name='new_name')
    # 问题：旧代码仍在使用 old_name，会立即报错

# ✅ 正确：多阶段迁移
# 阶段 1：添加新字段并同步数据
def upgrade():
    # 1. 添加新字段
    op.add_column('users', sa.Column('new_name', sa.String(100)))
    
    # 2. 复制数据
    op.execute("UPDATE users SET new_name = old_name")
    
    # 3. 设置非空约束
    op.alter_column('users', 'new_name', nullable=False)

# 阶段 2：更新应用代码使用新字段

# 阶段 3：删除旧字段（在新代码部署后）
def upgrade():
    op.drop_column('users', 'old_name')
```

**为什么这样做？**
- 允许零停机部署
- 旧代码和新代码可以共存
- 可以安全回滚

---

### 字段类型变更

#### 模式：先扩展，后收缩

**问题**：直接修改字段类型可能导致数据丢失。

**错误示例**：

```python
# ❌ 危险：从 TEXT 改为 VARCHAR(50)
def upgrade():
    op.alter_column('credentials', 'api_key',
                    type_=sa.String(50))
    # 如果现有数据超过 50 字符，会被截断！
```

**正确做法**：

```python
# ✅ 方案 1：先验证数据
def upgrade():
    # 1. 检查是否有超长数据
    connection = op.get_bind()
    result = connection.execute(
        "SELECT COUNT(*) FROM credentials WHERE LENGTH(api_key) > 50"
    )
    count = result.scalar()
    
    if count > 0:
        raise Exception(f"发现 {count} 条数据超过 50 字符，无法迁移")
    
    # 2. 安全地修改类型
    op.alter_column('credentials', 'api_key', type_=sa.String(50))

# ✅ 方案 2：添加新字段
def upgrade():
    # 1. 添加新字段
    op.add_column('credentials', sa.Column('api_key_new', sa.String(50)))
    
    # 2. 迁移数据（截断或转换）
    op.execute("""
        UPDATE credentials 
        SET api_key_new = SUBSTRING(api_key, 1, 50)
    """)
    
    # 3. 删除旧字段，重命名新字段
    op.drop_column('credentials', 'api_key')
    op.alter_column('credentials', 'api_key_new', new_column_name='api_key')
```

---

### 加密字段迁移

#### 常见错误：忘记解密数据

**场景**：从加密存储迁移到明文存储。

**错误示例**：

```python
# ❌ 错误：直接重命名，数据仍是加密的
def upgrade():
    op.alter_column('credentials', 'api_key_encrypted',
                    new_column_name='api_key')
    # 问题：api_key 列中存储的是加密数据，但代码期望明文！
```

**正确做法**：

```python
# ✅ 方案 1：在迁移中解密
def upgrade():
    from app.core.encryption import EncryptionService
    
    # 1. 添加新列
    op.add_column('credentials', sa.Column('api_key', sa.Text()))
    
    # 2. 解密并复制数据
    connection = op.get_bind()
    encryption = EncryptionService()
    
    credentials = connection.execute(
        "SELECT id, api_key_encrypted FROM credentials"
    )
    
    for cred in credentials:
        try:
            decrypted = encryption.decrypt(cred.api_key_encrypted)
            connection.execute(
                "UPDATE credentials SET api_key = %s WHERE id = %s",
                (decrypted, cred.id)
            )
        except Exception as e:
            print(f"警告：凭证 {cred.id} 解密失败: {e}")
    
    # 3. 删除旧列
    op.drop_column('credentials', 'api_key_encrypted')

# ✅ 方案 2：要求重新创建（适用于测试环境）
def upgrade():
    """
    ⚠️ 警告：此迁移会导致现有凭证无法使用！
    
    现有的加密凭证将无法解密，需要重新创建。
    仅适用于测试环境或可以接受数据丢失的情况。
    """
    op.alter_column('credentials', 'api_key_encrypted',
                    new_column_name='api_key')
```

**预防措施**：
1. 在迁移文件顶部添加清晰的警告注释
2. 在文档中说明破坏性变更
3. 提供数据导出脚本
4. 在测试环境先验证

---

### 迁移文件命名

#### 约定：描述性的迁移文件名

**格式**：`{revision}_{description}.py`

**好的命名**：
- ✅ `ecc01e4b_remove_encryption_from_credentials.py`
- ✅ `a1b2c3d4_add_user_email_verification.py`
- ✅ `f5e6d7c8_migrate_old_pricing_to_new_format.py`

**不好的命名**：
- ❌ `ecc01e4b_update.py`（太模糊）
- ❌ `a1b2c3d4_fix.py`（没有说明修复了什么）
- ❌ `f5e6d7c8_changes.py`（太通用）

**为什么重要？**
- 快速了解迁移内容
- 便于回滚时识别
- 团队协作时清晰

---

### 迁移文件注释

#### 模式：完整的迁移文档

**必须包含的信息**：

```python
"""简短的标题

Revision ID: ecc01e4bf4bc
Revises: eece6c8e3bad
Create Date: 2026-02-08 16:00:00.000000

变更说明：
- 将 api_key_encrypted 重命名为 api_key
- 将 api_secret_encrypted 重命名为 api_secret

⚠️ 警告：
此迁移会导致现有加密凭证无法使用！
如果数据库中已有加密的凭证，需要先解密后再运行此迁移。

影响范围：
- ai_model_credentials 表
- 所有现有凭证需要重新创建

回滚说明：
运行 downgrade 会将字段名改回，但不会恢复加密数据。
"""
```

---

### 数据迁移脚本

#### 模式：独立的数据迁移脚本

**何时使用**：
- 大量数据需要转换
- 迁移逻辑复杂
- 需要人工审核

**示例**：

```python
# scripts/migrate_encrypted_credentials.py
"""
导出加密凭证的脚本

使用方法：
1. 运行此脚本导出数据：
   python scripts/migrate_encrypted_credentials.py > credentials_backup.csv

2. 运行数据库迁移：
   alembic upgrade head

3. 使用导出的数据重新创建凭证
"""
import asyncio
from app.core.database import get_db
from app.core.encryption import EncryptionService
from app.models.ai_model_credential import AIModelCredential
from sqlalchemy import select

async def export_credentials():
    encryption = EncryptionService()
    
    async for db in get_db():
        result = await db.execute(select(AIModelCredential))
        credentials = result.scalars().all()
        
        print("id,provider_id,credential_name,api_key,api_secret")
        
        for cred in credentials:
            try:
                decrypted_key = encryption.decrypt(cred.api_key_encrypted)
                decrypted_secret = ""
                if cred.api_secret_encrypted:
                    decrypted_secret = encryption.decrypt(cred.api_secret_encrypted)
                
                print(f"{cred.id},{cred.provider_id},{cred.credential_name},"
                      f"{decrypted_key},{decrypted_secret}")
            except Exception as e:
                print(f"# 错误：凭证 {cred.id} 解密失败: {e}", file=sys.stderr)
        
        break

if __name__ == "__main__":
    asyncio.run(export_credentials())
```

---

## 数据库设计原则

### 敏感字段命名

**约定**：敏感字段应该有明确的后缀。

**推荐的命名**：
- `api_key` - 明文存储
- `api_key_encrypted` - 加密存储
- `api_key_hash` - 哈希存储（不可逆）

**为什么重要？**
- 一眼就能看出字段的存储方式
- 避免混淆（明文 vs 加密）
- 便于代码审查

---

### 索引策略

**原则**：为常用查询字段添加索引。

**示例**：

```python
class AIModelCredential(Base):
    __tablename__ = "ai_model_credentials"
    
    id = Column(UUID, primary_key=True)
    provider_id = Column(UUID, ForeignKey(...), index=True)  # ✅ 常用于筛选
    is_active = Column(Boolean, default=True, index=True)    # ✅ 常用于筛选
    credential_name = Column(String(100))                    # ❌ 不常用于查询
```

**何时添加索引**：
- ✅ 外键字段
- ✅ 常用于 WHERE 条件的字段
- ✅ 常用于 ORDER BY 的字段
- ✅ 布尔标志字段（如 is_active）

**何时不添加索引**：
- ❌ 很少查询的字段
- ❌ 高基数字段（如 UUID 主键已有索引）
- ❌ 频繁更新的字段

---

## 迁移检查清单

部署前检查：

- [ ] 迁移文件有清晰的注释
- [ ] 测试了 upgrade 和 downgrade
- [ ] 在测试环境验证过
- [ ] 如果是破坏性变更，有数据备份方案
- [ ] 如果涉及敏感数据，有导出脚本
- [ ] 团队成员已审查

---

## 业务配置系统设计

### 配置读取性能优化

**问题**：每次请求都查询数据库获取配置，在高并发场景下会产生大量重复查询。

**解决方案**：使用内存缓存 + TTL 机制。

```python
import time
from typing import Optional

_config_cache: Optional[dict] = None
_config_cache_ts: float = 0
_CONFIG_CACHE_TTL = 60  # 秒

async def get_credits_config(db: AsyncSession) -> dict:
    global _config_cache, _config_cache_ts

    now = time.monotonic()
    if _config_cache is not None and (now - _config_cache_ts) < _CONFIG_CACHE_TTL:
        return _config_cache

    # 从数据库读取...
    _config_cache = parsed
    _config_cache_ts = now
    return parsed
```

**关键点**：
- 设置合理的 TTL（如 60 秒）
- 异常时回退到默认值
- 管理员修改配置后可通过重启服务或手动清空缓存生效

---

### 同步函数的数据库操作

**问题**：Celery worker 使用同步数据库会话，如果在函数内部自行 commit，可能导致事务边界混乱。

**解决方案**：同步函数不自行 commit，由调用方统一管理事务。

```python
# ❌ 错误：函数内部 commit
def consume_credits_sync(db, user_id, amount):
    user.credits -= amount
    db.add(record)
    db.commit()  # 事务边界不确定
    return result

# ✅ 正确：调用方管理事务
def consume_credits_sync(db, user_id, amount):
    user.credits -= amount
    db.add(record)
    return {"success": True}  # 不 commit

# 调用方
def run_task():
    consume_credits_sync(db, user_id, 100)
    db.commit()  # 统一在任务完成时 commit
```

---

### 配置读取的异常处理

**问题**：如果数据库表不存在（如迁移未执行），代码会直接抛异常导致任务失败。

**解决方案**：添加异常兜底逻辑，失败时回退到代码默认值。

```python
try:
    result = db.query(SystemConfig).all()
    configs = {c.key: c.value for c in result}
    parsed = _parse_config(configs)
except Exception as e:
    logger.warning(f"读取系统配置失败，使用默认值: {e}")
    return _DEFAULT_CONFIG  # 回退到默认值
```

---

### 积分扣费失败的处理

**问题**：任务完成后扣费失败但任务仍返回成功，导致用户免费使用服务。

**解决方案**：使用 logger.error 记录详细信息，便于排查和追缴。

```python
credits_result = consume_credits_for_task_sync(db, user_id, "breakdown", task_id)
if not credits_result["success"]:
    logger.error(
        f"积分扣费失败: user={user_id}, task={task_id}, "
        f"reason={credits_result['message']}"
    )
```

**注意**：
- 使用 `logger.error` 而非 `print`
- 记录关键上下文（user_id, task_id, 失败原因）
- 考虑是否需要记录到"欠费"表以便后续追缴

---

### 积分扣费重复问题

**问题**：用户积分被重复扣除两次（如 "剧情拆解（基础费）100" 出现两次）

**原因**：API 层预扣积分后，Celery 任务完成时又执行了一次扣费

**症状**：账单记录中出现两条相同描述的扣费记录

**修复**：
1. 选择一个扣费时机（推荐 API 层预扣）
2. 删除 Celery 任务中的重复扣费代码
3. 确保失败时能正确返还积分

```python
# ✅ API 层预扣（推荐）
async def start_breakdown(...):
    # 任务开始前预扣
    await quota_service.consume_credits(user, "breakdown", "剧情拆解")
    # 提交 Celery 任务...

# ✅ Celery 任务不再重复扣费
def run_breakdown_task(...):
    # ... 执行任务 ...
    # 注意：不再调用 consume_credits_for_task_sync
    # 如果任务失败，需要手动调用 refund_episode_quota_sync 返还积分
    if failed:
        refund_episode_quota_sync(db, user_id, 1)
```

**预防**：
- 明确扣费时机（在哪个环节扣）
- 在代码注释中说明"已在 XX 环节扣费"
- 单元测试验证扣费次数

---

### 前端数据的准确性

**问题**：在前端用有限的分页数据做聚合计算（如本月消耗），结果不准确。

**解决方案**：后端直接返回聚合结果。

```typescript
// ❌ 前端计算（不准确，只算当前页）
const monthlyConsumed = records.reduce((sum, r) => sum + r.credits, 0)

// ✅ 后端返回（精确）
const info = await billingApi.getCreditsInfo();
const monthlyConsumed = info.data.monthly_consumed;
```

---

### 字段命名不一致问题

**问题**：后端 User 模型有 `credits`（积分）和 `balance`（旧余额）两个字段，前端使用 `balance` 显示积分，导致数据不一致

**原因**：
- 后端 `credits` 字段存储积分
- `/auth/me` 端点直接返回 ORM 对象，Pydantic 使用 `balance` 字段（Pydantic v2 的 `from_attributes` 会自动映射）
- 但 User 模型中 `balance` 是 DECIMAL(10,2) 类型，值可能为 0
- 前端显示 `user.balance`（0），但 BillingModal 调用 `/billing/credits` API 返回 `credits` 字段（实际积分）

**症状**：前端显示的积分与账单详情中的余额不一致

**修复**：修改 `/auth/me` 端点，手动映射字段

```python
# ✅ 正确：手动构建响应，映射字段
@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        balance=current_user.credits,  # 使用 credits 作为积分余额
        ...
    )
```

**预防**：
- 明确字段语义：只用 `credits` 存储积分
- API 响应模型与数据库模型分离
- 前端类型定义与后端响应对齐

---

**最后更新**: 2026-02-13
**相关变更**: 积分显示不一致问题修复

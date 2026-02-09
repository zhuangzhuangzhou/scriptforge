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

**最后更新**: 2026-02-08
**相关变更**: 模型管理系统 v1.1.0 - 加密字段迁移

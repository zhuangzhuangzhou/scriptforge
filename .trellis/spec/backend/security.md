# 后端安全规范

## 敏感数据存储

### 应用层加密 vs 数据库级加密

#### 决策：优先使用数据库级加密

**背景**：
在模型管理系统 v1.0.0 中，我们最初使用应用层 AES-256-GCM 加密来保护 API Key。在 v1.1.0 中移除了这个功能。

**为什么移除应用层加密？**

1. **密钥管理复杂性**
   - 需要安全存储 `ENCRYPTION_KEY` 环境变量
   - 密钥丢失 = 所有数据永久丢失
   - 密钥轮换困难

2. **部署复杂度**
   - 每个环境都需要配置加密密钥
   - 开发/测试/生产环境的密钥管理
   - 容器化部署时的密钥注入

3. **有更好的替代方案**
   - PostgreSQL TDE（Transparent Data Encryption）
   - 文件系统级加密（LUKS, FileVault, BitLocker）
   - 云服务商的加密服务（AWS KMS, Azure Key Vault）

**何时使用应用层加密？**

仅在以下情况下考虑应用层加密：
- ✅ 需要字段级加密（不同字段用不同密钥）
- ✅ 需要跨数据库的加密一致性
- ✅ 数据库不支持 TDE
- ✅ 有专业的密钥管理系统（如 HashiCorp Vault）

**何时使用数据库级加密？**（推荐）

大多数情况下应该使用数据库级加密：
- ✅ 简化应用代码
- ✅ 密钥管理由数据库负责
- ✅ 性能更好（数据库优化）
- ✅ 备份自动加密

#### 实现示例

**不推荐：应用层加密**

```python
# ❌ 复杂且容易出错
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

class EncryptionService:
    def __init__(self):
        key = os.getenv('ENCRYPTION_KEY')  # 密钥管理问题
        if not key:
            raise ValueError("ENCRYPTION_KEY not set")
        self.key = base64.b64decode(key)
        self.aesgcm = AESGCM(self.key)

    def encrypt(self, plaintext: str) -> str:
        iv = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(iv, plaintext.encode(), None)
        return base64.b64encode(iv + ciphertext).decode()

# 使用时
credential.api_key_encrypted = encryption_service.encrypt(api_key)
```

**推荐：数据库级加密**

```sql
-- ✅ 简单且可靠
-- PostgreSQL TDE
ALTER DATABASE your_db SET default_tablespace = encrypted_tablespace;

-- 或使用 pgcrypto 扩展（字段级加密）
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE credentials (
    id UUID PRIMARY KEY,
    api_key TEXT  -- 自动加密
);
```

**如果必须明文存储**

```python
# ✅ 明文存储 + 严格的访问控制
class AIModelCredential(Base):
    api_key = Column(Text, nullable=False)  # 明文存储
    
# 配合以下安全措施：
# 1. 数据库访问控制（防火墙 + 白名单）
# 2. 强密码策略
# 3. SSL/TLS 连接
# 4. 审计日志
# 5. 定期安全审计
```

---

## API Key 脱敏显示

### 模式：始终脱敏显示敏感数据

**问题**：API Key 等敏感数据不应该在日志、UI、API 响应中完整显示。

**解决方案**：使用脱敏函数。

**示例**：

```python
# ✅ 好的做法
def mask_api_key(api_key: str) -> str:
    """脱敏 API Key"""
    if len(api_key) <= 10:
        return "***"
    
    prefix = api_key[:3]   # 保留前缀（如 "sk-"）
    suffix = api_key[-3:]  # 保留后缀
    return f"{prefix}***...***{suffix}"

# 使用
masked_key = mask_api_key("sk-1234567890abcdefghijklmnopqrstuvwxyz")
# 输出: "sk-***...***xyz"
```

**应用场景**：
- ✅ API 响应中的凭证列表
- ✅ 管理界面显示
- ✅ 日志记录
- ✅ 错误消息

**不要脱敏的场景**：
- ❌ 实际调用第三方 API 时（需要完整的 Key）
- ❌ 用户首次创建凭证时的确认（可以显示一次）

---

## 数据库迁移中的敏感数据

### 常见错误：破坏性迁移导致数据丢失

**症状**：运行迁移后，现有的加密数据无法解密。

**原因**：直接重命名加密字段为明文字段，但数据仍是加密的。

**错误示例**：

```python
# ❌ 错误：直接重命名，数据仍是加密的
def upgrade():
    op.alter_column('credentials', 'api_key_encrypted',
                    new_column_name='api_key')
    # 现在 api_key 列中存储的是加密数据，但代码期望明文！
```

**正确做法**：

```python
# ✅ 方案 1：先解密再迁移
def upgrade():
    # 1. 添加新列
    op.add_column('credentials', sa.Column('api_key', sa.Text()))
    
    # 2. 解密并复制数据
    connection = op.get_bind()
    credentials = connection.execute(
        "SELECT id, api_key_encrypted FROM credentials"
    )
    for cred in credentials:
        decrypted = decrypt(cred.api_key_encrypted)
        connection.execute(
            "UPDATE credentials SET api_key = %s WHERE id = %s",
            (decrypted, cred.id)
        )
    
    # 3. 删除旧列
    op.drop_column('credentials', 'api_key_encrypted')

# ✅ 方案 2：要求重新创建（适用于测试环境）
def upgrade():
    # 警告：此迁移会导致现有凭证无法使用
    op.alter_column('credentials', 'api_key_encrypted',
                    new_column_name='api_key')
    # 在文档中明确说明需要重新创建凭证
```

**预防措施**：
1. 在迁移文件中添加清晰的注释
2. 在文档中说明破坏性变更
3. 提供数据导出脚本
4. 在测试环境先验证

---

## 安全检查清单

### 敏感数据存储

- [ ] 使用数据库级加密（PostgreSQL TDE）
- [ ] 或使用文件系统加密
- [ ] 如果使用应用层加密，有专业的密钥管理系统
- [ ] 敏感数据在 UI/API/日志中脱敏显示

### 数据库安全

- [ ] 数据库访问控制（防火墙 + 白名单）
- [ ] 使用强密码
- [ ] 启用 SSL/TLS 连接
- [ ] 定期备份并加密备份文件
- [ ] 审计日志记录所有敏感操作

### API 安全

- [ ] 所有敏感端点需要认证
- [ ] 使用 HTTPS（生产环境强制）
- [ ] 输入验证（Pydantic）
- [ ] 权限控制（管理员/用户）

---

## 参考资料

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [PostgreSQL Encryption Options](https://www.postgresql.org/docs/current/encryption-options.html)
- [NIST Cryptographic Standards](https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines)

---

**最后更新**: 2026-02-08
**相关变更**: 模型管理系统 v1.1.0 - 移除应用层加密

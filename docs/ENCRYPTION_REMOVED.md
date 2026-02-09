# ⚠️ 加密功能已移除

## 变更说明

从 v1.1.0 版本开始，模型管理系统已移除 ENCRYPTION_KEY 加密功能。

### 变更内容

**之前（v1.0.0）：**
- API Key 使用 AES-256-GCM 加密存储
- 需要设置 ENCRYPTION_KEY 环境变量
- 数据库字段：`api_key_encrypted`, `api_secret_encrypted`

**现在（v1.1.0+）：**
- API Key 以明文形式存储
- 不再需要 ENCRYPTION_KEY 环境变量
- 数据库字段：`api_key`, `api_secret`
- 仍然保留脱敏显示功能（sk-***...***abc）

### 数据库迁移

如果您从 v1.0.0 升级，需要运行迁移：

```bash
cd backend
alembic upgrade head
```

⚠️ **警告**：如果数据库中已有加密的凭证，迁移后这些数据将无法使用，需要重新创建凭证。

### 安全建议

由于 API Key 现在以明文存储，请务必：

1. **数据库访问控制**
   - 限制数据库访问权限
   - 使用强密码
   - 启用 SSL/TLS 连接

2. **网络安全**
   - 使用防火墙保护数据库
   - 不要将数据库暴露到公网
   - 使用 VPN 或专用网络

3. **备份安全**
   - 加密数据库备份文件
   - 安全存储备份
   - 定期测试恢复流程

4. **数据库级加密**（推荐）
   - PostgreSQL: 使用 Transparent Data Encryption (TDE)
   - 或使用加密的文件系统

5. **审计日志**
   - 记录所有凭证访问
   - 定期审查日志
   - 设置异常告警

### 为什么移除加密？

根据用户反馈，移除加密功能的原因：
- 简化部署流程（不需要管理 ENCRYPTION_KEY）
- 避免密钥丢失导致数据无法恢复
- 数据库级加密更安全且更易管理

### 如果需要加密怎么办？

建议使用以下方案：

1. **数据库级加密**（推荐）
   ```sql
   -- PostgreSQL TDE
   ALTER DATABASE your_db SET default_tablespace = encrypted_tablespace;
   ```

2. **文件系统加密**
   - Linux: LUKS
   - macOS: FileVault
   - Windows: BitLocker

3. **应用层加密**
   - 如果确实需要应用层加密，可以参考 v1.0.0 的实现
   - 或联系技术支持获取定制方案

---

**版本**: v1.1.0
**日期**: 2026-02-08

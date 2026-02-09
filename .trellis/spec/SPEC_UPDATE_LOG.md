# 规范更新日志

记录所有规范文档的更新历史。

## 2026-02-08 - 移除加密功能的经验总结

### 更新的规范

1. **`backend/security.md`** - 新增
   - 应用层加密 vs 数据库级加密的决策指南
   - API Key 脱敏显示模式
   - 数据库迁移中的敏感数据处理
   - 安全检查清单

2. **`backend/database.md`** - 新增
   - 破坏性变更的多阶段迁移策略
   - 字段类型变更的安全做法
   - 加密字段迁移的常见错误和正确做法
   - 迁移文件命名和注释规范
   - 数据迁移脚本模式

### 学到的关键知识

#### 1. 应用层加密的权衡

**问题**：
- 密钥管理复杂（ENCRYPTION_KEY 环境变量）
- 密钥丢失导致数据永久丢失
- 部署复杂度增加

**解决方案**：
- 优先使用数据库级加密（PostgreSQL TDE）
- 或使用文件系统加密
- 仅在特殊场景下使用应用层加密

**影响**：
- 简化了部署流程
- 降低了密钥管理风险
- 但需要更严格的数据库安全措施

#### 2. 破坏性迁移的处理

**问题**：
直接重命名加密字段为明文字段，导致数据无法使用。

**错误做法**：
```python
# ❌ 直接重命名
op.alter_column('credentials', 'api_key_encrypted',
                new_column_name='api_key')
```

**正确做法**：
```python
# ✅ 方案 1：先解密再迁移
# 1. 添加新列
# 2. 解密并复制数据
# 3. 删除旧列

# ✅ 方案 2：要求重新创建（测试环境）
# 在文档中明确说明破坏性变更
```

**预防措施**：
- 在迁移文件中添加清晰的警告注释
- 提供数据导出脚本
- 在测试环境先验证

#### 3. API Key 脱敏显示

**模式**：
```python
def mask_api_key(api_key: str) -> str:
    if len(api_key) <= 10:
        return "***"
    prefix = api_key[:3]
    suffix = api_key[-3:]
    return f"{prefix}***...***{suffix}"
```

**应用场景**：
- API 响应
- 管理界面
- 日志记录
- 错误消息

**不脱敏的场景**：
- 实际调用第三方 API
- 用户首次创建凭证的确认

### 相关文件

**代码变更**：
- `backend/app/models/ai_model_credential.py`
- `backend/app/ai/adapters/model_config_service.py`
- `backend/app/api/v1/admin/credentials.py`
- `backend/alembic/versions/ecc01e4bf4bc_*.py`

**文档**：
- `docs/ENCRYPTION_REMOVED.md`
- `docs/ENCRYPTION_REMOVAL_SUMMARY.md`
- `CHANGELOG_ENCRYPTION_REMOVAL.md`

### 适用场景

这些规范适用于：
- 需要存储敏感数据（API Key、密码等）
- 需要进行破坏性数据库迁移
- 需要在加密和明文存储之间做决策

### 未来改进

可能的改进方向：
- 添加数据库级加密的具体实施指南
- 添加更多迁移模式（如数据类型转换）
- 添加安全审计的自动化工具

---

**更新人**: AI Assistant
**审查状态**: 待审查
**相关任务**: 模型管理系统 v1.1.0 - 移除加密功能

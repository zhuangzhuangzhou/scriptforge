# 模型管理功能 - 性能优化建议

## 1. 数据库索引优化

### 已创建的索引
在数据库迁移中，我们已经创建了以下索引：

**ai_model_providers 表：**
- `idx_providers_key` - provider_key
- `idx_providers_enabled` - is_enabled

**ai_models 表：**
- `idx_models_provider` - provider_id
- `idx_models_enabled` - is_enabled
- `idx_models_default` - is_default

**ai_model_credentials 表：**
- `idx_credentials_provider` - provider_id
- `idx_credentials_active` - is_active

**ai_model_pricing 表：**
- `idx_pricing_model` - model_id
- `idx_pricing_active` - is_active

### 建议添加的复合索引

```sql
-- 1. 模型查询优化（按提供商和状态查询）
CREATE INDEX idx_models_provider_enabled
ON ai_models(provider_id, is_enabled);

-- 2. 凭证查询优化（按提供商和状态查询）
CREATE INDEX idx_credentials_provider_active
ON ai_model_credentials(provider_id, is_active);

-- 3. 计费规则查询优化（按模型和生效时间查询）
CREATE INDEX idx_pricing_model_time
ON ai_model_pricing(model_id, is_active, effective_from, effective_until);
```

## 2. 查询优化建议

### ModelConfigService.get_model_config()

**当前查询：**
- 3个独立查询：模型 → 凭证 → 提供商信息

**优化建议：**
- 使用 JOIN 一次性获取所有数据
- 减少数据库往返次数

**优化后的查询示例：**
```python
result = await self.db.execute(
    select(AIModel, AIModelCredential, AIModelProvider)
    .join(AIModelProvider)
    .join(AIModelCredential, AIModelCredential.provider_id == AIModel.provider_id)
    .where(AIModel.id == model_id)
    .where(AIModel.is_enabled == True)
    .where(AIModelCredential.is_active == True)
)
```

## 3. 缓存策略

### 推荐使用 Redis 缓存

**缓存内容：**
1. 模型配置（5分钟过期）
2. 计费规则（10分钟过期）
3. 系统配置（15分钟过期）

**缓存键设计：**
```
model_config:{model_id}
pricing_rule:{model_id}
system_config:{config_key}
```

**缓存刷新策略：**
- 配置更新时主动刷新缓存
- 使用 Redis EXPIRE 自动过期

### 实现示例

```python
import redis
import json

class CachedModelConfigService(ModelConfigService):
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        super().__init__(db)
        self.redis = redis_client

    async def get_model_config(self, model_id: str):
        # 尝试从缓存获取
        cache_key = f"model_config:{model_id}"
        cached = self.redis.get(cache_key)

        if cached:
            return json.loads(cached)

        # 从数据库获取
        config = await super().get_model_config(model_id)

        if config:
            # 写入缓存（5分钟过期）
            self.redis.setex(
                cache_key,
                300,
                json.dumps(config)
            )

        return config
```

## 4. API 响应优化

### 分页优化
所有列表 API 已实现分页，建议：
- 默认页大小：20
- 最大页大小：100
- 使用游标分页代替偏移分页（大数据量时）

### 响应字段优化
- 列表 API 只返回必要字段
- 详情 API 返回完整信息
- 使用 Pydantic 的 `exclude_unset=True` 减少响应大小

## 5. 连接池优化

### 当前配置
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)
```

### 生产环境建议
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,          # 增加连接池大小
    max_overflow=40,       # 增加溢出连接数
    pool_pre_ping=True,    # 保持连接检查
    pool_recycle=3600,     # 1小时回收连接
    echo=False,            # 生产环境关闭 SQL 日志
)
```

## 6. 批量操作优化

### 批量插入优化
使用 SQLAlchemy 的 `bulk_insert_mappings` 代替逐条插入：

```python
# 不推荐
for item in items:
    db.add(Model(**item))
await db.commit()

# 推荐
await db.execute(
    insert(Model),
    items
)
await db.commit()
```

## 7. 监控指标

### 建议监控的指标
1. **API 响应时间**
   - 目标：P95 < 500ms
   - 目标：P99 < 1000ms

2. **数据库查询时间**
   - 慢查询阈值：> 100ms
   - 记录并优化慢查询

3. **缓存命中率**
   - 目标：> 80%

4. **错误率**
   - 目标：< 0.1%

## 8. 性能测试建议

### 压力测试场景
1. 并发获取模型配置（100 QPS）
2. 并发创建/更新配置（10 QPS）
3. 大量计费规则查询（50 QPS）

### 测试工具
- Apache Bench (ab)
- Locust
- k6

### 测试命令示例
```bash
# 测试获取模型列表 API
ab -n 1000 -c 10 -H "Authorization: Bearer <token>" \
   http://localhost:8000/api/v1/admin/models/models
```

## 9. 代码优化建议

### 使用异步上下文管理器
```python
# 推荐
async with AsyncSessionLocal() as db:
    # 操作
    await db.commit()

# 不推荐
db = AsyncSessionLocal()
try:
    # 操作
    await db.commit()
finally:
    await db.close()
```

### 避免 N+1 查询
使用 `selectinload` 或 `joinedload` 预加载关联数据：

```python
result = await db.execute(
    select(AIModel)
    .options(selectinload(AIModel.provider))
    .options(selectinload(AIModel.pricing_rules))
)
```

## 10. 部署优化

### 环境变量配置
```bash
# 必须设置
ENCRYPTION_KEY=<32字节的base64编码密钥>

# 推荐设置
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
REDIS_URL=redis://localhost:6379/0
```

### 生成加密密钥
```python
import os
import base64

# 生成32字节随机密钥
key = os.urandom(32)
print(base64.b64encode(key).decode())
```

---

## 总结

优先级排序：
1. **高优先级**：设置 ENCRYPTION_KEY 环境变量
2. **高优先级**：添加复合索引
3. **中优先级**：实现 Redis 缓存
4. **中优先级**：优化数据库查询（使用 JOIN）
5. **低优先级**：性能测试和监控

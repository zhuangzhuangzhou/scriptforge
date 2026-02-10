# model_config_id 字段实现

## 修改内容

### 1. ✅ 将 model_config_id 改为必填字段

**文件**: `backend/app/api/v1/breakdown.py`

```python
class BreakdownStartRequest(BaseModel):
    batch_id: str
    model_config_id: str  # 必填：AI 模型配置 ID（之前是 Optional）
    selected_skills: Optional[List[str]] = None
    # ...
```

**影响**:
- ❌ **破坏性变更**: 前端必须传递这个参数
- ✅ 确保每个任务都有明确的模型配置

### 2. ✅ 创建同步版本的 get_adapter_sync

**文件**: `backend/app/ai/adapters/__init__.py`

```python
def get_adapter_sync(
    db: Session,
    model_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> BaseModelAdapter:
    """获取模型适配器实例（同步版本，用于 Celery）"""
    
    # 1. 查询模型
    model = db.query(AIModel).filter(
        AIModel.id == model_id,
        AIModel.is_enabled == True
    ).first()
    
    # 2. 查询提供商
    provider = db.query(AIModelProvider).filter(
        AIModelProvider.id == model.provider_id,
        AIModelProvider.is_enabled == True
    ).first()
    
    # 3. 查询凭证
    credential = db.query(AIModelCredential).filter(
        AIModelCredential.provider_id == provider.id,
        AIModelCredential.is_active == True
    ).first()
    
    # 4. 根据提供商类型创建适配器
    if provider_type == "anthropic":
        return AnthropicAdapter(...)
    elif provider_type == "openai":
        return OpenAIAdapter(...)
    # ...
```

**支持的提供商**:
- ✅ OpenAI
- ✅ Anthropic
- ✅ Azure OpenAI
- ✅ Google Gemini

### 3. ✅ 在 Celery 任务中使用模型配置

**文件**: `backend/app/tasks/breakdown_tasks.py`

```python
# 读取任务配置
task_config = task_record.config if task_record else {}

# 获取模型配置 ID（必需）
model_id = task_config.get("model_config_id")
if not model_id:
    raise ValueError("任务配置中缺少 model_config_id")

# 获取模型适配器
from app.ai.adapters import get_adapter_sync
try:
    model_adapter = get_adapter_sync(
        db=db,
        model_id=model_id,
        user_id=user_id
    )
except ValueError as e:
    raise AITaskException(
        code="MODEL_ERROR",
        message=f"模型配置错误: {str(e)}"
    )

# 使用 model_adapter 进行 AI 调用
# ...
```

## 前端需要的修改

### 1. 获取可用模型列表

**新增 API 调用**:
```typescript
// 获取所有可用的模型
const models = await api.get('/api/v1/admin/models', {
  params: {
    is_enabled: true
  }
});

// 或者获取默认模型
const defaultModel = models.find(m => m.is_default);
```

### 2. 在拆解配置中添加模型选择

**UI 组件**:
```tsx
<Form.Item label="AI 模型" name="model_config_id" rules={[{ required: true }]}>
  <Select placeholder="选择 AI 模型">
    {models.map(model => (
      <Option key={model.id} value={model.id}>
        {model.display_name}
        {model.is_default && <Tag color="blue">默认</Tag>}
      </Option>
    ))}
  </Select>
</Form.Item>
```

### 3. 提交请求时包含 model_config_id

**修改前**:
```typescript
const data = {
  batch_id: "xxx",
  selected_skills: [],
  adapt_method_key: "adapt_method_default",
  quality_rule_key: "qa_breakdown_default",
  output_style_key: "output_style_default"
  // 缺少 model_config_id
};
```

**修改后**:
```typescript
const data = {
  batch_id: "xxx",
  model_config_id: selectedModelId,  // 必须添加
  selected_skills: [],
  adapt_method_key: "adapt_method_default",
  quality_rule_key: "qa_breakdown_default",
  output_style_key: "output_style_default"
};
```

### 4. 设置默认值

**建议**:
```typescript
const [modelConfigId, setModelConfigId] = useState<string>();

useEffect(() => {
  // 加载模型列表
  loadModels().then(models => {
    // 使用默认模型
    const defaultModel = models.find(m => m.is_default);
    if (defaultModel) {
      setModelConfigId(defaultModel.id);
    } else if (models.length > 0) {
      // 如果没有默认模型，使用第一个
      setModelConfigId(models[0].id);
    }
  });
}, []);
```

## 错误处理

### 1. 模型不存在

**错误**:
```json
{
  "detail": "模型不存在或未启用: xxx"
}
```

**前端处理**:
```typescript
if (error.response?.data?.detail?.includes('模型不存在')) {
  message.error('所选模型不可用，请重新选择');
  // 重新加载模型列表
  loadModels();
}
```

### 2. 缺少 model_config_id

**错误**:
```json
{
  "detail": [
    {
      "loc": ["body", "model_config_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**前端处理**:
```typescript
if (error.response?.status === 422) {
  message.error('请选择 AI 模型');
}
```

### 3. 凭证不可用

**错误**:
```json
{
  "detail": "没有可用的凭证: OpenAI"
}
```

**前端处理**:
```typescript
if (error.response?.data?.detail?.includes('没有可用的凭证')) {
  message.error('AI 服务配置错误，请联系管理员');
}
```

## 数据库查询

### 获取可用模型列表

```sql
SELECT 
  m.id,
  m.display_name,
  m.model_key,
  m.is_default,
  p.name as provider_name,
  p.provider_type
FROM ai_models m
JOIN ai_model_providers p ON m.provider_id = p.id
WHERE m.is_enabled = true
  AND p.is_enabled = true
ORDER BY m.is_default DESC, m.display_name;
```

### 获取默认模型

```sql
SELECT id, display_name
FROM ai_models
WHERE is_enabled = true
  AND is_default = true
LIMIT 1;
```

## 测试建议

### 1. 测试模型选择

```bash
# 运行测试脚本
cd backend
./venv/bin/python test_model_selection.py
```

**预期输出**:
```
📋 找到 X 个可用模型:

模型 ID: xxx
  名称: GPT-4
  模型键: gpt-4
  提供商: OpenAI
  类型: openai
  是否默认: True

⭐ 默认模型:
   ID: xxx
   名称: GPT-4
```

### 2. 测试 API 请求

```bash
# 测试缺少 model_config_id
curl -X POST "http://localhost:8000/api/v1/breakdown/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "xxx"
  }'

# 应该返回 422 错误

# 测试包含 model_config_id
curl -X POST "http://localhost:8000/api/v1/breakdown/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "xxx",
    "model_config_id": "valid-model-id"
  }'

# 应该成功创建任务
```

### 3. 测试模型不存在

```bash
curl -X POST "http://localhost:8000/api/v1/breakdown/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "xxx",
    "model_config_id": "invalid-model-id"
  }'

# 应该返回错误：模型不存在或未启用
```

## 迁移建议

### 1. 设置默认模型

```sql
-- 将某个模型设置为默认
UPDATE ai_models
SET is_default = true
WHERE id = 'your-preferred-model-id';

-- 确保只有一个默认模型
UPDATE ai_models
SET is_default = false
WHERE id != 'your-preferred-model-id';
```

### 2. 向后兼容（可选）

如果需要向后兼容，可以在 API 中添加默认值：

```python
class BreakdownStartRequest(BaseModel):
    batch_id: str
    model_config_id: Optional[str] = None  # 保持可选
    # ...

# 在接口中处理
if not request.model_config_id:
    # 使用默认模型
    default_model = db.query(AIModel).filter(
        AIModel.is_enabled == True,
        AIModel.is_default == True
    ).first()
    
    if not default_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请选择 AI 模型或设置默认模型"
        )
    
    request.model_config_id = str(default_model.id)
```

## 总结

### 后端修改

1. ✅ `model_config_id` 改为必填字段
2. ✅ 创建 `get_adapter_sync` 函数
3. ✅ 在 Celery 任务中使用模型配置
4. ✅ 添加错误处理

### 前端需要修改

1. ❌ 添加模型选择 UI
2. ❌ 获取可用模型列表
3. ❌ 在请求中包含 `model_config_id`
4. ❌ 设置默认值

### 测试状态

- ✅ 代码语法检查通过
- ⏳ 需要运行测试脚本验证
- ⏳ 需要前端配合测试

### 优先级

- **P0 - 立即处理**: 前端必须添加 `model_config_id` 参数
- **P1 - 重要**: 设置默认模型
- **P2 - 建议**: 添加模型选择 UI

---

**实现时间**: 2026-02-10
**实现人员**: AI Assistant
**状态**: ✅ 后端完成，等待前端配合

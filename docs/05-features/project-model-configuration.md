# 项目模型配置实现

## 需求说明

1. **项目配置中保存模型 ID**
   - 用户在项目设置中选择模型
   - 保存到项目表中

2. **两个不同的模型字段**
   - `breakdown_model_id`: 剧情拆解模型
   - `script_model_id`: 剧本生成模型

3. **从项目配置读取**
   - 启动拆解任务时，从项目配置读取 `breakdown_model_id`
   - 启动剧本生成时，从项目配置读取 `script_model_id`
   - 不需要前端传参

## 实现内容

### 1. ✅ 数据库表结构修改

**文件**: `backend/app/models/project.py`

```python
class Project(Base):
    # ... 其他字段 ...
    
    # AI 模型配置
    breakdown_model_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("ai_models.id", ondelete="SET NULL"), 
        nullable=True
    )  # 剧情拆解模型
    
    script_model_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("ai_models.id", ondelete="SET NULL"), 
        nullable=True
    )  # 剧本生成模型
```

**SQL 迁移脚本**: `backend/add_model_ids_to_projects.sql`

```sql
-- 添加字段
ALTER TABLE projects ADD COLUMN breakdown_model_id UUID;
ALTER TABLE projects ADD COLUMN script_model_id UUID;

-- 添加外键约束
ALTER TABLE projects 
ADD CONSTRAINT fk_projects_breakdown_model 
FOREIGN KEY (breakdown_model_id) REFERENCES ai_models(id) ON DELETE SET NULL;

ALTER TABLE projects 
ADD CONSTRAINT fk_projects_script_model 
FOREIGN KEY (script_model_id) REFERENCES ai_models(id) ON DELETE SET NULL;
```

### 2. ✅ API 修改

**文件**: `backend/app/api/v1/breakdown.py`

#### 请求模型修改

```python
class BreakdownStartRequest(BaseModel):
    batch_id: str
    # model_config_id 已移除，不再需要前端传参
    selected_skills: Optional[List[str]] = None
    pipeline_id: Optional[str] = None
    # ...
```

#### 启动拆解逻辑修改

```python
@router.post("/start")
async def start_breakdown(...):
    # 1. 获取批次
    batch = ...
    
    # 2. 获取项目配置
    project = await db.execute(
        select(Project).where(Project.id == batch.project_id)
    )
    
    # 3. 检查是否配置了拆解模型
    if not project.breakdown_model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="项目未配置剧情拆解模型，请先在项目设置中选择模型"
        )
    
    # 4. 创建任务，使用项目配置的模型 ID
    task = AITask(
        config={
            "model_config_id": str(project.breakdown_model_id),  # 从项目读取
            # ...
        }
    )
```

**修改的接口**:
1. ✅ `POST /breakdown/start` - 启动单个批次拆解
2. ✅ `POST /breakdown/start-all` - 批量启动所有未拆解批次
3. ✅ `POST /breakdown/continue/{project_id}` - 继续拆解
4. ✅ `POST /breakdown/batch-start` - 批量启动拆解（增强版）

### 3. ✅ Celery 任务使用模型

**文件**: `backend/app/tasks/breakdown_tasks.py`

```python
# 读取任务配置
task_config = task_record.config if task_record else {}

# 获取模型配置 ID（从项目配置中读取）
model_id = task_config.get("model_config_id")
if not model_id:
    raise ValueError("任务配置中缺少 model_config_id")

# 获取模型适配器
from app.ai.adapters import get_adapter_sync
model_adapter = get_adapter_sync(
    db=db,
    model_id=model_id,
    user_id=user_id
)

# 使用 model_adapter 进行 AI 调用
# ...
```

## 前端需要的修改

### 1. 项目设置页面

**添加模型选择器**:

```tsx
// 项目设置表单
<Form.Item 
  label="剧情拆解模型" 
  name="breakdown_model_id"
  rules={[{ required: true, message: '请选择剧情拆解模型' }]}
>
  <Select placeholder="选择 AI 模型">
    {models.map(model => (
      <Option key={model.id} value={model.id}>
        {model.display_name}
        {model.is_default && <Tag color="blue">推荐</Tag>}
      </Option>
    ))}
  </Select>
</Form.Item>

<Form.Item 
  label="剧本生成模型" 
  name="script_model_id"
  rules={[{ required: true, message: '请选择剧本生成模型' }]}
>
  <Select placeholder="选择 AI 模型">
    {models.map(model => (
      <Option key={model.id} value={model.id}>
        {model.display_name}
        {model.is_default && <Tag color="blue">推荐</Tag>}
      </Option>
    ))}
  </Select>
</Form.Item>
```

### 2. 获取模型列表

```typescript
// API 调用
const getAvailableModels = async () => {
  const response = await api.get('/api/v1/admin/models', {
    params: {
      is_enabled: true
    }
  });
  return response.data;
};
```

### 3. 保存项目配置

```typescript
// 更新项目
const updateProject = async (projectId: string, data: any) => {
  await api.put(`/api/v1/projects/${projectId}`, {
    ...data,
    breakdown_model_id: selectedBreakdownModel,
    script_model_id: selectedScriptModel
  });
};
```

### 4. 启动拆解（无需传 model_config_id）

```typescript
// 之前：需要传 model_config_id
const startBreakdown = async (batchId: string) => {
  await api.post('/api/v1/breakdown/start', {
    batch_id: batchId,
    model_config_id: selectedModelId,  // ❌ 不再需要
    selected_skills: []
  });
};

// 现在：不需要传 model_config_id
const startBreakdown = async (batchId: string) => {
  await api.post('/api/v1/breakdown/start', {
    batch_id: batchId,
    selected_skills: []
    // model_config_id 从项目配置读取
  });
};
```

## 数据库迁移步骤

### 1. 执行 SQL 脚本

```bash
# 连接到数据库
psql -h localhost -p 5433 -U your_user -d your_database

# 执行迁移脚本
\i backend/add_model_ids_to_projects.sql
```

### 2. 验证字段已添加

```sql
-- 查看表结构
\d projects

-- 应该看到：
-- breakdown_model_id | uuid |
-- script_model_id    | uuid |
```

### 3. 设置默认模型（可选）

```sql
-- 为所有现有项目设置默认模型
UPDATE projects 
SET breakdown_model_id = (
    SELECT id FROM ai_models 
    WHERE is_enabled = true AND is_default = true 
    LIMIT 1
)
WHERE breakdown_model_id IS NULL;
```

## 错误处理

### 1. 项目未配置模型

**错误响应**:
```json
{
  "detail": "项目未配置剧情拆解模型，请先在项目设置中选择模型"
}
```

**前端处理**:
```typescript
if (error.response?.data?.detail?.includes('未配置剧情拆解模型')) {
  Modal.confirm({
    title: '未配置模型',
    content: '请先在项目设置中选择剧情拆解模型',
    onOk: () => {
      // 跳转到项目设置页面
      navigate(`/projects/${projectId}/settings`);
    }
  });
}
```

### 2. 模型不存在或未启用

**错误响应**:
```json
{
  "detail": "模型不存在或未启用: xxx"
}
```

**前端处理**:
```typescript
if (error.response?.data?.detail?.includes('模型不存在')) {
  message.error('所选模型不可用，请在项目设置中重新选择');
}
```

## 测试建议

### 1. 测试项目配置

```bash
# 创建项目时设置模型
curl -X POST "http://localhost:8000/api/v1/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试项目",
    "breakdown_model_id": "valid-model-id",
    "script_model_id": "valid-model-id"
  }'
```

### 2. 测试启动拆解（不传 model_config_id）

```bash
# 启动拆解
curl -X POST "http://localhost:8000/api/v1/breakdown/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "xxx",
    "selected_skills": []
  }'

# 应该成功，模型 ID 从项目配置读取
```

### 3. 测试未配置模型的项目

```bash
# 对于没有配置模型的项目
curl -X POST "http://localhost:8000/api/v1/breakdown/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "xxx"
  }'

# 应该返回 400 错误：项目未配置剧情拆解模型
```

## 区分两个模型

### 剧情拆解模型 (breakdown_model_id)

**使用场景**: 
- `/api/v1/breakdown/start` - 启动剧情拆解
- `/api/v1/breakdown/start-all` - 批量启动拆解
- `/api/v1/breakdown/continue` - 继续拆解

**读取方式**:
```python
model_id = project.breakdown_model_id
```

### 剧本生成模型 (script_model_id)

**使用场景**:
- `/api/v1/scripts/generate` - 生成剧本
- 其他剧本相关接口

**读取方式**:
```python
model_id = project.script_model_id
```

**注意**: 不要混淆这两个字段！

## 向后兼容性

### 现有项目处理

**问题**: 现有项目没有配置模型 ID

**解决方案**:

1. **方案 1**: 设置默认模型
```sql
UPDATE projects 
SET breakdown_model_id = (SELECT id FROM ai_models WHERE is_default = true LIMIT 1)
WHERE breakdown_model_id IS NULL;
```

2. **方案 2**: 提示用户配置
```python
if not project.breakdown_model_id:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="项目未配置剧情拆解模型，请先在项目设置中选择模型"
    )
```

**推荐**: 使用方案 2，让用户主动选择模型

## 总结

### 后端修改

1. ✅ 添加数据库字段 `breakdown_model_id` 和 `script_model_id`
2. ✅ 移除请求参数 `model_config_id`
3. ✅ 从项目配置读取模型 ID
4. ✅ 添加模型配置检查
5. ✅ 4 个接口全部修改完成

### 前端需要修改

1. ❌ 项目设置页面添加模型选择器
2. ❌ 保存项目时包含模型 ID
3. ❌ 启动拆解时移除 `model_config_id` 参数
4. ❌ 添加错误处理（未配置模型）

### 数据库迁移

1. ⏳ 执行 SQL 脚本添加字段
2. ⏳ 为现有项目设置默认模型（可选）

### 测试状态

- ✅ 代码语法检查通过
- ⏳ 需要执行数据库迁移
- ⏳ 需要前端配合测试

---

**实现时间**: 2026-02-10
**实现人员**: AI Assistant
**状态**: ✅ 后端完成，等待数据库迁移和前端配合

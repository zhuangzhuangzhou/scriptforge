# 项目模型配置实现完成报告

**日期**: 2026-02-10  
**状态**: ✅ 后端实现完成，等待数据库迁移和前端配合

---

## 实现概述

根据用户需求，已完成以下功能：

1. ✅ 在项目表中添加两个模型字段：`breakdown_model_id` 和 `script_model_id`
2. ✅ 修改所有拆解接口，从项目配置读取模型 ID，不再需要前端传参
3. ✅ 区分剧情拆解模型和剧本生成模型，避免混淆
4. ✅ 添加模型配置检查，未配置模型时返回友好错误提示
5. ✅ Celery 任务使用同步方式获取模型适配器

---

## 已修改的文件

### 1. 数据库模型 (backend/app/models/project.py)

```python
# 添加了两个模型字段
breakdown_model_id = Column(UUID(as_uuid=True), ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True)
script_model_id = Column(UUID(as_uuid=True), ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True)
```

### 2. API 接口 (backend/app/api/v1/breakdown.py)

修改了 4 个接口：

- ✅ `POST /breakdown/start` - 启动单个批次拆解
- ✅ `POST /breakdown/start-all` - 批量启动所有未拆解批次  
- ✅ `POST /breakdown/continue/{project_id}` - 继续拆解
- ✅ `POST /breakdown/batch-start` - 批量启动拆解（增强版）

**关键改动**：
1. 移除了 `BreakdownStartRequest` 中的 `model_config_id` 字段
2. 从项目配置读取 `breakdown_model_id`
3. 添加模型配置检查，未配置时返回 400 错误
4. 任务配置中使用 `project.breakdown_model_id`

### 3. Celery 任务 (backend/app/tasks/breakdown_tasks.py)

```python
# 从任务配置读取模型 ID
model_id = task_config.get("model_config_id")

# 使用同步方式获取模型适配器
from app.ai.adapters import get_adapter_sync
model_adapter = get_adapter_sync(
    db=db,
    model_id=model_id,
    user_id=user_id
)
```

### 4. 模型适配器 (backend/app/ai/adapters/__init__.py)

添加了 `get_adapter_sync()` 函数，支持在 Celery 同步上下文中获取模型适配器。

### 5. 数据库迁移

- ✅ SQL 脚本: `backend/add_model_ids_to_projects.sql`
- ✅ Alembic 迁移: `backend/alembic/versions/add_model_ids_to_project.py`

---

## 下一步操作

### 1. 执行数据库迁移 ⏳

**方式 1: 使用 Alembic（推荐）**

```bash
cd backend
alembic upgrade head
```

**方式 2: 直接执行 SQL**

```bash
psql -h localhost -p 5433 -U your_user -d your_database -f add_model_ids_to_projects.sql
```

**验证迁移**：

```sql
-- 查看表结构
\d projects

-- 应该看到：
-- breakdown_model_id | uuid | 
-- script_model_id    | uuid |
```

### 2. 前端修改 ⏳

#### 2.1 项目设置页面

添加两个模型选择器：

```tsx
<Form.Item 
  label="剧情拆解模型" 
  name="breakdown_model_id"
  rules={[{ required: true, message: '请选择剧情拆解模型' }]}
>
  <Select placeholder="选择 AI 模型">
    {models.map(model => (
      <Option key={model.id} value={model.id}>
        {model.display_name}
      </Option>
    ))}
  </Select>
</Form.Item>

<Form.Item 
  label="剧本生成模型" 
  name="script_model_id"
>
  <Select placeholder="选择 AI 模型">
    {models.map(model => (
      <Option key={model.id} value={model.id}>
        {model.display_name}
      </Option>
    ))}
  </Select>
</Form.Item>
```

#### 2.2 获取可用模型列表

```typescript
const getAvailableModels = async () => {
  const response = await api.get('/api/v1/admin/models', {
    params: { is_enabled: true }
  });
  return response.data;
};
```

#### 2.3 启动拆解（移除 model_config_id）

```typescript
// ❌ 旧代码
const startBreakdown = async (batchId: string) => {
  await api.post('/api/v1/breakdown/start', {
    batch_id: batchId,
    model_config_id: selectedModelId,  // 不再需要
    selected_skills: []
  });
};

// ✅ 新代码
const startBreakdown = async (batchId: string) => {
  await api.post('/api/v1/breakdown/start', {
    batch_id: batchId,
    selected_skills: []
    // model_config_id 从项目配置读取
  });
};
```

#### 2.4 错误处理

```typescript
// 处理未配置模型的错误
if (error.response?.data?.detail?.includes('未配置剧情拆解模型')) {
  Modal.confirm({
    title: '未配置模型',
    content: '请先在项目设置中选择剧情拆解模型',
    onOk: () => {
      navigate(`/projects/${projectId}/settings`);
    }
  });
}
```

### 3. 测试流程 ⏳

#### 3.1 测试项目配置

```bash
# 创建项目并设置模型
curl -X POST "http://localhost:8000/api/v1/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试项目",
    "breakdown_model_id": "valid-model-id",
    "script_model_id": "valid-model-id"
  }'
```

#### 3.2 测试启动拆解

```bash
# 启动拆解（不传 model_config_id）
curl -X POST "http://localhost:8000/api/v1/breakdown/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "xxx",
    "selected_skills": []
  }'

# 应该成功，模型 ID 从项目配置读取
```

#### 3.3 测试未配置模型的项目

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

---

## 错误处理

### 1. 项目未配置模型

**HTTP 状态码**: 400 Bad Request

**错误信息**:
```json
{
  "detail": "项目未配置剧情拆解模型，请先在项目设置中选择模型"
}
```

### 2. 模型不存在或未启用

**HTTP 状态码**: 500 Internal Server Error (在 Celery 任务中)

**错误信息**:
```json
{
  "code": "MODEL_ERROR",
  "message": "模型配置错误: 模型不存在或未启用: xxx"
}
```

---

## 重要提醒

### ⚠️ 区分两个模型字段

1. **breakdown_model_id**: 用于剧情拆解
   - 接口: `/breakdown/start`, `/breakdown/start-all`, `/breakdown/continue`, `/breakdown/batch-start`
   
2. **script_model_id**: 用于剧本生成
   - 接口: `/scripts/generate` 等剧本相关接口
   - **注意**: 剧本生成接口尚未修改，需要后续实现

### ⚠️ 向后兼容性

现有项目的 `breakdown_model_id` 和 `script_model_id` 为 NULL，需要：

**方案 1**: 设置默认模型（可选）
```sql
UPDATE projects 
SET breakdown_model_id = (
    SELECT id FROM ai_models 
    WHERE is_enabled = true AND is_default = true 
    LIMIT 1
)
WHERE breakdown_model_id IS NULL;
```

**方案 2**: 提示用户配置（推荐）
- 用户首次启动拆解时，会收到 400 错误
- 前端引导用户到项目设置页面选择模型

---

## 技术细节

### 数据库约束

```sql
-- 外键约束，模型删除时设置为 NULL
ALTER TABLE projects 
ADD CONSTRAINT fk_projects_breakdown_model 
FOREIGN KEY (breakdown_model_id) 
REFERENCES ai_models(id) 
ON DELETE SET NULL;

ALTER TABLE projects 
ADD CONSTRAINT fk_projects_script_model 
FOREIGN KEY (script_model_id) 
REFERENCES ai_models(id) 
ON DELETE SET NULL;
```

### 同步数据库操作

Celery 任务使用同步数据库会话和同步适配器获取函数：

```python
from app.core.database import SyncSessionLocal
from app.ai.adapters import get_adapter_sync

db = SyncSessionLocal()
model_adapter = get_adapter_sync(db=db, model_id=model_id, user_id=user_id)
```

---

## 验证清单

### 后端 ✅

- [x] 数据库模型添加字段
- [x] API 接口移除 model_config_id 参数
- [x] API 接口从项目配置读取模型 ID
- [x] 添加模型配置检查
- [x] Celery 任务使用模型 ID
- [x] 创建数据库迁移脚本
- [x] 语法检查通过

### 数据库 ⏳

- [ ] 执行 Alembic 迁移
- [ ] 验证字段已添加
- [ ] 验证外键约束已创建
- [ ] （可选）为现有项目设置默认模型

### 前端 ⏳

- [ ] 项目设置页面添加模型选择器
- [ ] 获取可用模型列表
- [ ] 保存项目时包含模型 ID
- [ ] 启动拆解时移除 model_config_id 参数
- [ ] 添加错误处理（未配置模型）
- [ ] 测试完整流程

---

## 相关文档

- [项目模型配置详细文档](./PROJECT_MODEL_CONFIGURATION.md)
- [Celery 修复总结](./CELERY_FIX_SUMMARY.md)
- [Breakdown API 修复](./BREAKDOWN_API_FIXES.md)

---

**实现完成时间**: 2026-02-10  
**实现人员**: AI Assistant  
**下一步**: 执行数据库迁移，前端配合实现

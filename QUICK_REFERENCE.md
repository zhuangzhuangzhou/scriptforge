# 项目模型配置 - 快速参考

**最后更新**: 2026-02-10 01:33  
**状态**: ✅ 后端完成 + 数据库迁移完成

---

## 📋 实现概述

用户需求：
1. ✅ 在项目配置中保存模型 ID（不从前端传参）
2. ✅ 区分两个模型：剧情拆解模型 & 剧本生成模型
3. ✅ 启动拆解时从项目配置读取模型

---

## ✅ 已完成

### 1. 数据库迁移 ✅
```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

**验证结果**:
- ✅ 字段已添加: `breakdown_model_id`, `script_model_id`
- ✅ 外键约束已创建
- ✅ 3 个可用模型（MiniMax-M2.1 为默认）
- ⚠️ 3 个现有项目尚未配置模型

### 2. 后端代码 ✅

**修改的文件**:
- `backend/app/models/project.py` - 添加模型字段
- `backend/app/api/v1/breakdown.py` - 4 个接口修改
- `backend/app/tasks/breakdown_tasks.py` - 使用模型配置
- `backend/app/ai/adapters/__init__.py` - 添加 `get_adapter_sync()`

**API 变更**:
- ❌ 移除: `model_config_id` 请求参数
- ✅ 新增: 从项目配置读取 `breakdown_model_id`
- ✅ 新增: 模型配置检查（未配置返回 400）

---

## ⏳ 待完成 - 前端

### 1. 项目设置页面

添加两个模型选择器：

```tsx
<Form.Item label="剧情拆解模型" name="breakdown_model_id" required>
  <Select placeholder="选择 AI 模型">
    {models.map(model => (
      <Option key={model.id} value={model.id}>
        {model.display_name}
      </Option>
    ))}
  </Select>
</Form.Item>

<Form.Item label="剧本生成模型" name="script_model_id">
  <Select placeholder="选择 AI 模型">
    {models.map(model => (
      <Option key={model.id} value={model.id}>
        {model.display_name}
      </Option>
    ))}
  </Select>
</Form.Item>
```

**获取模型列表**:
```typescript
const models = await api.get('/api/v1/admin/models?is_enabled=true');
```

### 2. 启动拆解

```typescript
// ❌ 旧代码
await api.post('/api/v1/breakdown/start', {
  batch_id: batchId,
  model_config_id: selectedModelId,  // 不再需要
  selected_skills: []
});

// ✅ 新代码
await api.post('/api/v1/breakdown/start', {
  batch_id: batchId,
  selected_skills: []
  // model_config_id 从项目配置读取
});
```

### 3. 错误处理

```typescript
if (error.response?.data?.detail?.includes('未配置剧情拆解模型')) {
  Modal.confirm({
    title: '未配置模型',
    content: '请先在项目设置中选择剧情拆解模型',
    onOk: () => navigate(`/projects/${projectId}/settings`)
  });
}
```

---

## 🔍 可用模型

系统中有 3 个可用模型：

1. **MiniMax-M2.1** [默认]
   - ID: `85ab2385-453c-4f1b-a7d1-3f2ae12256ee`

2. **GPT-4**
   - ID: `3a6fede3-3f41-483a-a83d-14a875f1a740`

3. **GPT-4 Turbo**
   - ID: `ff4cc2ca-c718-4147-968e-7864dbc8e0de`

---

## 🧪 测试

### 测试未配置模型的项目

```bash
curl -X POST "http://localhost:8000/api/v1/breakdown/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"batch_id": "xxx", "selected_skills": []}'

# 应该返回 400: "项目未配置剧情拆解模型"
```

### 测试已配置模型的项目

先配置项目模型，然后启动拆解应该成功。

---

## ⚠️ 重要提醒

### 区分两个模型

1. **breakdown_model_id** - 剧情拆解
   - 用于: `/breakdown/start`, `/breakdown/start-all`, `/breakdown/continue`, `/breakdown/batch-start`

2. **script_model_id** - 剧本生成
   - 用于: `/scripts/generate` 等（尚未实现）

**不要混淆这两个字段！**

---

## 📚 相关文档

- [迁移执行报告](./docs/MIGRATION_EXECUTION_REPORT.md) - 数据库迁移详情
- [实现完成报告](./docs/IMPLEMENTATION_COMPLETE.md) - 完整实现文档
- [项目模型配置](./docs/PROJECT_MODEL_CONFIGURATION.md) - 详细设计文档
- [迁移指南](./backend/MIGRATION_GUIDE.md) - 迁移操作指南

---

## 🎯 下一步

1. ✅ ~~执行数据库迁移~~ (已完成)
2. ⏳ 前端实现项目设置页面
3. ⏳ 前端修改启动拆解逻辑
4. ⏳ 完整流程测试

---

**实现人员**: AI Assistant  
**完成时间**: 2026-02-10 01:33

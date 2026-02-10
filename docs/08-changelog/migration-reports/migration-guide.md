# 数据库迁移指南 - 添加项目模型配置

## 快速执行

### 方式 1: 使用 Alembic（推荐）

```bash
# 1. 进入 backend 目录
cd backend

# 2. 查看待执行的迁移
alembic history

# 3. 执行迁移
alembic upgrade head

# 4. 验证迁移
alembic current
```

### 方式 2: 直接执行 SQL

```bash
# 连接数据库（根据实际情况修改参数）
psql -h localhost -p 5433 -U your_user -d your_database

# 执行迁移脚本
\i add_model_ids_to_projects.sql

# 或者使用命令行
psql -h localhost -p 5433 -U your_user -d your_database -f add_model_ids_to_projects.sql
```

---

## 验证迁移结果

### 1. 检查表结构

```sql
-- 查看 projects 表结构
\d projects

-- 应该看到新增的字段：
-- breakdown_model_id | uuid | 
-- script_model_id    | uuid |
```

### 2. 检查外键约束

```sql
-- 查看外键约束
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.table_name = 'projects'
    AND tc.constraint_type = 'FOREIGN KEY'
    AND (tc.constraint_name LIKE '%breakdown_model%' OR tc.constraint_name LIKE '%script_model%');

-- 应该看到：
-- fk_projects_breakdown_model | projects | breakdown_model_id | ai_models | id
-- fk_projects_script_model    | projects | script_model_id    | ai_models | id
```

### 3. 检查数据

```sql
-- 查看项目统计
SELECT 
    COUNT(*) as total_projects,
    COUNT(breakdown_model_id) as projects_with_breakdown_model,
    COUNT(script_model_id) as projects_with_script_model
FROM projects;
```

---

## 可选：设置默认模型

如果希望为现有项目设置默认模型：

```sql
-- 查询可用的默认模型
SELECT id, display_name, model_key, is_default 
FROM ai_models 
WHERE is_enabled = true;

-- 为所有项目设置默认拆解模型
UPDATE projects 
SET breakdown_model_id = 'your-default-model-id'
WHERE breakdown_model_id IS NULL;

-- 为所有项目设置默认剧本生成模型
UPDATE projects 
SET script_model_id = 'your-default-model-id'
WHERE script_model_id IS NULL;
```

---

## 回滚迁移（如果需要）

### 使用 Alembic 回滚

```bash
# 回滚到上一个版本
alembic downgrade -1

# 或回滚到特定版本
alembic downgrade add_ai_task_state_machine
```

### 手动回滚

```sql
-- 删除外键约束
ALTER TABLE projects DROP CONSTRAINT IF EXISTS fk_projects_script_model;
ALTER TABLE projects DROP CONSTRAINT IF EXISTS fk_projects_breakdown_model;

-- 删除列
ALTER TABLE projects DROP COLUMN IF EXISTS script_model_id;
ALTER TABLE projects DROP COLUMN IF EXISTS breakdown_model_id;
```

---

## 常见问题

### Q1: 迁移失败，提示列已存在

**原因**: 列可能已经通过其他方式添加

**解决方案**:
```sql
-- 检查列是否存在
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'projects' 
    AND column_name IN ('breakdown_model_id', 'script_model_id');

-- 如果列已存在，只需添加外键约束
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

### Q2: 外键约束创建失败

**原因**: 可能存在无效的模型 ID

**解决方案**:
```sql
-- 清理无效的模型 ID
UPDATE projects 
SET breakdown_model_id = NULL 
WHERE breakdown_model_id NOT IN (SELECT id FROM ai_models);

UPDATE projects 
SET script_model_id = NULL 
WHERE script_model_id NOT IN (SELECT id FROM ai_models);

-- 然后重新创建外键约束
```

### Q3: Alembic 提示 "Can't locate revision"

**原因**: 迁移链断裂

**解决方案**:
```bash
# 查看当前数据库版本
alembic current

# 查看迁移历史
alembic history

# 手动标记当前版本
alembic stamp head
```

---

## 迁移后测试

### 1. 测试 API 接口

```bash
# 启动后端服务
uvicorn app.main:app --reload

# 测试启动拆解（不传 model_config_id）
curl -X POST "http://localhost:8000/api/v1/breakdown/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "your-batch-id",
    "selected_skills": []
  }'

# 应该返回 400 错误（如果项目未配置模型）
# 或成功启动任务（如果项目已配置模型）
```

### 2. 测试 Celery 任务

```bash
# 启动 Celery worker
celery -A app.core.celery_app worker --loglevel=info

# 观察日志，确认任务能正确获取模型适配器
```

---

## 迁移检查清单

- [ ] 备份数据库（重要！）
- [ ] 执行迁移（Alembic 或 SQL）
- [ ] 验证表结构
- [ ] 验证外键约束
- [ ] 检查数据完整性
- [ ] （可选）设置默认模型
- [ ] 测试 API 接口
- [ ] 测试 Celery 任务
- [ ] 重启后端服务
- [ ] 重启 Celery worker

---

**迁移版本**: add_model_ids_to_project  
**创建日期**: 2026-02-10  
**依赖版本**: add_ai_task_state_machine

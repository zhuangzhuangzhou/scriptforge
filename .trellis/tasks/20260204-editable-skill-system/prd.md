# 用户可编辑 Skill 系统

## Goal
实现基于 Prompt 模板的用户可编辑 Skill 系统，让用户可以创建、编辑、使用自定义 Skill。

## Requirements

### 1. 修改 Skill 数据库模型
文件: `backend/app/models/skill.py`

新增字段:
- `prompt_template` (Text) - Prompt 模板，支持 {{variable}} 变量
- `output_schema` (JSON) - 输出格式定义
- `input_variables` (JSON) - 输入变量列表 ["content", "context"]
- `is_template_based` (Boolean) - 是否为模板 Skill (区分硬编码和模板)

### 2. 创建数据库迁移
文件: `backend/alembic/versions/add_skill_template_fields.py`

### 3. 创建模板 Skill 执行器
文件: `backend/app/ai/skills/template_skill_executor.py`

功能:
- 从数据库加载 Skill 定义
- 替换 Prompt 模板中的变量
- 调用 LLM 生成结果
- 解析 JSON 输出

### 4. 修改 SkillLoader
文件: `backend/app/ai/skills/skill_loader.py`

功能:
- 支持从数据库加载模板 Skill
- 合并文件 Skill 和数据库 Skill

### 5. 完善 Skill API
文件: `backend/app/api/v1/skills_user.py`

新增端点:
- POST /skills/template - 创建模板 Skill
- PUT /skills/template/{id} - 编辑模板 Skill
- POST /skills/template/{id}/test - 测试 Skill

## Acceptance Criteria
- [ ] Skill 模型新增字段
- [ ] 数据库迁移创建
- [ ] 模板执行器实现
- [ ] SkillLoader 支持数据库加载
- [ ] API 端点完善

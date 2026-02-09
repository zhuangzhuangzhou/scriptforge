# AI ScriptFlow 后端架构与数据模型全面分析

> 生成时间：2026-02-08
> 分析范围：数据模型、API路由、核心功能、架构设计

---

## 📊 数据模型

### 核心业务实体

#### **Project (项目)**
- **字段**: id, user_id, name, novel_type, description, original_file_path/name/size/type, batch_size, chapter_split_rule, total_chapters, total_words, processed_chapters, status, created_at, updated_at
- **状态流转**: draft → uploaded → ready → parsing → scripting → completed
- **关系**: 1:N Chapter, 1:N Batch, 1:N PlotBreakdown, 1:N Script, 1:N AITask
- **文件**: `backend/app/models/project.py`

#### **Chapter (章节)**
- **字段**: id, project_id, batch_id, chapter_number, title, content, word_count, txt_file_path, txt_file_size, skill_processed
- **关系**: N:1 Project, N:1 Batch
- **特色**: skill_processed 存储 Skill 处理后的结构化数据快照
- **文件**: `backend/app/models/chapter.py`

#### **Batch (批次)**
- **字段**: id, project_id, batch_number, start_chapter, end_chapter, total_chapters, total_words, breakdown_status, script_status, ai_processed, context_size
- **状态**: breakdown_status/script_status (pending/processing/completed/failed)
- **关系**: N:1 Project, 1:N Chapter, 1:N PlotBreakdown, 1:N Script
- **文件**: `backend/app/models/batch.py`

#### **PlotBreakdown (剧情拆解)**
- **字段**: id, batch_id, project_id, conflicts, plot_hooks, characters, scenes, emotions, consistency_status, consistency_score, consistency_results, qa_status, qa_report, used_adapt_method_id
- **关系**: N:1 Batch, N:1 Project, 1:N Script
- **特色**: 包含一致性检查和 OWR 质检功能
- **文件**: `backend/app/models/plot_breakdown.py`

#### **Script (剧本)**
- **字段**: id, batch_id, project_id, plot_breakdown_id, episode_number, title, content (JSONB), format_version, word_count, scene_count, is_current
- **关系**: N:1 Batch, N:1 Project, N:1 PlotBreakdown
- **特色**: content 为 JSONB 存储结构化剧本，支持版本管理
- **文件**: `backend/app/models/script.py`

---

### 工作流与执行系统

#### **Pipeline (流水线)**
- **字段**: id, user_id, name, description, config, stages_config, is_default, is_active, version, parent_pipeline_id
- **用途**: 定义剧本生成的完整工作流
- **关系**: 1:N PipelineStage, 1:N PipelineExecution
- **文件**: `backend/app/models/pipeline.py`

#### **PipelineStage (流水线阶段)**
- **字段**: id, pipeline_id, name, display_name, description, skills, skills_order, config, input_mapping, output_mapping, order
- **阶段类型**: breakdown (拆解), script (剧本生成)
- **文件**: `backend/app/models/pipeline.py`

#### **PipelineExecution (流水线执行记录)**
- **字段**: id, pipeline_id, project_id, status, current_stage, progress, current_step, result, error_message, celery_task_id, started_at, completed_at
- **状态**: pending → running → completed/failed
- **文件**: `backend/app/models/pipeline.py`

#### **AITask (AI任务)**
- **字段**: id, project_id, batch_id, task_type, status, progress, current_step, retry_count, depends_on, config, result, error_message, celery_task_id
- **任务类型**: breakdown, script, consistency_check
- **状态**: queued → running → completed/failed
- **文件**: `backend/app/models/ai_task.py`

---

### 技能与智能体系统

#### **Skill (技能)**
- **字段**: id, name, display_name, description, category, module_path, class_name, parameters, is_active, is_builtin, visibility, owner_id, allowed_users, is_template_based, prompt_template, output_schema, input_variables
- **分类**: breakdown, script, analysis
- **权限**: public (公共), private (私有), shared (协作)
- **特色**: 支持模板驱动的可编辑 Skill
- **文件**: `backend/app/models/skill.py`

#### **AgentDefinition (智能体定义)**
- **字段**: id, user_id, name, display_name, description, category, role, goal, system_prompt, workflow_config, trigger_rules, prompt_template, parameters_schema, default_parameters, output_format
- **工作流配置**: 支持多步骤、条件分支、自动触发
- **触发规则**: step_completed, command_received, state_changed
- **文件**: `backend/app/models/agent.py`

#### **AgentExecution (智能体执行记录)**
- **字段**: id, agent_id, pipeline_id, node_id, step_id, input_data, output_data, context_data, context_history, status, error_message, execution_time, tokens_used, model_used
- **文件**: `backend/app/models/agent.py`

---

### 辅助配置

#### **SplitRule (章节拆分规则)**
- **字段**: id, name, display_name, pattern, pattern_type, example, is_default, is_active
- **用途**: 定义小说章节的识别规则（正则表达式）
- **文件**: `backend/app/models/split_rule.py`

#### **AIConfiguration (AI配置)**
- **字段**: id, user_id, key, value (JSONB), category, is_active, description
- **分类**: adapt_method (适配方法), prompt_template (提示模板), quality_rule (质量规则)
- **特色**: 动态配置，支持用户级覆盖
- **文件**: `backend/app/models/ai_configuration.py`

#### **User (用户)**
- **字段**: id, email, username, hashed_password, role, tier, credits, monthly_episodes_used, monthly_reset_at, api_keys
- **等级**: free, creator, studio, enterprise
- **文件**: `backend/app/models/user.py`

---

## 🔌 API 路由结构

### **项目管理** (`/api/v1/projects`)
| 端点 | 方法 | 功能 |
|------|------|------|
| `POST /` | 创建项目 | 创建新项目，检查配额限制 |
| `GET /` | 获取项目列表 | 获取当前用户所有项目 |
| `GET /{id}` | 获取项目详情 | 获取单个项目信息 |
| `PUT /{id}` | 更新项目 | 更新项目基本信息 |
| `DELETE /{id}` | 删除项目 | 删除项目及关联数据 |
| `POST /{id}/upload` | 上传小说文件 | 上传 TXT 到 MinIO，状态 → uploaded |
| `POST /{id}/split` | 拆分章节 | 执行章节识别拆分，状态 → ready |
| `POST /{id}/start` | 启动项目 | 开始剧情分析，状态 → parsing |
| `POST /{id}/create-batches` | 创建批次 | 按 batch_size 分批（幂等） |
| `GET /{id}/batches` | 获取批次列表 | 分页获取项目批次 |
| `GET /{id}/chapters` | 获取章节列表 | 分页+搜索章节 |
| `POST /{id}/chapters/upload` | 上传单章节 | 插入新章节到指定位置 |
| `DELETE /{id}/chapters/{cid}` | 删除章节 | 删除指定章节 |
| `GET /{id}/logs` | 获取项目日志 | 查看项目操作日志 |

**文件**: `backend/app/api/v1/projects.py`

---

### **剧情拆解** (`/api/v1/breakdown`)
| 端点 | 方法 | 功能 |
|------|------|------|
| `POST /start` | 启动拆解 | 为单个批次启动拆解任务 |
| `POST /start-all` | 批量启动 | 启动所有 pending 批次 |
| `POST /start-continue` | 继续拆解 | 从第一个 pending 批次继续 |
| `GET /tasks/{id}` | 获取任务状态 | 查询拆解任务进度 |
| `GET /results/{batch_id}` | 获取拆解结果 | 获取 PlotBreakdown 数据 |

**特色**: 自动消耗剧集配额，创建 AITask 并启动 Celery 异步任务
**文件**: `backend/app/api/v1/breakdown.py`

---

### **剧本生成** (`/api/v1/scripts`)
| 端点 | 方法 | 功能 |
|------|------|------|
| `POST /generate` | 生成剧本 | 基于 PlotBreakdown 生成剧本 |
| `GET /` | 获取剧本列表 | 按项目/批次筛选 |
| `GET /{id}` | 获取单个剧本 | 查看剧本详情 |

**前置条件**: 必须先完成 breakdown
**文件**: `backend/app/api/v1/scripts.py`

---

### **Pipeline 管理** (`/api/v1/pipeline`)
| 端点 | 方法 | 功能 |
|------|------|------|
| `GET /pipelines` | 获取 Pipeline 列表 | 用户 + 默认 Pipeline |
| `POST /pipelines` | 创建 Pipeline | 自定义工作流 |
| `GET /pipelines/{id}` | 获取详情 | Pipeline + Stages |
| `PUT /pipelines/{id}` | 更新 Pipeline | 修改配置，版本号+1 |
| `DELETE /pipelines/{id}` | 删除 Pipeline | 软删除（is_active=false） |
| `POST /pipelines/{id}/execute` | 执行 Pipeline | 启动工作流 |
| `GET /pipelines/{id}/executions` | 执行历史 | 查看历史记录 |
| `GET /pipelines/{id}/executions/{eid}` | 执行详情 | 查看单次执行 |
| `GET /pipelines/{id}/executions/{eid}/logs` | 执行日志 | 实时日志流 |

**文件**: `backend/app/api/v1/pipeline.py`

---

### **其他路由**
- **认证**: `/api/v1/auth` - 登录、注册、刷新 Token
- **技能管理（管理员）**: `/api/v1/skills/admin` - CRUD Skill 定义
- **技能管理（用户）**: `/api/v1/skills/user` - 用户自定义 Skill
- **智能体定义**: `/api/v1/agent-definition` - Agent CRUD
- **配额管理**: `/api/v1/quota` - 检查配额、消耗记录
- **订阅计费**: `/api/v1/subscription`, `/api/v1/billing`
- **导出**: `/api/v1/export` - 导出剧本/拆解结果
- **WebSocket**: `/api/v1/websocket` - 实时推送任务进度
- **AI 配置**: `/api/v1/configurations` - 管理 AI 配置

---

## 🎯 相关功能点

### **1. 剧情拆解功能**
- **实现路径**:
  - API: `backend/app/api/v1/breakdown.py`
  - Model: `backend/app/models/plot_breakdown.py`
  - Task: `app.tasks.breakdown_tasks.run_breakdown_task` (Celery)
- **核心流程**:
  1. 创建 AITask (task_type=breakdown)
  2. 启动 Celery 异步任务
  3. 执行 Skill/Pipeline 进行拆解
  4. 保存 PlotBreakdown 结果（冲突、伏笔、人物、场景、情感）
  5. 可选：一致性检查 + OWR 质检

### **2. 剧本生成功能**
- **实现路径**:
  - API: `backend/app/api/v1/scripts.py`
  - Model: `backend/app/models/script.py`
  - Task: `app.tasks.script_tasks.run_script_task` (Celery)
- **核心流程**:
  1. 验证 PlotBreakdown 存在
  2. 创建 AITask (task_type=script, depends_on=breakdown_task)
  3. 基于 PlotBreakdown 数据生成结构化剧本（JSONB）
  4. 保存 Script 记录

### **3. 章节拆分功能**
- **实现路径**:
  - API: `POST /api/v1/projects/{id}/split`
  - Util: `app.utils.chapter_splitter.ChapterSplitter`
- **核心逻辑**:
  - 从 MinIO 读取原文件
  - 使用 SplitRule 的正则表达式识别章节
  - 批量插入 Chapter 记录
  - 更新 Project 统计信息

### **4. 批次管理功能**
- **实现路径**:
  - API: `POST /api/v1/projects/{id}/create-batches`
  - Util: `app.utils.batch_divider.BatchDivider`
- **核心逻辑**:
  - 按 batch_size 分组章节
  - 智能计算上下文大小 (context_size)
  - 关联章节到批次 (Chapter.batch_id)

### **5. Pipeline 工作流系统**
- **特色**:
  - 可视化配置多阶段工作流
  - 支持 Skill 编排和执行顺序
  - 输入输出映射（input_mapping/output_mapping）
  - 实时日志记录（PipelineExecutionLog）
  - 版本管理和分支（parent_pipeline_id）

### **6. Agent 智能体系统**
- **特色**:
  - 声明式工作流配置（workflow_config）
  - 条件分支和自动触发（trigger_rules）
  - 上下文历史管理（context_history）
  - 支持 call_skill / call_agent / conditional 动作

### **7. 配额与计费系统**
- **实现**:
  - 用户等级（free/creator/studio/enterprise）
  - 项目配额检查（QuotaService.check_project_quota）
  - 剧集配额消耗（consume_episode_quota）
  - 算力积分（User.credits）
  - 月度重置（monthly_reset_at）

---

## 🏗️ 架构洞察

### **1. 核心业务流程**
```
上传小说 → 拆分章节 → 创建批次 → 剧情拆解 → 剧本生成
  (TXT)     (Regex)    (Batch)    (Breakdown)   (Script)
   ↓          ↓          ↓           ↓            ↓
uploaded → ready → parsing → scripting → completed
```

### **2. 异步任务架构**
- 使用 **Celery** 处理耗时的 AI 任务
- AITask 表记录任务状态和依赖关系（depends_on）
- WebSocket 实时推送任务进度
- 支持任务重试（retry_count）

### **3. 数据隔离与权限**
- 所有 API 通过 `get_current_user` 验证身份
- 数据查询强制关联 `user_id` 过滤
- MinIO 路径包含 `user_id` 实现存储隔离
- Skill 支持权限控制（visibility: public/private/shared）

### **4. 灵活配置系统**
- **SplitRule**: 预定义或自定义章节识别规则
- **AIConfiguration**: 动态 Prompt、适配方法、质检规则
- **Skill**: 模板驱动的可编辑 AI 能力
- **Pipeline**: 可视化工作流编排

### **5. 质量保障机制**
- **一致性检查**: consistency_status, consistency_score
- **OWR 质检**: qa_status, qa_report
- **适配方法追踪**: used_adapt_method_id
- **版本管理**: Script.is_current, Pipeline.version

### **6. 扩展性设计**
- **JSONB 字段**: 灵活存储结构化数据（content, config, result）
- **模块化 Skill**: 通过 module_path + class_name 动态加载
- **Agent 工作流**: 声明式配置，无需硬编码
- **Pipeline 分支**: parent_pipeline_id 支持工作流迭代

### **7. 性能优化**
- 分页查询（page, page_size）
- 批量操作（db.add_all, 批量更新）
- 异步数据库（AsyncSession）
- 对象存储（MinIO）分离文件数据

---

## 📌 关键发现

1. **核心数据流**: Project → Chapter → Batch → PlotBreakdown → Script
2. **三大处理引擎**: ChapterSplitter (拆分) → Skill/Agent (拆解) → Skill/Agent (剧本)
3. **双轨执行系统**: AITask (单任务) + Pipeline (工作流)
4. **四层配置体系**: 系统默认 → AIConfiguration → 用户自定义 Skill → Pipeline 编排
5. **完整的配额计费**: 项目数、剧集数、算力积分三维度控制

系统架构成熟，支持从小说上传到剧本生成的全流程自动化处理，具备良好的扩展性和灵活性。

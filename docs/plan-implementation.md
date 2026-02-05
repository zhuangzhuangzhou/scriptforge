# 小说改编剧本系统 - 实施计划

## 项目概述

**统一流程口径**：类型确定 → 剧情拆解+分集标注 → 单集剧本创作 → 质检闭环

**配置驱动原则**：Skill / Agent / Pipeline 通过数据库配置，前端可编辑，执行引擎运行时读取最新配置。


**项目名称**：小说改编剧本系统（Novel-to-Script System）

**核心目标**：开发一款 Web 端应用，让用户能够将上传的小说文件，通过批次处理和两阶段 AI 工作流（剧情拆解 → 剧本生成），自动改编成符合影视剧本标准的剧集，并支持在线编辑和导出。

**核心工作流**：
1. **类型确定** → 确认小说类型并初始化拆解文档
2. **剧情拆解+分集标注** → 按批次拆解剧情点并标注集数
3. **单集剧本创作** → 基于未用剧情点生成剧本
4. **质检闭环** → 拆解与剧本均需 PASS 才能落盘
5. **编辑与导出** → 在创作完成后进入编辑与导出

**技术方案**：Python AI 优先方案
- 前端：React 18 + TypeScript + Vite
- 后端：Python 3.11+ + FastAPI
- AI 框架：LangChain + LangGraph
- 任务队列：Celery + Redis
- 数据库：PostgreSQL 15+
- 文件存储：MinIO（本地开发）/ S3（生产环境）

---

## 用户使用流程

### 流程 1：创建项目

**页面元素**：
- 项目名称（必填）
- 小说类型（选择：都市、古装、科幻等）
- 项目描述（选填）
- 批次大小（必填）：将小说按章节作为一个整体/上下文进行处理
- 章节拆分规则（必填）：自动拆分小说文件为章节的规则
- 上传小说文件（必填）：支持 txt, docx, pdf 等格式

**处理逻辑**：
1. 用户上传小说文件
2. 系统根据章节拆分规则自动识别章节
3. 系统按批次大小将章节分组
4. 创建项目并保存配置

### 流程 2：项目配置

**页面展示**：
- 项目基础信息：项目名称、小说类型、项目描述
- 统计信息：章节总数、总字数、已处理章节数
- 模型配置：
  - **Breakdown 模型**：用于阅读小说原文，提取冲突点、剧情钩子进行分离
  - **Script 模型**：用于将剧情改写为视觉化的剧集，控制节奏和格式

**用户操作**：
- 选择 Breakdown 模型（OpenAI、Anthropic、自定义等）
- 选择 Script 模型
- 配置模型参数（温度、最大 tokens 等）

### 流程 3：剧情拆解（Plot/Breakdown）

**页面布局**：
- 左侧：Agent/Skill 选择器
- 中间：拆解结果列表（按批次分组展示）
- 右侧：拆解详情
- 右下角：控制台窗口（可折叠）

**操作流程**：
1. 用户选择要使用的 Agent/Skill（冲突点提取、剧情钩子识别等）
2. 点击"启动拆解"按钮
3. 右下角控制台窗口展开，实时展示拆解过程：
   - 当前处理的章节
   - 模型返回的信息
   - 进度百分比
4. 拆解完成后：
   - 控制台自动折叠
   - 中间列表展示已拆解的剧情（按批次分组）
   - 列表上方显示"一致性检查"状态（通过/失败）
   - "启动拆解"按钮变为"拆解下一批次（1/x）"
   - 新增"全部拆解"按钮

**一致性检查**：
- 检查拆解结果的逻辑一致性
- 检查人物关系的连贯性
- 检查剧情发展的合理性

### 流程 4：剧本生成（Scripts）

**页面布局**：
- 左侧：剧集列表（按批次分组）
- 右侧：剧本内容展示和编辑区
- 右下角：控制台窗口（可折叠）
- 上方按钮：下载本集、全部打包

**操作流程**：
1. 点击"生成剧本"按钮
2. 右下角控制台窗口展开，实时展示生成过程：
   - 当前生成的剧集
   - 大模型返回的信息
   - 进度百分比
3. 生成完成后：
   - 控制台自动折叠
   - 左侧列表展示已生成的剧集
   - 点击剧集后，右侧展示生成的剧本内容
4. 用户可以在线编辑剧本内容
5. 点击"下载本集"或"全部打包"导出剧本

### 流程 5：编辑和导出

**编辑功能**：
- 在线富文本编辑
- 剧本格式化
- 场景、对话、舞台指示的语法高亮
- 自动保存

**导出功能**：
- 单集导出：PDF、Word、Fountain、txt
- 批量导出：打包为 ZIP 文件

---

## 一、项目结构

### 1.1 根目录结构

```
novel-to-script/
├── frontend/          # React 前端项目
├── backend/           # FastAPI 后端项目
├── docker/            # Docker 配置文件
├── docs/              # 项目文档
├── scripts/           # 部署和工具脚本
├── docker-compose.yml # 本地开发环境
└── README.md          # 项目说明
```

### 1.2 关键文件路径

**前端关键文件**：
- `frontend/src/App.tsx` - 应用主组件
- `frontend/src/router/index.tsx` - 路由配置
- `frontend/src/components/editor/ScriptEditor/` - 剧本编辑器
- `frontend/src/store/` - 状态管理

**后端关键文件**：
- `backend/app/main.py` - FastAPI 应用入口
- `backend/app/api/v1/` - API 路由
- `backend/app/ai/graph/workflow.py` - LangGraph 工作流
- `backend/app/ai/skills/` - 6个内置 Skills
- `backend/app/models/` - 数据库模型

---

## 二、数据库设计

### 2.1 核心表

1. **users** - 用户表（认证、权限、余额）
2. **projects** - 项目表（小说项目管理、批次配置）
3. **chapters** - 章节表（小说章节内容）
4. **batches** - 批次表（章节分组）
5. **plot_breakdowns** - 剧情拆解表（Breakdown 阶段结果）
6. **scripts** - 剧本表（Script 阶段结果，JSONB 存储）
7. **script_versions** - 版本历史表
8. **ai_tasks** - AI 任务表（异步任务追踪）
9. **model_configs** - 模型配置表（Breakdown 和 Script 模型）
10. **consistency_checks** - 一致性检查表
11. **export_records** - 导出记录表
12. **system_settings** - 系统配置表

### 2.2 关键设计决策

- 使用 UUID 作为主键（分布式友好）
- 剧本内容使用 JSONB 存储（灵活的结构化数据）
- 批次处理：章节 → 批次 → 剧情拆解 → 剧本生成
- 两阶段工作流：Breakdown（剧情拆解）→ Script（剧本生成）
- 版本历史采用增量存储策略
- 所有时间字段使用 TIMESTAMP WITH TIME ZONE

---

## 三、API 接口设计

### 3.1 认证授权接口

```
POST   /api/v1/auth/register          # 用户注册
POST   /api/v1/auth/login             # 用户登录
GET    /api/v1/auth/me                # 获取当前用户信息
PUT    /api/v1/auth/me                # 更新用户信息
GET    /api/v1/auth/balance           # 获取用户余额
```

### 3.2 项目管理接口

```
GET    /api/v1/projects               # 获取项目列表
POST   /api/v1/projects               # 创建新项目
GET    /api/v1/projects/{id}          # 获取项目详情
PUT    /api/v1/projects/{id}          # 更新项目信息
DELETE /api/v1/projects/{id}          # 删除项目
POST   /api/v1/projects/{id}/upload   # 上传小说文件
GET    /api/v1/projects/{id}/stats    # 获取项目统计信息
```

### 3.3 章节和批次接口

```
GET    /api/v1/projects/{id}/chapters # 获取章节列表
GET    /api/v1/projects/{id}/batches  # 获取批次列表
GET    /api/v1/batches/{id}           # 获取批次详情
```

### 3.4 剧情拆解接口（Breakdown）

```
POST   /api/v1/breakdown/start        # 启动剧情拆解
POST   /api/v1/breakdown/start-all    # 全部拆解
GET    /api/v1/breakdown/tasks/{id}   # 获取拆解任务状态
GET    /api/v1/breakdown/results/{batch_id} # 获取拆解结果
WS     /api/v1/ws/breakdown/{task_id} # WebSocket 实时进度
```

### 3.5 一致性检查接口

```
POST   /api/v1/consistency/check      # 启动一致性检查
GET    /api/v1/consistency/results/{id} # 获取检查结果
```

### 3.6 剧本生成接口（Script）

```
POST   /api/v1/scripts/generate       # 生成剧本
GET    /api/v1/scripts/tasks/{id}     # 获取生成任务状态
GET    /api/v1/scripts/{id}           # 获取剧本详情
PUT    /api/v1/scripts/{id}           # 更新剧本内容
GET    /api/v1/scripts/batch/{batch_id} # 获取批次的所有剧本
WS     /api/v1/ws/scripts/{task_id}   # WebSocket 实时进度
```

### 3.7 模型配置接口

```
GET    /api/v1/models/configs         # 获取模型配置列表
POST   /api/v1/models/configs         # 创建模型配置
PUT    /api/v1/models/configs/{id}    # 更新模型配置
DELETE /api/v1/models/configs/{id}    # 删除模型配置
```

### 3.8 导出接口

```
POST   /api/v1/export/single          # 导出单集
POST   /api/v1/export/batch           # 批量导出（打包）
GET    /api/v1/export/{id}/download   # 下载导出文件
```

### 3.9 管理端接口

```
GET    /api/v1/admin/users            # 用户管理
PUT    /api/v1/admin/users/{id}       # 更新用户状态
GET    /api/v1/admin/stats            # 系统统计
GET    /api/v1/admin/settings         # 系统配置
PUT    /api/v1/admin/settings         # 更新系统配置
```

---

## 四、AI 工作流设计

### 4.1 两阶段工作流架构

**阶段 1：Breakdown（剧情拆解）**
- 输入：小说章节内容（按批次）
- 输出：结构化的剧情元素（冲突点、剧情钩子、人物、场景、情绪点）
- 模型：Breakdown Model（用户可配置）

**阶段 2：Script（剧本生成）**
- 输入：Breakdown 阶段的输出
- 输出：符合影视剧本格式的剧集
- 模型：Script Model（用户可配置）

### 4.2 Breakdown 阶段 - LangGraph 状态机

**工作流节点**：
1. `load_chapters` - 加载批次的章节内容
2. `extract_conflicts` - 提取冲突点
3. `identify_plot_hooks` - 识别剧情钩子
4. `analyze_characters` - 分析人物关系
5. `identify_scenes` - 识别场景
6. `extract_emotions` - 提取情绪点
7. `consistency_check` - 一致性检查
8. `save_breakdown` - 保存拆解结果

### 4.3 Script 阶段 - LangGraph 状态机

**工作流节点**：
1. `load_breakdown` - 加载 Breakdown 结果
2. `plan_episodes` - 规划剧集结构
3. `generate_scenes` - 生成场景
4. `write_dialogues` - 编写对话
5. `add_stage_directions` - 添加舞台指示
6. `format_script` - 格式化剧本
7. `validate_script` - 验证剧本格式
8. `save_script` - 保存剧本

### 4.4 模型适配器设计

**支持的模型提供商**：
- OpenAI（GPT-4, GPT-3.5）
- Anthropic（Claude）
- Azure OpenAI
- 自定义模型（用户提供 API）

---

## 五、MVP 版本功能范围

### 5.1 MVP 核心功能（v0.1）

**用户端核心流程**：
1. ✅ 用户注册/登录
2. ✅ 创建项目（配置批次大小、章节拆分规则）
3. ✅ 上传小说文件（txt, docx）
4. ✅ 自动章节识别和批次划分
5. ✅ 配置 Breakdown 和 Script 模型
6. ✅ 启动剧情拆解（单批次）
7. ✅ 实时进度展示（控制台窗口）
8. ✅ 查看拆解结果
9. ✅ 启动剧本生成（单批次）
10. ✅ 查看生成的剧本
11. ✅ 基础编辑功能
12. ✅ 导出单集为 PDF

**后台管理端**：
1. ✅ 用户管理（查看、禁用）
2. ✅ 系统模型 API Key 配置
3. ✅ 基础统计信息

**技术实现**：
- 前端：基础 UI 组件 + 项目管理 + 简单编辑器 + 控制台窗口
- 后端：完整的 API + 两阶段 AI 工作流（Breakdown + Script）
- AI：LangGraph 状态机 + 基础模型适配器（OpenAI）
- 数据库：所有核心表
- 实时通信：WebSocket 进度推送
- 部署：Docker Compose 本地部署

**MVP 不包含的功能**：
- 全部拆解/生成（只支持单批次）
- 一致性检查
- 版本管理
- 多模型支持（只支持 OpenAI）
- 高级编辑器功能
- 批量导出

### 5.2 完整版功能（v1.0）

在 MVP 基础上增加：
1. 全部拆解/生成功能
2. 一致性检查
3. 版本管理（历史记录、对比、回滚）
4. 多模型支持（Anthropic、Azure、自定义）
5. 高级编辑器（富文本、格式化、语法高亮）
6. 批量导出（打包为 ZIP）
7. 更多导出格式（Word、Fountain）
8. Agent/Skill 自定义配置
9. 性能优化和错误处理

---

## 六、开发阶段划分

### 阶段 1：基础架构搭建（第1-2周）

**目标**：建立项目骨架和开发环境

**任务**：
1. 初始化前端项目（React + Vite + TypeScript）
2. 初始化后端项目（FastAPI + Python）
3. 配置 Docker 开发环境（PostgreSQL + Redis + MinIO）
4. 设置数据库（创建核心表）
5. 配置 Alembic 数据库迁移
6. 实现基础认证系统（JWT）
7. 实现用户注册/登录 API 和页面

**验证**：
- 前端可以访问并显示登录页面
- 后端 API 文档可以访问（/docs）
- 用户可以注册和登录
- 数据库连接正常

### 阶段 2：项目管理和文件处理（第3周）

**目标**：实现项目创建和小说文件上传

**任务**：
1. 实现项目 CRUD API
2. 实现文件上传 API
3. 实现文件存储（MinIO）
4. 实现文件解析器（txt, docx）
5. 实现章节识别和拆分
6. 实现批次划分逻辑
7. 实现项目管理页面（Dashboard、创建项目、项目详情）

**验证**：
- 用户可以创建项目
- 用户可以上传 txt 和 docx 文件
- 系统可以自动识别章节
- 系统可以按批次大小划分章节

### 阶段 3：Breakdown 工作流（第4-5周）

**目标**：实现剧情拆解功能

**任务**：
1. 配置 LangChain + LangGraph
2. 实现 Breakdown 状态机工作流
3. 实现模型适配器（OpenAI）
4. 实现冲突点提取节点
5. 实现剧情钩子识别节点
6. 实现人物分析节点
7. 实现场景识别节点
8. 实现情绪点提取节点
9. 配置 Celery 异步任务
10. 实现 WebSocket 实时进度推送
11. 实现剧情拆解页面和控制台窗口

**验证**：
- Breakdown 工作流可以完整执行
- 每个节点可以产生预期输出
- 任务进度可以实时更新（控制台窗口）
- 异步任务可以正常执行
- 拆解结果可以正确保存和展示

### 阶段 4：Script 工作流（第6-7周）

**目标**：实现剧本生成功能

**任务**：
1. 实现 Script 状态机工作流
2. 实现剧集规划节点
3. 实现场景生成节点
4. 实现对话编写节点
5. 实现舞台指示节点
6. 实现剧本格式化节点
7. 实现剧本验证节点
8. 实现剧本生成页面
9. 实现剧集列表和剧本展示

**验证**：
- Script 工作流可以完整执行
- 生成的剧本符合影视剧本格式
- 任务进度可以实时更新
- 剧本可以正确保存和展示

### 阶段 5：编辑和导出（第8周）

**目标**：实现剧本编辑和导出功能

**任务**：
1. 集成编辑器库（Slate.js / TipTap）
2. 实现剧本格式化工具
3. 实现自动保存
4. 实现 PDF 导出器
5. 实现导出模板
6. 实现导出任务队列
7. 实现文件下载 API

**验证**：
- 用户可以编辑剧本内容
- 编辑内容可以自动保存
- 用户可以导出剧本为 PDF
- PDF 格式符合影视剧本标准

### 阶段 6：管理端和系统配置（第9周）

**目标**：实现后台管理功能

**任务**：
1. 实现用户管理页面
2. 实现系统配置页面
3. 实现模型配置管理
4. 实现使用统计页面
5. 实现余额管理

**验证**：
- 管理员可以查看和管理用户
- 管理员可以配置系统参数
- 管理员可以查看使用统计

### 阶段 7：测试和优化（第10周）

**目标**：完善 MVP 版本

**任务**：
1. 编写单元测试
2. 编写集成测试
3. 端到端测试
4. 性能优化
5. 错误处理完善
6. 文档编写

**验证**：
- 所有核心功能测试通过
- 系统性能满足基本要求
- 错误可以正确处理和提示

---

## 七、关键技术实现

### 7.1 剧本内容的 JSONB 结构

```json
{
  "version": "1.0",
  "episode_number": 1,
  "title": "第一集标题",
  "scenes": [
    {
      "scene_number": 1,
      "location": "内景 - 咖啡厅 - 日",
      "content": [
        {
          "type": "stage_direction",
          "text": "张三坐在窗边，手里拿着一杯咖啡。"
        },
        {
          "type": "dialogue",
          "character": "张三",
          "text": "今天天气真好。"
        }
      ]
    }
  ]
}
```

### 7.2 WebSocket 实时进度推送

```python
# backend/app/api/v1/websocket.py
@router.websocket("/ws/breakdown/{task_id}")
async def websocket_breakdown_progress(
    websocket: WebSocket,
    task_id: str
):
    await websocket.accept()
    try:
        while True:
            progress = await get_task_progress(task_id)
            await websocket.send_json(progress)
            if progress["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
```

---

## 八、下一步行动

### 立即开始

1. **阶段 1：基础架构搭建**（第1-2周）
   - 初始化前后端项目
   - 配置开发环境
   - 实现用户认证

2. **第一个里程碑**：用户可以注册、登录、创建项目、上传文件

3. **核心里程碑**：完成 Breakdown 和 Script 两阶段工作流

4. **MVP 发布**：完成所有 MVP 功能（预计10周）

### 关键文件路径

**前端关键文件**：
- `frontend/src/pages/user/Dashboard.tsx` - 项目管理首页
- `frontend/src/pages/user/CreateProject.tsx` - 创建项目页面
- `frontend/src/pages/user/PlotBreakdown.tsx` - 剧情拆解页面
- `frontend/src/pages/user/ScriptGeneration.tsx` - 剧本生成页面
- `frontend/src/components/common/ConsoleWindow.tsx` - 控制台窗口组件

**后端关键文件**：
- `backend/app/main.py` - FastAPI 应用入口
- `backend/app/ai/graph/breakdown_workflow.py` - Breakdown 工作流
- `backend/app/ai/graph/script_workflow.py` - Script 工作流
- `backend/app/tasks/ai_tasks.py` - Celery 异步任务
- `backend/app/api/v1/websocket.py` - WebSocket 端点

---

**计划完成时间**：2026-02-03

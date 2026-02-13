# Skill 与 Resource 关联分析

## 概述

本文档分析 Skill 和 Resource 两个功能模块的关系，以及当前实现中存在的问题。

## 核心区别

| 维度 | Skills (技能) | Resources (资源文档) |
|------|--------------|---------------------|
| 用途 | 可执行的 AI 能力单元 | 静态知识/参考文档 |
| 核心内容 | `prompt_template` + 输入/输出 Schema | `content` (Markdown 文档) |
| 分类 | breakdown/qa/script (功能分类) | methodology/output_style/qa_rules/template (知识分类) |
| 执行性 | 有测试功能，可直接调用 LLM | 纯文本，被 Skill 引用 |
| 配置 | model_config、example_input/output | 无 |

## 关联方式

Skill 和 Resource 之间通过任务配置间接关联，而非数据库外键。

### 执行流程

```
1. 任务启动
   ↓
2. PipelineExecutor 加载 Resource 内容
   - adapt_method = await self.get_adapt_method()  → 从 AIResource 表读取 Markdown
   - quality_rule = await self.get_quality_rule()
   - output_style = await self.get_output_style()
   ↓
3. 将 Resource 内容注入到 context 字典
   context = {
       "chapters": [...],
       "adapt_method": "# 网文改编方法论\n...",  ← Resource 内容
       "quality_rule": "# 质检标准\n...",        ← Resource 内容
       "output_style": "# 输出风格\n...",        ← Resource 内容
   }
   ↓
4. 执行 Skill 时，context 作为 variables 传入
   await self.template_executor.execute(
       skill_id=str(skill.id),
       variables=context,  ← 包含 Resource 内容
   )
   ↓
5. TemplateSkillExecutor 渲染模板
   prompt = self._render_template(skill.prompt_template, variables)
   # 将 {{adapt_method}} 替换为实际的 Markdown 内容
```

## 当前问题

### 问题描述

Skill 模板中引用的变量与 PipelineExecutor 加载的变量不匹配。

### Skill 模板使用的变量（以 webtoon_breakdown 为例）

```
{adapt_method}    - 改编方法论
{output_style}    - 输出风格
{template}        - 格式模板
{example}         - 示例
{chapters_text}   - 章节文本
{start_chapter}   - 起始章节
{end_chapter}     - 结束章节
```

### PipelineExecutor 加载的变量

```python
# pipeline_executor.py 中的 run_breakdown 方法
context = {
    "chapters": chapters,
    "model_adapter": self.model_adapter,
    "adapt_method": adapt_method,      # ✅ 已加载
    "quality_rule": quality_rule,      # ⚠️ 模板中未使用
    "output_style": output_style       # ✅ 已加载
}
```

### 缺失的变量

| 变量名 | 状态 | 说明 |
|-------|------|------|
| `{template}` | ❌ 未加载 | 格式模板，应从 AIResource (category: template) 加载 |
| `{example}` | ❌ 未加载 | 示例文档，应从 AIResource (category: template) 加载 |
| `{chapters_text}` | ❌ 未转换 | context 中是 `chapters`，但模板需要 `chapters_text` |
| `{start_chapter}` | ❌ 未传入 | 起始章节号 |
| `{end_chapter}` | ❌ 未传入 | 结束章节号 |

## 修复方案

### 1. 在 PipelineExecutor 中添加缺失的 Resource 加载方法

```python
async def get_template(self) -> str:
    """获取格式模板配置"""
    if self._template is None:
        key = self.task_config.get("template_key", "template_default")
        resource = await self._load_resource(key, "template")
        self._template = resource.content if resource else ""
    return self._template

async def get_example(self) -> str:
    """获取示例配置"""
    if self._example is None:
        key = self.task_config.get("example_key", "example_default")
        resource = await self._load_resource(key, "template")
        self._example = resource.content if resource else ""
    return self._example
```

### 2. 在 run_breakdown 中加载并注入这些变量

```python
async def run_breakdown(...):
    # 加载配置
    adapt_method = await self.get_adapt_method()
    quality_rule = await self.get_quality_rule()
    output_style = await self.get_output_style()
    template = await self.get_template()      # 新增
    example = await self.get_example()        # 新增

    chapters = await self._load_chapters(batch_id)

    # 计算章节范围
    start_chapter = chapters[0].get("chapter_number", 1) if chapters else 1
    end_chapter = chapters[-1].get("chapter_number", len(chapters)) if chapters else 1

    context = {
        "chapters": chapters,
        "chapters_text": self._format_chapters_text(chapters),  # 新增：格式化章节文本
        "model_adapter": self.model_adapter,
        "adapt_method": adapt_method,
        "quality_rule": quality_rule,
        "output_style": output_style,
        "template": template,           # 新增
        "example": example,             # 新增
        "start_chapter": start_chapter, # 新增
        "end_chapter": end_chapter      # 新增
    }
```

### 3. 确保 AIResource 中有对应的初始数据

需要在 `init_ai_resources.py` 中添加 `template_default` 和 `example_default` 资源。

## 修复记录

### 修复日期：2026-02-13

### 修复内容

1. **添加缓存变量**（第 32-37 行）
   - 新增 `_template` 和 `_example` 缓存变量

2. **扩展 context 注入**（第 49-75 行）
   - 加载 `template` 和 `example` Resource
   - 计算 `start_chapter` 和 `end_chapter`
   - 格式化 `chapters_text`

3. **新增方法**
   - `get_template()`: 加载格式模板 Resource
   - `get_example()`: 加载示例 Resource
   - `_format_chapters_text()`: 将章节列表格式化为 Markdown 文本

### 修复后的变量映射

| Skill 模板变量 | context 键 | Resource 来源 |
|---------------|-----------|--------------|
| `{adapt_method}` | `adapt_method` | `adapt_method_default` (methodology) |
| `{output_style}` | `output_style` | `output_style_default` (output_style) |
| `{template}` | `template` | `plot_breakdown_template_default` (template) |
| `{example}` | `example` | `plot_breakdown_example_default` (template) |
| `{chapters_text}` | `chapters_text` | 业务数据（格式化后的章节文本） |
| `{start_chapter}` | `start_chapter` | 业务数据（第一章章节号） |
| `{end_chapter}` | `end_chapter` | 业务数据（最后一章章节号） |

## 相关文件

- `backend/app/tasks/breakdown_tasks.py` - 剧情拆解 Celery 任务（主用）
- `backend/app/tasks/script_tasks.py` - 单集剧本 Celery 任务
- `backend/app/ai/simple_executor.py` - 简化的 Skill/Agent 执行器
- `backend/app/core/init_simple_system.py` - 内置 Skill 定义
- `backend/app/core/init_ai_resources.py` - 内置 Resource 初始化
- `backend/app/models/skill.py` - Skill 模型
- `backend/app/models/ai_resource.py` - AIResource 模型

## 废弃代码清理记录

### 清理日期：2026-02-13

### 删除的文件

| 文件 | 说明 |
|-----|------|
| `backend/app/ai/pipeline_executor.py` | Pipeline 执行器（已废弃） |
| `backend/app/tasks/pipeline_tasks.py` | Pipeline Celery 任务（已废弃） |
| `backend/app/api/v1/pipeline.py` | Pipeline API 路由（已废弃） |

### 修改的文件

| 文件 | 修改内容 |
|-----|---------|
| `backend/app/api/v1/router.py` | 移除 pipeline 路由注册 |
| `backend/app/api/v1/scripts.py` | 删除旧版 `/scripts/generate` API 和 `ScriptGenerateRequest` |
| `backend/app/tasks/script_tasks.py` | 删除旧版 `run_script_task` 函数，清理无用导入 |

### 原因

项目演进过程中产生了两套执行系统：
1. **Pipeline 系统（旧）**：基于 Pipeline/Stage 配置，抽象过度
2. **简化系统（新）**：直接调用 Skill，更简单高效

前端已全面使用简化系统的 API（`/breakdown/start`、`/scripts/episode/start`），Pipeline 系统已无调用，故删除。

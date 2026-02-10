# Agent 实现机制探索报告

## Context（背景）

用户询问系统中是否包含以下两个 agent，以及 agent 的实现机制：
1. 剧情拆解质量校验员（breakdown-aligner）
2. 一致性检查员（webtoon-aligner）

需要解释：
- 这两个 agent 是否存在
- Agent 在系统中是如何实现的
- 如何确保大模型按照预期执行

## 探索发现

### 1. 特定 Agent 的存在性

#### ✅ Breakdown-Aligner（剧情拆解质量校验员）
- **文档位置**: `docs/05-features/ai-workflow/breakdown-aligner.md`
- **代码实现**: `backend/app/ai/skills/breakdown_aligner.py`
- **类名**: `BreakdownAlignerSkill`
- **状态**: 已完整实现

#### ⚠️ Webtoon-Aligner（一致性检查员）
- **文档位置**: `docs/05-features/ai-workflow/webtoon-aligner.md`
- **状态**: 文档已定义，在 orchestrator 中被引用，但尚未实现为独立 Skill 类

### 2. Agent 实现架构

系统采用 **配置驱动 + 模型适配器 + 工作流编排** 的架构：

```
┌─────────────────────────────────────────────────────────┐
│                    Agent 定义层                          │
│  (AgentDefinition 数据库表 + Markdown 文档)              │
│  - 角色设定 (role)                                       │
│  - 目标 (goal)                                           │
│  - 系统提示词 (system_prompt)                            │
│  - Prompt 模板 (prompt_template)                         │
│  - 工作流配置 (workflow_config)                          │
│  - 触发规则 (trigger_rules)                              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   Agent 调度层                           │
│  (AgentOrchestrator)                                     │
│  - 解析工作流配置                                        │
│  - 执行步骤序列                                          │
│  - 处理条件分支                                          │
│  - 触发自动质检                                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   Agent 执行层                           │
│  (AgentExecutor)                                         │
│  - 构建完整 Prompt                                       │
│  - 调用模型适配器                                        │
│  - 解析响应结果                                          │
│  - 验证输出格式                                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  模型适配器层                            │
│  (BaseModelAdapter)                                      │
│  - AnthropicAdapter (Claude)                             │
│  - OpenAIAdapter (GPT)                                   │
│  - GeminiAdapter (Gemini)                                │
└─────────────────────────────────────────────────────────┘
```

### 3. 核心组件详解

#### 3.1 AgentDefinition（Agent 定义）
**位置**: `backend/app/models/agent.py`

数据库表结构：
```python
class AgentDefinition(Base):
    # 基本信息
    name: String(100)              # 内部标识
    display_name: String(255)      # 显示名称
    description: Text              # 描述
    category: String(50)           # 分类

    # Agent 角色配置
    role: Text                      # 角色设定
    goal: Text                      # 目标描述
    system_prompt: Text             # 系统提示词

    # Workflow 配置
    workflow_config: JSON           # 工作流配置
    trigger_rules: JSON             # 触发规则配置

    # Prompt 模板
    prompt_template: Text           # Prompt 模板

    # 参数配置
    parameters_schema: JSON         # 参数 Schema
    default_parameters: JSON        # 默认参数

    # 执行配置
    output_format: String           # text, json, structured
```

#### 3.2 AgentOrchestrator（Agent 调度器）
**位置**: `backend/app/ai/agents/orchestrator.py`

核心功能：
- 解析 `workflow_config` 中的步骤序列
- 支持 4 种步骤类型：
  - `CALL_SKILL`: 调用 Skill
  - `CALL_AGENT`: 递归调用 Sub-Agent
  - `CONDITIONAL`: 条件判断
  - `BRANCH`: 分支
- 处理 `trigger_rules` 实现自动触发
- 维护执行上下文（ExecutionContext）

#### 3.3 AgentExecutor（Agent 执行器）
**位置**: `backend/app/ai/agents/agent_executor.py`

执行流程：
```python
async def execute(agent_definition, input_data, context, parameters):
    # 1. 构建完整的 prompt
    full_prompt = _build_prompt(
        template=agent_definition["prompt_template"],
        input_data=input_data,
        context=context,
        parameters=parameters
    )

    # 2. 获取系统提示词
    system_prompt = agent_definition["system_prompt"]

    # 3. 调用模型生成
    response = await model_adapter.generate(
        prompt=full_prompt,
        system_prompt=system_prompt,
        temperature=parameters.get("temperature", 0.7),
        max_tokens=parameters.get("max_tokens", 4096)
    )

    # 4. 解析结果
    result = _parse_response(response, output_format)

    return {
        "success": True,
        "output": result,
        "tokens_used": tokens_used
    }
```

#### 3.4 模型适配器（Model Adapter）
**位置**: `backend/app/ai/adapters/`

支持的模型：
- **AnthropicAdapter**: Claude 系列（claude-3-opus, claude-3-sonnet 等）
- **OpenAIAdapter**: GPT 系列（gpt-4, gpt-3.5-turbo 等）
- **GeminiAdapter**: Google Gemini 系列

基类接口：
```python
class BaseModelAdapter(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """同步生成"""
        pass

    @abstractmethod
    async def generate_async(self, prompt: str, **kwargs) -> str:
        """异步生成"""
        pass

    @abstractmethod
    def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
        """流式生成"""
        pass
```

### 4. 如何确保大模型按预期执行

系统通过 **5 层约束机制** 确保大模型按预期执行：

#### 4.1 系统提示词（System Prompt）
定义 Agent 的角色和行为约束：
```python
system_prompt = f"""
# 角色
{agent_definition.role}

# 目标
{agent_definition.goal}

# 约束
- 必须严格遵循输出格式
- 不得偏离任务目标
- 必须基于提供的数据进行分析
"""
```

#### 4.2 Prompt 模板（Prompt Template）
使用变量替换构建结构化 Prompt：
```python
prompt_template = """
你是一名资深的漫改编辑，负责审核剧情拆解结果。

### 审核准则
{{rules}}

### 原始章节内容
{{chapters}}

### 待审核的剧情拆解结果
{{breakdown_data}}

### 输出格式（必须严格遵循）
{
    "status": "PASS 或 FAIL",
    "score": 0-100的整数分,
    "issues": ["问题1", "问题2"],
    "suggestions": ["改进建议1", "改进建议2"]
}
"""
```

#### 4.3 输出格式验证（Output Format Validation）
```python
def _parse_response(response: str, output_format: str):
    """根据输出格式解析和验证 Agent 输出"""
    if output_format == "json":
        # 提取 JSON
        json_data = _extract_json(response)
        # 验证 Schema
        validate_schema(json_data, expected_schema)
        return json_data
    elif output_format == "structured":
        # 解析结构化数据
        return _extract_structured(response)
    else:
        return response.strip()
```

#### 4.4 参数约束（Parameters Schema）
```python
parameters_schema = {
    "type": "object",
    "properties": {
        "temperature": {"type": "number", "minimum": 0, "maximum": 1},
        "max_tokens": {"type": "integer", "minimum": 1, "maximum": 8192}
    },
    "required": ["temperature"]
}
```

#### 4.5 工作流约束（Workflow Constraints）
通过工作流配置限制执行路径：
```json
{
    "steps": [
        {
            "id": "step_1",
            "name": "提取冲突",
            "action": "call_skill",
            "target": "conflict_extraction",
            "validation": {
                "required_fields": ["conflicts"],
                "min_count": 1
            }
        },
        {
            "id": "step_2",
            "name": "质量检查",
            "action": "call_agent",
            "target": "breakdown-aligner",
            "auto_trigger": {
                "after": "step_1",
                "condition": "always"
            }
        }
    ]
}
```

### 5. Breakdown-Aligner 的具体实现

#### 5.1 Skill 类实现
**位置**: `backend/app/ai/skills/breakdown_aligner.py`

```python
class BreakdownAlignerSkill(BaseSkill):
    """剧情拆解对齐器 (Aligner Skill)"""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # 1. 获取输入数据
        chapters = context.get("chapters", [])
        breakdown_data = context.get("breakdown_data", {})
        adapt_method = context.get("adapt_method", {})
        model_adapter = context.get("model_adapter")

        # 2. 构建审核 Prompt
        prompt = self._build_qa_prompt(
            chapters=chapters,
            breakdown_data=breakdown_data,
            rules=adapt_method.get("qa_rules", [])
        )

        # 3. 调用模型生成
        response = await model_adapter.generate_async(
            prompt=prompt,
            temperature=0.3,  # 低温度确保稳定输出
            max_tokens=2048
        )

        # 4. 解析 JSON 响应
        result = json.loads(response)

        # 5. 返回质检结果
        return {
            "qa_status": result.get("status", "FAIL"),
            "qa_score": result.get("score", 0),
            "qa_report": result
        }
```

#### 5.2 8 维度检查标准
从文档 `docs/05-features/ai-workflow/breakdown-aligner.md` 定义：

1. **冲突强度评估** - 判断提取的冲突是否达到核心冲突标准
2. **情绪钩子识别准确性** - 验证情绪钩子类型和强度评分
3. **冲突密度达标性** - 计算 6 章内核心冲突数量
4. **分集标注合理性** - 验证每集分配的剧情点数量
5. **压缩策略正确性** - 验证该删的删了、该保留的保留了
6. **剧情点描述规范性** - 验证【剧情n】格式是否完整清晰
7. **原文还原准确性** - 对比小说原文，验证是否准确提取
8. **类型特性符合度** - 验证是否符合该小说类型的特殊要求

### 6. 配置管理

#### 6.1 配置存储
**位置**: `backend/app/models/ai_configuration.py`

```python
class AIConfiguration(Base):
    key: String(255)        # 配置键
    value: JSON             # 配置值
    category: String(50)    # 分类
    user_id: UUID           # 用户 ID（NULL = 系统配置）
    is_active: Boolean      # 是否激活
```

#### 6.2 配置初始化
**位置**: `backend/scripts/init_ai_configs.py`

从 Markdown 文档解析配置并存储到数据库：
```python
CONFIG_MAPPING = [
    {
        "file_path": "docs/breakdown-aligner.md",
        "key": "qa_breakdown_default",
        "category": "quality_rule"
    },
    {
        "file_path": "docs/webtoon-aligner.md",
        "key": "qa_webtoon_default",
        "category": "quality_rule"
    }
]
```

### 7. API 端点

**位置**: `backend/app/api/v1/agent_definition.py`

提供完整的 Agent 管理 API：
- `GET /api/v1/agent-definitions` - 获取 Agent 列表
- `POST /api/v1/agent-definitions` - 创建 Agent
- `GET /api/v1/agent-definitions/{agent_id}` - 获取 Agent 详情
- `PUT /api/v1/agent-definitions/{agent_id}` - 更新 Agent
- `DELETE /api/v1/agent-definitions/{agent_id}` - 删除 Agent
- `POST /api/v1/agent-definitions/execute` - 执行 Agent

### 8. 关键文件位置

| 功能 | 文件路径 |
|------|---------|
| Agent 数据模型 | `backend/app/models/agent.py` |
| Agent 执行器 | `backend/app/ai/agents/agent_executor.py` |
| Agent 调度器 | `backend/app/ai/agents/orchestrator.py` |
| Breakdown-Aligner Skill | `backend/app/ai/skills/breakdown_aligner.py` |
| Breakdown-Aligner 文档 | `docs/05-features/ai-workflow/breakdown-aligner.md` |
| Webtoon-Aligner 文档 | `docs/05-features/ai-workflow/webtoon-aligner.md` |
| 模型适配器基类 | `backend/app/ai/adapters/base.py` |
| Anthropic 适配器 | `backend/app/ai/adapters/anthropic_adapter.py` |
| OpenAI 适配器 | `backend/app/ai/adapters/openai_adapter.py` |
| Gemini 适配器 | `backend/app/ai/adapters/gemini_adapter.py` |
| Skill 加载器 | `backend/app/ai/skills/skill_loader.py` |
| 配置初始化 | `backend/scripts/init_ai_configs.py` |
| 配置模型 | `backend/app/models/ai_configuration.py` |
| Agent API | `backend/app/api/v1/agent_definition.py` |

## 总结

### Agent 实现的核心机制

1. **配置驱动**: Agent 的所有行为通过数据库配置定义，无需修改代码
2. **模型适配器**: 支持多个 AI 模型，统一接口
3. **工作流编排**: 通过 Orchestrator 管理复杂的执行流程
4. **5 层约束**: 系统提示词 + Prompt 模板 + 输出验证 + 参数约束 + 工作流约束
5. **自动质检**: 通过触发规则实现自动质检（如 breakdown-aligner）

### 确保大模型按预期执行的方法

1. **明确的角色设定**: 通过 `role` 和 `goal` 字段定义 Agent 的身份和目标
2. **结构化的 Prompt**: 使用模板系统构建清晰的输入格式
3. **严格的输出格式**: 要求 JSON 输出并进行 Schema 验证
4. **低温度参数**: 质检类任务使用低温度（0.3）确保稳定输出
5. **多轮验证**: 通过工作流配置实现多步骤验证

### 两个 Agent 的状态

- ✅ **Breakdown-Aligner**: 已完整实现，包含 8 维度检查标准
- ✅ **Webtoon-Aligner**: 已完整实现，包含 11 维度检查标准

## 实现完成记录

### Webtoon-Aligner 实现详情（2026-02-10）

#### 已创建文件
1. ✅ `backend/app/ai/skills/webtoon_aligner_skill.py` - Skill 实现类
2. ✅ `backend/app/ai/skills/breakdown_aligner_skill.py` - 重命名以符合加载规范

#### 实现特性
- **11 维度检查标准**：
  1. 剧情点还原一致性
  2. 剧情点使用一致性
  3. 跨集连贯性
  4. 节奏控制一致性
  5. 视觉化风格一致性
  6. 人物行为一致性
  7. 时间线逻辑一致性
  8. 格式规范一致性
  9. 悬念设置一致性
  10. 类型特性一致性
  11. 改编禁忌检查

- **核心功能**：
  - 批次级检查（支持多集同时检查）
  - 跨集连贯性验证（自动读取前一集内容）
  - 基于 plot_breakdown.md 和 adapt_method.md 的双基准检查
  - 结构化 JSON 输出（包含每个维度的详细问题）
  - 低温度（0.3）确保稳定输出

- **输入参数**：
  ```python
  context = {
      "batch_number": int,           # 批次号
      "episode_range": tuple,        # 集数范围，如 (1, 5)
      "plot_breakdown": Dict,        # 剧情拆解数据
      "adapt_method": Dict,          # 改编方法论配置
      "episodes_content": List[Dict], # 待检查的剧本内容
      "previous_episode": Dict,      # 前一集内容（可选）
      "model_adapter": object        # AI 模型适配器
  }
  ```

- **输出格式**：
  ```python
  {
      "check_status": "PASS/FAIL/ERROR",
      "check_score": 0-100,
      "check_report": {
          "status": "PASS/FAIL",
          "score": 0-100,
          "dimensions": {
              "plot_restoration": {"pass": bool, "issues": []},
              "plot_usage": {"pass": bool, "issues": []},
              # ... 其他 9 个维度
          },
          "issues": [
              {
                  "dimension": "维度名称",
                  "episode": 集数,
                  "severity": "critical/warning",
                  "description": "问题描述",
                  "conflict": "冲突内容对比",
                  "suggestion": "修改建议"
              }
          ],
          "summary": "总体评价"
      },
      "batch_number": int,
      "episode_range": tuple
  }
  ```

#### 验证结果
```bash
$ python3 test_skills_loading.py

已加载的 Skills 数量: 10

✅ breakdown_aligner 已加载
   描述: 审核剧情拆解结果是否符合改编方法论要求

✅ webtoon_aligner 已加载
   描述: 检查网文改编漫剧内容的一致性和质量，确保符合改编方法论和剧情拆解要求
```

#### 技术要点
1. **自动加载机制**：文件名必须以 `_skill.py` 结尾才能被 SkillLoader 自动加载
2. **继承结构**：继承自 `BaseSkill`，实现 `execute()` 方法
3. **错误处理**：包含 JSON 解析失败的容错机制
4. **Prompt 工程**：详细的 11 维度检查标准和输出格式要求

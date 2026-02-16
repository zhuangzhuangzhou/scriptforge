# AI 模块开发规范

## 1. Skill 系统架构

### 1.1 核心概念

**Skill** 是系统中可复用的 AI 能力单元，用于封装特定的 AI 任务逻辑。

**关键特性**:
- 继承自 `BaseSkill` 基类
- 实现异步 `execute()` 方法
- 通过 `SkillLoader` 自动加载
- 支持参数配置和上下文传递

### 1.2 目录结构

```text
backend/app/ai/
├── adapters/              # AI 模型适配器
│   ├── base.py            # 基类接口
│   ├── anthropic_adapter.py
│   ├── openai_adapter.py
│   └── gemini_adapter.py
├── agents/                # Agent 编排层
│   ├── agent_executor.py  # Agent 执行器
│   └── orchestrator.py    # 工作流调度器
├── skills/                # Skill 实现
│   ├── base_skill.py      # Skill 基类
│   ├── skill_loader.py    # Skill 加载器
│   ├── *_skill.py         # 具体 Skill 实现
│   └── template_skill_executor.py
└── models/                # AI 相关数据模型
```

## 2. Skill 开发规范

### 2.1 命名规范 ⚠️ CRITICAL

**文件命名**: 必须以 `_skill.py` 结尾

```bash
# ✅ 正确 - 会被自动加载
breakdown_aligner_skill.py
webtoon_aligner_skill.py
conflict_extraction_skill.py

# ❌ 错误 - 不会被加载
breakdown_aligner.py
webtoon_aligner.py
```

**原因**: `SkillLoader` 只加载以 `_skill.py` 结尾的文件（见 `skill_loader.py:39`）

```python
# skill_loader.py
for filename in os.listdir(skills_dir):
    if filename.endswith("_skill.py") and filename != "base_skill.py":
        # 只有这些文件会被加载
```

**类命名**: 使用 `PascalCase` + `Skill` 后缀

```python
# ✅ 正确
class BreakdownAlignerSkill(BaseSkill):
    pass

class WebtoonAlignerSkill(BaseSkill):
    pass

# ❌ 错误
class BreakdownAligner(BaseSkill):  # 缺少 Skill 后缀
    pass
```

### 2.2 基本结构

```python
import logging
from typing import Dict, Any
from app.ai.skills.base_skill import BaseSkill

logger = logging.getLogger(__name__)

class YourSkill(BaseSkill):
    """
    Skill 描述
    """

    def __init__(self):
        super().__init__(
            name="your_skill",  # Skill 标识符（snake_case）
            description="简短描述"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 Skill

        Args:
            context: 包含以下字段:
                - model_adapter: AI 模型适配器（必需）
                - 其他业务参数...

        Returns:
            Dict[str, Any]: 执行结果
        """
        # 1. 获取输入参数
        model_adapter = context.get("model_adapter")
        if not model_adapter:
            raise ValueError("需要提供 model_adapter")

        # 2. 构建 Prompt
        prompt = self._build_prompt(context)

        # 3. 调用模型
        response = await model_adapter.generate_async(
            prompt=prompt,
            temperature=0.7,
            max_tokens=2048
        )

        # 4. 解析结果
        result = self._parse_response(response)

        # 5. 返回结果
        return result

    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """构建 Prompt（私有方法）"""
        pass

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析响应（私有方法）"""
        pass
```

### 2.3 错误处理模式

**JSON 解析容错** - 必须实现

```python
import json

def _parse_response(self, response: str) -> Dict[str, Any]:
    """解析 AI 响应，支持 Markdown 代码块"""
    try:
        # 提取 JSON（某些模型会返回 Markdown 代码块）
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()

        result = json.loads(response)
        return {
            "status": "SUCCESS",
            "data": result
        }
    except Exception as e:
        logger.error(f"响应解析失败: {e}, 原始响应: {response[:500]}")
        return {
            "status": "ERROR",
            "error": str(e),
            "raw_response": response  # 保留原始响应用于调试
        }
```

**为什么需要这样做**:
1. 不同模型的输出格式可能不同（有的会用 Markdown 包裹 JSON）
2. 保留原始响应便于调试
3. 避免因解析失败导致整个流程中断

### 2.4 温度参数选择

| 任务类型 | 推荐温度 | 原因 |
|---------|---------|------|
| **质检/审核** | 0.3 | 需要稳定、一致的输出 |
| **创作/生成** | 0.7 | 需要创造性和多样性 |
| **分类/提取** | 0.5 | 平衡准确性和灵活性 |

```python
# ✅ 质检类 Skill
response = await model_adapter.generate_async(
    prompt=prompt,
    temperature=0.3,  # 低温度确保稳定输出
    max_tokens=2048
)

# ✅ 创作类 Skill
response = await model_adapter.generate_async(
    prompt=prompt,
    temperature=0.7,  # 高温度增加创造性
    max_tokens=4096
)
```

## 3. Prompt 工程最佳实践

### 3.1 结构化 Prompt 模板

```python
def _build_prompt(self, context: Dict[str, Any]) -> str:
    """构建结构化 Prompt"""

    prompt = f"""你是一名资深的{角色描述}，负责{任务描述}。

### 任务目标
{明确的目标描述}

### 输入数据
{格式化的输入数据}

### 检查标准
{详细的检查标准或规则}

### 输出格式（必须严格遵循）
{{
    "field1": "说明",
    "field2": "说明"
}}

### 要求
1. 要求1
2. 要求2
3. 要求3

请开始执行。
"""
    return prompt
```

**关键要素**:
1. **角色设定**: 明确 AI 的身份和专业领域
2. **任务目标**: 清晰描述要完成什么
3. **输入数据**: 结构化展示输入
4. **检查标准**: 详细的评判标准
5. **输出格式**: 明确的 JSON Schema
6. **执行要求**: 具体的约束条件

### 3.2 输出格式约束

**使用 JSON Schema 约束输出**:

```python
prompt = f"""
### 输出格式（必须严格遵循 JSON 格式）

{{
    "status": "PASS 或 FAIL",
    "score": 0-100的整数分,
    "issues": [
        {{
            "dimension": "维度名称",
            "severity": "critical/warning",
            "description": "问题描述",
            "suggestion": "修改建议"
        }}
    ],
    "summary": "总体评价"
}}

注意：
- status 只能是 PASS 或 FAIL
- score 必须是 0-100 的整数
- issues 是数组，可以为空
"""
```

### 3.3 多维度检查模式

**适用场景**: 质检类 Skill（如 Breakdown-Aligner、Webtoon-Aligner）

```python
prompt = f"""
### 检查标准（{维度数量} 个维度）

请严格按照以下维度进行检查：

**【维度1】维度名称**
- 检查点1
- 检查点2
- 检查点3

**【维度2】维度名称**
- 检查点1
- 检查点2

...

### 输出格式
{{
    "dimensions": {{
        "dimension1": {{"pass": true/false, "issues": []}},
        "dimension2": {{"pass": true/false, "issues": []}}
    }},
    "overall_status": "PASS/FAIL"
}}
"""
```

## 4. SkillLoader 使用

### 4.1 自动加载机制

**SkillLoader 工作原理**:
1. 扫描 `app/ai/skills/` 目录
2. 查找所有 `*_skill.py` 文件
3. 动态导入模块
4. 查找继承自 `BaseSkill` 的类
5. 实例化并注册到 `skills` 字典

**单例模式**: SkillLoader 使用单例模式，全局只有一个实例

```python
# 第一次调用会初始化并加载所有 Skills
loader = SkillLoader()

# 后续调用返回同一个实例
loader2 = SkillLoader()  # loader2 is loader == True
```

### 4.2 获取和执行 Skill

```python
from app.ai.skills.skill_loader import SkillLoader

# 获取 SkillLoader 实例
loader = SkillLoader()

# 列出所有已加载的 Skill
skill_names = loader.list_skill_names()
print(skill_names)  # ['breakdown_aligner', 'webtoon_aligner', ...]

# 获取特定 Skill
skill = loader.get_skill("webtoon_aligner")
if skill:
    print(f"找到 Skill: {skill.description}")

# 执行 Skill
result = await loader.execute_skill("webtoon_aligner", context)
```

### 4.3 验证 Skill 加载

**创建测试脚本**:

```python
#!/usr/bin/env python3
"""测试 Skills 加载"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ai.skills.skill_loader import SkillLoader

def test_skills_loading():
    loader = SkillLoader()
    skill_names = loader.list_skill_names()

    print(f"已加载的 Skills 数量: {len(skill_names)}")
    for name in sorted(skill_names):
        skill = loader.get_skill(name)
        print(f"  - {name}: {skill.description}")

if __name__ == "__main__":
    test_skills_loading()
```

## 5. 常见错误和解决方案

### 5.1 Skill 未被加载

**症状**: 调用 `get_skill()` 返回 `None`

**可能原因**:
1. ❌ 文件名不是 `*_skill.py` 格式
2. ❌ 类没有继承 `BaseSkill`
3. ❌ `__init__()` 方法没有调用 `super().__init__()`
4. ❌ 文件中有语法错误导致导入失败

**解决方案**:
```bash
# 1. 检查文件名
ls app/ai/skills/*_skill.py

# 2. 运行测试脚本查看加载日志
python3 test_skills_loading.py

# 3. 检查类定义
grep -n "class.*Skill" app/ai/skills/your_skill.py
```

### 5.2 JSON 解析失败

**症状**: 返回 `ERROR` 状态，`raw_response` 包含非 JSON 内容

**可能原因**:
1. Prompt 不够明确，模型没有按 JSON 格式输出
2. 模型输出被截断（`max_tokens` 太小）
3. 模型在 JSON 前后添加了额外文本

**解决方案**:
```python
# 1. 在 Prompt 中强调输出格式
prompt = f"""
### 输出格式（必须严格遵循 JSON 格式，不要添加任何其他文本）

{{
    "field": "value"
}}

重要：只输出 JSON，不要添加任何解释或说明。
"""

# 2. 增加 max_tokens
response = await model_adapter.generate_async(
    prompt=prompt,
    max_tokens=4096  # 增加到足够大
)

# 3. 使用更强大的模型
# Claude Opus 比 Haiku 更擅长遵循复杂的输出格式要求
```

### 5.3 上下文数据缺失

**症状**: `KeyError` 或 `None` 值导致执行失败

**解决方案**:
```python
# ✅ 使用 .get() 并提供默认值
model_adapter = context.get("model_adapter")
if not model_adapter:
    raise ValueError("需要提供 model_adapter")

# ✅ 提供合理的默认值
temperature = context.get("temperature", 0.7)
max_tokens = context.get("max_tokens", 2048)

# ✅ 记录警告日志
if not context.get("plot_breakdown"):
    logger.warning("未提供 plot_breakdown，检查质量可能受影响")
```

## 6. 质检类 Skill 特殊模式

### 6.1 双基准检查模式

**适用场景**: 需要对照多个基准文档进行检查（如 Webtoon-Aligner）

```python
async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
    # 获取两个基准
    plot_breakdown = context.get("plot_breakdown", {})  # 基准1
    adapt_method = context.get("adapt_method", {})      # 基准2

    # 构建 Prompt 时同时引用两个基准
    prompt = f"""
### 核心基准文档

#### 1. 剧情拆解（plot_breakdown.md）- 最重要的基准
{self._format_plot_breakdown(plot_breakdown)}

#### 2. 改编方法论（adapt_method.md）
{self._format_adapt_method(adapt_method)}

### 检查要求
严格基于以上两个基准进行检查...
"""
```

### 6.2 批次检查模式

**适用场景**: 一次检查多个单元（如多集剧本）

```python
async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
    batch_number = context.get("batch_number", 1)
    episode_range = context.get("episode_range", (1, 1))  # (start, end)
    episodes_content = context.get("episodes_content", [])

    # 构建批次检查 Prompt
    prompt = f"""
### 检查任务
第 {batch_number} 批次（第 {episode_range[0]}-{episode_range[1]} 集）的检查。

### 待检查内容
{self._format_episodes(episodes_content)}

### 检查要求
逐集检查，汇总所有问题...
"""
```

### 6.3 跨单元连贯性检查

**适用场景**: 检查相邻单元之间的衔接（如跨集连贯性）

```python
async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
    current_episode = context.get("current_episode")
    previous_episode = context.get("previous_episode")  # 可选

    if previous_episode:
        # 包含跨集连贯性检查
        prompt = f"""
### 前一集内容（用于检查连贯性）
{previous_episode.get('content', '')}

### 当前集内容
{current_episode.get('content', '')}

### 检查要点
- 开场是否自然接续前一集结尾
- 人物状态是否连续
- 场景转换是否合理
"""
    else:
        # 跳过跨集检查
        prompt = f"""
### 当前集内容
{current_episode.get('content', '')}

注意：这是第一集，无需检查跨集连贯性。
"""
```

## 7. 与 AgentOrchestrator 集成

### 7.1 工作流配置

```python
workflow_config = {
    "steps": [
        {
            "id": "step_1",
            "name": "剧情拆解",
            "action": "call_skill",
            "target": "conflict_extraction"
        },
        {
            "id": "step_2",
            "name": "拆解质量检查",
            "action": "call_skill",
            "target": "breakdown_aligner",
            "auto_trigger": {
                "after": "step_1",
                "condition": "always"
            }
        }
    ]
}
```

### 7.2 自动触发规则

```python
trigger_rules = {
    "auto_trigger": True,
    "trigger_after": "breakdown_complete",
    "trigger_condition": "always"  # 或 "on_success", "on_failure"
}
```

## 8. 测试和调试

### 8.1 单元测试模板

```python
import pytest
from app.ai.skills.your_skill import YourSkill
from app.ai.adapters.anthropic_adapter import AnthropicAdapter

@pytest.mark.asyncio
async def test_your_skill():
    # 准备
    skill = YourSkill()
    model_adapter = AnthropicAdapter(api_key="test_key")

    context = {
        "model_adapter": model_adapter,
        "input_data": {...}
    }

    # 执行
    result = await skill.execute(context)

    # 断言
    assert result["status"] == "SUCCESS"
    assert "data" in result
```

### 8.2 调试技巧

```python
# 1. 添加详细日志
logger.info(f"执行 Skill: {self.name}")
logger.debug(f"输入上下文: {context.keys()}")
logger.debug(f"Prompt 长度: {len(prompt)} 字符")

# 2. 保存原始响应
if response:
    logger.debug(f"原始响应: {response[:500]}...")

# 3. 记录执行时间
import time
start_time = time.time()
result = await model_adapter.generate_async(prompt)
elapsed = time.time() - start_time
logger.info(f"模型调用耗时: {elapsed:.2f}秒")
```

## 9. 性能优化

### 9.1 Prompt 长度优化

```python
# ❌ 不好 - Prompt 过长
prompt = f"""
### 原始章节内容（10万字）
{full_novel_content}
"""

# ✅ 好 - 只包含必要内容
prompt = f"""
### 相关章节摘要
{self._extract_relevant_chapters(chapters, max_length=5000)}
"""
```

### 9.2 批量处理

```python
# ❌ 不好 - 逐个处理
for episode in episodes:
    result = await skill.execute({"episode": episode})

# ✅ 好 - 批量处理
result = await skill.execute({"episodes": episodes})
```

## 10. 文档规范

### 10.1 Skill 文档字符串

```python
class YourSkill(BaseSkill):
    """
    Skill 简短描述（一句话）

    详细说明：
    - 功能1
    - 功能2
    - 功能3

    使用场景：
    - 场景1
    - 场景2
    """

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 Skill

        Args:
            context: 包含以下字段:
                - field1 (Type): 说明
                - field2 (Type): 说明
                - model_adapter (object): AI 模型适配器（必需）

        Returns:
            Dict[str, Any]: 包含以下字段:
                - status (str): SUCCESS/FAIL/ERROR
                - data (Dict): 结果数据
                - error (str, optional): 错误信息

        Raises:
            ValueError: 当缺少必需参数时
        """
```

## 11. 检查清单

### 11.1 新 Skill 开发检查清单

- [ ] 文件名以 `_skill.py` 结尾
- [ ] 类继承自 `BaseSkill`
- [ ] `__init__()` 调用 `super().__init__(name, description)`
- [ ] 实现 `async def execute(self, context)`
- [ ] 包含 JSON 解析容错逻辑
- [ ] 添加详细的文档字符串
- [ ] 使用合适的温度参数
- [ ] 记录必要的日志
- [ ] 创建测试脚本验证加载
- [ ] 更新相关文档

### 11.2 质检类 Skill 额外检查清单

- [ ] 明确定义检查维度
- [ ] 提供详细的检查标准
- [ ] 输出包含具体问题和修改建议
- [ ] 支持批次检查（如适用）
- [ ] 支持跨单元连贯性检查（如适用）
- [ ] 使用低温度（0.3）确保稳定输出
- [ ] 基于明确的基准文档进行检查

---

## 12. 简化架构：Agent / Skill / Resource 三层模式

> **2026-02-12 新增**：基于实践总结的简化架构模式

### 12.1 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      Resource 层                             │
│  AI 资源文档（方法论、输出风格、质检规则、模板案例）          │
│  存储在 AIResource 表，按 category 分类                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Agent 层                               │
│  工作流编排（循环、条件、重试）                              │
│  存储在 SimpleAgent 表，workflow 字段定义流程                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Skill 层                               │
│  Prompt 模板 + 输入/输出定义                                 │
│  存储在 Skill 表，prompt_template 字段定义模板               │
└─────────────────────────────────────────────────────────────┘
```

### 12.2 核心组件

#### Resource（AI 资源文档）

**定义**：存储 AI 任务所需的参考文档，如方法论、规则、模板等。

**分类**：
| Category | 说明 | 示例 |
|----------|------|------|
| `methodology` | 方法论 | 改编核心原则、拆解方法 |
| `output_style` | 输出风格 | 格式规范、语言风格 |
| `qa_rules` | 质检规则 | 检查维度、评分标准 |
| `template` | 模板案例 | 输出格式模板、示例 |

**加载方式**：
```python
# 通过 resource_ids 加载用户选择的资源
grouped_resources = _load_resources_by_ids_sync(db, resource_ids)
adapt_method = "\n\n---\n\n".join(grouped_resources.get("methodology", []))
```

#### Skill（技能单元）

**定义**：Prompt 模板 + 输入/输出 Schema，是最小的 AI 执行单元。

**核心字段**：
- `prompt_template`：Prompt 模板，使用 `{variable}` 占位符
- `input_schema`：输入参数定义
- `output_schema`：输出格式定义
- `model_config`：模型配置（temperature、max_tokens）

**执行器**：`SimpleSkillExecutor`
```python
class SimpleSkillExecutor:
    def execute_skill(self, skill_name: str, inputs: Dict[str, Any], task_id: str):
        # 1. 加载 Skill 配置
        # 2. 预处理输入（自动 JSON 序列化）
        # 3. 填充 Prompt 模板
        # 4. 调用模型
        # 5. 解析 JSON 响应
```

#### Agent（工作流编排）

**定义**：编排多个 Skill 的执行顺序，支持循环、条件、重试。

**工作流类型**：
| Type | 说明 |
|------|------|
| `sequential` | 顺序执行所有步骤 |
| `loop` | 循环执行直到满足退出条件 |

**执行器**：`SimpleAgentExecutor`

### 12.3 循环工作流配置

```python
{
    "type": "loop",
    "max_iterations": 3,
    "exit_condition": "qa_result.status == 'PASS' or qa_result.score >= 70",
    "steps": [
        {
            "id": "breakdown",
            "skill": "webtoon_breakdown",
            "inputs": {
                "chapters_text": "${context.chapters_text}",
                "adapt_method": "${context.adapt_method}"
            },
            "output_key": "plot_points",
            "on_fail": "stop",
            "max_retries": 1
        },
        {
            "id": "qa",
            "skill": "breakdown_aligner",
            "inputs": {
                "plot_points": "${breakdown.plot_points}",
                "chapters_text": "${context.chapters_text}"
            },
            "output_key": "qa_result",
            "on_fail": "skip"
        },
        {
            "id": "fix",
            "skill": "webtoon_breakdown",
            "condition": "qa_result.status != 'PASS' and qa_result.score < 70",
            "inputs": {...},
            "output_key": "plot_points",
            "on_fail": "skip"
        }
    ]
}
```

**步骤配置字段**：
| 字段 | 说明 |
|------|------|
| `id` | 步骤标识符 |
| `skill` | 要调用的 Skill 名称 |
| `inputs` | 输入参数模板，支持 `${context.xxx}` 和 `${step_id.xxx}` 引用 |
| `output_key` | 输出结果的键名 |
| `condition` | 条件表达式，为真时才执行 |
| `on_fail` | 失败处理：`stop`（停止）/ `skip`（跳过）|
| `max_retries` | 最大重试次数 |

### 12.4 输入类型自动转换

> **Gotcha**：Skill 的 `prompt_template` 使用 Python `str.format()`，所有输入必须是字符串。

**问题**：Agent 步骤之间传递的数据可能是 `list` 或 `dict`，直接填充模板会报错。

**解决方案**：`SimpleSkillExecutor` 自动转换输入类型：

```python
# 预处理输入：将非字符串类型转换为 JSON 字符串
processed_inputs = {}
for key, value in inputs.items():
    if isinstance(value, str):
        processed_inputs[key] = value
    elif isinstance(value, (list, dict)):
        processed_inputs[key] = json.dumps(value, ensure_ascii=False, indent=2)
    elif value is None:
        processed_inputs[key] = ""
    else:
        processed_inputs[key] = str(value)
```

### 12.5 用户友好的日志消息

> **最佳实践**：日志消息应该让用户理解正在发生什么，而不是暴露技术细节。

**对比**：
| 场景 | ❌ 技术性消息 | ✅ 用户友好消息 |
|------|-------------|----------------|
| Agent 启动 | `开始执行 Agent: breakdown_agent` | `🤖 启动智能流程：剧情拆解 Agent` |
| 循环迭代 | `循环迭代 1/3` | `🔄 第 1 轮处理（共 3 轮）` |
| 质检通过 | `循环在第 1 轮满足退出条件` | `✅ 质量检查通过，第 1 轮完成` |
| 达到上限 | `循环达到最大迭代次数 3，强制退出` | `⚠️ 已完成 3 轮处理，结果可能需要人工复核` |
| 重试 | `重试步骤 qa (第 1 次)` | `🔁 正在重试...（第 1 次）` |

**原则**：
1. 使用 emoji 增加可读性
2. 避免暴露内部变量名（如 `step_id`）
3. 条件不满足时不发布日志（避免用户困惑）
4. 失败时给出下一步建议

### 12.6 完整调用流程

```
前端 Workspace
    │
    ▼ POST /breakdown/start (resource_ids, batch_id)
API (breakdown.py)
    │
    ▼ run_breakdown_task.delay()
Celery Task (breakdown_tasks.py)
    │
    ├── 1. 加载章节数据
    ├── 2. 加载 AI 资源文档 (Resource)
    ├── 3. 构建 Agent 上下文
    │
    ▼ SimpleAgentExecutor.execute_agent("breakdown_agent")
Agent 执行器 (simple_executor.py)
    │
    ├── 加载 SimpleAgent 配置
    ├── 执行循环工作流
    │       │
    │       ├── Step 1: webtoon_breakdown (Skill)
    │       ├── Step 2: breakdown_aligner (Skill)
    │       └── Step 3: webtoon_breakdown (条件修正)
    │
    ▼ 返回结果
保存 PlotBreakdown
    │
    ▼ 更新 AITask 和 Batch 状态
完成
```

---

**最后更新**: 2026-02-13
**相关文档**:
- [Agent 实现机制探索报告](../../docs/agent-implementation-analysis.md)
- [Agent Skills 使用指南](../../docs/agent-skills-usage-guide.md)

---

## 13. 日志记录规范

### 13.1 LLM 调用日志

> **2026-02-13 新增**：所有 AI 模型调用必须记录完整日志，便于调试和审计。

**日志内容**：
| 字段 | 说明 |
|------|------|
| `prompt` | 完整的请求 prompt |
| `response` | 完整的模型响应 |
| `prompt_tokens` | 输入 token 数 |
| `response_tokens` | 输出 token 数 |
| `latency_ms` | 响应延迟（毫秒） |
| `status` | `success` / `error` |

**适配器自动记录**：
```python
# OpenAIAdapter 和 AnthropicAdapter 自动记录调用日志
adapter = await get_adapter(db=db, model_id=model_config_id)
response = adapter.generate(prompt, temperature=0.7)
# 自动记录到 llm_call_logs 表
```

**禁用日志**（生产环境可能需要）：
```python
adapter = await get_adapter(db=db, log_enabled=False)
```

### 13.2 API 请求日志

> **2026-02-13 新增**：使用 `APILoggingMiddleware` 自动记录所有 HTTP 请求。

**排除路径**：
- `/health` - 健康检查
- `/docs`, `/openapi.json`, `/redoc` - API 文档
- `/favicon.ico` - 图标

**启用方式**（`main.py`）：
```python
from app.middleware.api_logging import APILoggingMiddleware

app.add_middleware(APILoggingMiddleware, enabled=settings.API_LOG_ENABLED)
```

### 13.3 日志查询（管理端）

| API | 用途 |
|-----|------|
| `GET /admin/llm-logs` | LLM 调用日志列表 |
| `GET /admin/llm-logs/{id}` | LLM 调用详情（包含完整 prompt/response） |
| `GET /admin/api-logs` | API 请求日志列表 |
| `GET /admin/logs/stats` | AI 任务统计 |

### 13.4 上下文传递

在 Celery 任务中传递上下文以便日志关联：
```python
from app.ai.llm_logger import llm_context

# 在任务开始时设置上下文
with llm_context(task_id=task_id, user_id=user_id, project_id=project_id):
    # 所有 LLM 调用会自动关联这些信息
    adapter = get_adapter_sync(db, model_id=model_id)
    result = adapter.generate(prompt)
```

---

## 14. 常见问题与解决方案

### 14.1 批次拆解集数不顺延

> **2026-02-13 新增**

**问题**：批次拆解时，大模型不知道前一批次已经拆到第几集，导致每次都从第1集开始编号。

**原因**：Skill 的 prompt_template 中没有告诉大模型"从第几集开始编号"。

**解决方案**：
1. 在 Skill 的 `input_schema` 中添加 `start_episode` 参数
2. 在 `prompt_template` 中明确说明集数编号规则
3. 在 Celery 任务中查询该项目之前批次的最大集数

```python
# breakdown_tasks.py
start_episode = 1
previous_breakdowns = db.query(PlotBreakdown).filter(
    PlotBreakdown.project_id == project_id,
    PlotBreakdown.batch_id != batch_id
).all()

for prev_bd in previous_breakdowns:
    if prev_bd.plot_points:
        for pp in prev_bd.plot_points:
            if isinstance(pp, dict) and pp.get("episode"):
                ep = pp.get("episode")
                if isinstance(ep, int) and ep >= start_episode:
                    start_episode = ep + 1
```

### 14.2 Skill/Agent 初始化不更新

**问题**：修改 `init_simple_system.py` 中的 Skill 定义后，数据库中的记录不会更新。

**原因**：原始逻辑是"存在则跳过"。

**解决方案**：改为"存在则更新"策略：
```python
if not existing_skill:
    # 创建新的 Skill
    skill = Skill(...)
    db.add(skill)
else:
    # 更新已存在的内置 Skill
    existing_skill.prompt_template = skill_data["prompt_template"]
    existing_skill.input_schema = skill_data["input_schema"]
    existing_skill.model_config = skill_data["model_config"]
```

### 14.3 配置优先级设计

**模式**：`Skill 配置 > 模型数据库配置 > 硬编码默认值`

```python
# simple_executor.py
skill_config = skill.model_config or {}
model_defaults = getattr(self.model_adapter, 'model_config', {}) or {}

# 合并配置
temperature = skill_config.get("temperature") or model_defaults.get("temperature_default") or 0.7
max_tokens = skill_config.get("max_tokens") or model_defaults.get("max_output_tokens") or 1000000
```

### 14.4 Token 超限错误处理

**问题**：JSON 响应被截断时，错误信息不友好。

**解决方案**：添加 `TokenLimitExceededError` 异常类：
```python
# exceptions.py
class TokenLimitExceededError(AITaskException):
    def __init__(self, message: str, limit: int = None, actual: int = None):
        super().__init__(message, code="TOKEN_LIMIT_EXCEEDED")

# classify_exception 中识别
token_limit_keywords = [
    "context_length_exceeded", "maximum context length",
    "token limit", "too many tokens", "input is too long"
]
if any(keyword in error_message for keyword in token_limit_keywords):
    return TokenLimitExceededError("内容超过模型 Token 限制，请减少输入内容或分批处理")
```

---

**最后更新**: 2026-02-13

### 14.5 多提供商 API 适配模式

**问题**：不同模型提供商的 API 接口格式不同，导致同一套代码无法兼容多个提供商。

**常见差异**：
| 提供商 | 认证方式 | API 路径 |
|--------|----------|----------|
| Anthropic 官方 | `x-api-key` header | `/v1/messages` |
| 第三方代理 (autocode) | `Authorization: Bearer` | `/v1/messages` |
| Gemini 官方 | URL query param `?key=API_KEY` | `/v1beta/models/{model}:generateContent` |

**解决方案**：在适配器中自动检测并适配

```python
# anthropic_adapter.py
def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
    # 构建 API URL：根据 base_url 自动适配路径
    base = self.base_url.rstrip('/')
    if '/v1' in base or '/messages' in base:
        url = base  # 用户提供了完整路径
    else:
        # 用户只提供了域名，自动补全路径
        if 'anthropic' in base.lower():
            url = f"{base}/anthropic/v1/messages"
        else:
            url = f"{base}/v1/messages"

    # 根据提供商选择认证方式
    headers = {"Content-Type": "application/json", "anthropic-version": "2023-06-01"}
    if "anthropic.com" not in url:
        # 第三方代理使用 Bearer token
        headers["Authorization"] = f"Bearer {self.api_key}"
    else:
        # 官方 API 使用 x-api-key
        headers["x-api-key"] = self.api_key

    # 使用 httpx 发送请求
    with self.http_client.stream("POST", url, json=request_body, headers=headers) as response:
        # 处理 SSE 流...
```

**注意事项**：
1. 用户在提供商管理中填写 `api_endpoint` 时只需填写到域名（如 `https://api.autocode.space`）
2. 适配器自动补全完整的 API 路径
3. 第三方代理可能返回 HTML 错误页面而非 JSON，需要检查响应格式

**为什么需要这样做**：
1. 简化用户配置：只需填写域名，无需了解各提供商的具体 API 路径
2. 兼容性：同一套代码可兼容官方 API 和第三方代理
3. 灵活性：未来新增提供商时只需更新适配逻辑

### 14.6 流式响应与 SDK 兼容性

**问题**：某些第三方代理的流式响应格式与官方 SDK 不兼容，导致 SDK 内部解析失败。

**错误表现**：
```
AttributeError: 'NoneType' object has no attribute 'append'
# SDK 的 accumulate_event 函数中 current_snapshot.content 为 None
```

**解决方案**：使用原始 HTTP 请求绕过 SDK

```python
# anthropic_adapter.py - 使用 httpx 替代 SDK 处理流式响应
def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
    # 使用 httpx 发送原始 HTTP 请求
    with self.http_client.stream("POST", url, json=request_body, headers=headers) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if data.get("type") == "content_block_delta":
                    text = data.get("delta", {}).get("text", "")
                    if text:
                        yield text
```

**为什么需要这样做**：
1. 第三方代理的响应格式可能与官方 API 有细微差异
2. SDK 对响应格式有严格假设，容错性差
3. 原始 HTTP 请求可以更灵活地处理各种响应格式

---

**最后更新**: 2026-02-14

---

## 15. 待优化任务

### 15.1 【TODO】Breakdown 输出格式优化：从 JSON 改为结构化文本

> **2026-02-16 新增**：当前架构存在效率问题，需要重构

**当前问题**：
```
LLM 生成 JSON → 解析 JSON → 存数据库 → 修正时再把 JSON 转文本给 LLM
```
这是脱裤子放屁，JSON 格式对 LLM 不友好，且浪费 Token。

**优化方案**：让 LLM 直接返回结构化文本格式
```
【剧情1】豪华酒店大堂，林浩、陈雪，林浩意外撞见陈雪与神秘男子密谈，悬念开场，第1集
【剧情2】地下停车场，林浩，林浩发现自己的车被人动过手脚，危机出现，第1集
```

**预期收益**：
| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| Token 消耗 | 高（JSON 冗余字符多） | 低（纯文本精简） |
| 修正精准度 | 低（JSON 来回转换） | 高（LLM 直接理解文本） |
| 解析复杂度 | 高（JSON 边界情况多） | 低（正则一行搞定） |

**涉及修改**：
1. `init_simple_system.py`：修改 `webtoon_breakdown` Skill 的 prompt_template 和 output_schema
2. `breakdown_tasks.py`：修改结果解析逻辑，从 JSON 解析改为正则解析
3. `PlotBreakdown` 模型：`plot_points` 字段存储格式变更（或新增 `plot_points_text` 字段）
4. 前端展示逻辑：适配新的数据格式

**优先级**：中（当前功能可用，但效率不高）

**关联**：`execution_mode` 功能已实现，可在此基础上进一步优化

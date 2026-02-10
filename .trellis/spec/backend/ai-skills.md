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

**最后更新**: 2026-02-10
**相关文档**:
- [Agent 实现机制探索报告](../../docs/agent-implementation-analysis.md)
- [Agent Skills 使用指南](../../docs/agent-skills-usage-guide.md)

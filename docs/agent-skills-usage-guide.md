# Agent Skills 使用指南

## 概述

本文档介绍如何使用系统中的两个核心质检 Agent Skills：
1. **Breakdown-Aligner**：剧情拆解质量校验员
2. **Webtoon-Aligner**：网文改编漫剧一致性校验员

## 1. Breakdown-Aligner（剧情拆解质量校验员）

### 功能说明
审核剧情拆解结果是否符合改编方法论要求，包含 8 维度检查标准。

### 使用示例

```python
from app.ai.skills.skill_loader import SkillLoader
from app.ai.adapters.anthropic_adapter import AnthropicAdapter

# 初始化
skill_loader = SkillLoader()
model_adapter = AnthropicAdapter(api_key="your_api_key")

# 准备上下文数据
context = {
    "chapters": [
        {
            "number": 1,
            "title": "重生归来",
            "content": "章节内容..."
        }
    ],
    "breakdown_data": {
        "plot_points": [
            {
                "id": 1,
                "title": "主角重生",
                "content": "主角回到十年前...",
                "conflict_type": "身份冲突",
                "hook_type": "悬念"
            }
        ]
    },
    "adapt_method": {
        "description": "标准网文适配漫画原则",
        "rules": [
            "3秒进冲突",
            "每30秒有推进",
            "500-800字/集"
        ],
        "qa_rules": [
            "冲突强度评估",
            "情绪钩子识别准确性",
            "冲突密度达标性"
        ]
    },
    "model_adapter": model_adapter
}

# 执行检查
result = await skill_loader.execute_skill("breakdown_aligner", context)

# 处理结果
if result["qa_status"] == "PASS":
    print(f"✅ 质检通过，得分: {result['qa_score']}")
else:
    print(f"❌ 质检失败，得分: {result['qa_score']}")
    print(f"问题: {result['qa_report']['issues']}")
    print(f"建议: {result['qa_report']['suggestions']}")
```

### 输出格式

```json
{
    "qa_status": "PASS",
    "qa_score": 85,
    "qa_report": {
        "status": "PASS",
        "score": 85,
        "issues": [],
        "suggestions": [
            "建议增强第3个剧情点的情绪钩子"
        ]
    }
}
```

## 2. Webtoon-Aligner（网文改编漫剧一致性校验员）

### 功能说明
检查网文改编漫剧内容的一致性和质量，包含 11 维度检查标准。

### 使用示例

```python
from app.ai.skills.skill_loader import SkillLoader
from app.ai.adapters.anthropic_adapter import AnthropicAdapter

# 初始化
skill_loader = SkillLoader()
model_adapter = AnthropicAdapter(api_key="your_api_key")

# 准备上下文数据
context = {
    "batch_number": 1,
    "episode_range": (1, 5),  # 第1-5集
    "plot_breakdown": {
        "plot_points": [
            {
                "episode": 1,
                "title": "重生归来",
                "content": "主角回到十年前，发现自己重生了",
                "hook_type": "悬念"
            },
            {
                "episode": 2,
                "title": "复仇开始",
                "content": "主角利用前世记忆，开始复仇计划",
                "hook_type": "冲突"
            }
        ]
    },
    "adapt_method": {
        "description": "标准网文适配漫画原则",
        "rules": [
            "3秒进冲突",
            "每30秒有推进",
            "500-800字/集",
            "1-3个场景/集",
            "每集结尾必须有【卡黑】"
        ]
    },
    "episodes_content": [
        {
            "episode_number": 1,
            "title": "重生归来",
            "content": "# 第1集：重生归来\n\n※场景：医院病房\n\n..."
        },
        {
            "episode_number": 2,
            "title": "复仇开始",
            "content": "# 第2集：复仇开始\n\n※场景：公司大厅\n\n..."
        }
    ],
    "previous_episode": None,  # 第一批次不需要
    "model_adapter": model_adapter
}

# 执行检查
result = await skill_loader.execute_skill("webtoon_aligner", context)

# 处理结果
if result["check_status"] == "PASS":
    print(f"✅ 一致性检查通过，得分: {result['check_score']}")
else:
    print(f"❌ 一致性检查失败，得分: {result['check_score']}")
    report = result["check_report"]

    # 打印各维度检查结果
    for dimension, data in report["dimensions"].items():
        if not data["pass"]:
            print(f"\n【{dimension}】未通过:")
            for issue in data["issues"]:
                print(f"  - {issue}")

    # 打印详细问题
    for issue in report["issues"]:
        print(f"\n问题 [{issue['severity']}]:")
        print(f"  维度: {issue['dimension']}")
        print(f"  集数: 第{issue['episode']}集")
        print(f"  描述: {issue['description']}")
        print(f"  建议: {issue['suggestion']}")
```

### 输出格式

```json
{
    "check_status": "FAIL",
    "check_score": 72,
    "check_report": {
        "status": "FAIL",
        "score": 72,
        "dimensions": {
            "plot_restoration": {
                "pass": true,
                "issues": []
            },
            "plot_usage": {
                "pass": true,
                "issues": []
            },
            "cross_episode_continuity": {
                "pass": true,
                "issues": []
            },
            "rhythm_control": {
                "pass": false,
                "issues": ["第3集字数超过800字"]
            },
            "visual_style": {
                "pass": false,
                "issues": ["第2集缺少视觉描述符号"]
            },
            "character_consistency": {
                "pass": true,
                "issues": []
            },
            "timeline_logic": {
                "pass": true,
                "issues": []
            },
            "format_compliance": {
                "pass": true,
                "issues": []
            },
            "suspense_setting": {
                "pass": false,
                "issues": ["第4集结尾缺少【卡黑】"]
            },
            "genre_characteristics": {
                "pass": true,
                "issues": []
            },
            "adaptation_taboos": {
                "pass": true,
                "issues": []
            }
        },
        "issues": [
            {
                "dimension": "节奏控制一致性",
                "episode": 3,
                "severity": "warning",
                "description": "第3集字数为850字，超过800字上限",
                "conflict": "要求: 500-800字/集，实际: 850字",
                "suggestion": "删减部分环境描写或心理描写，压缩到800字以内"
            },
            {
                "dimension": "视觉化风格一致性",
                "episode": 2,
                "severity": "warning",
                "description": "第2集缺少视觉描述符号（※场景、△动作等）",
                "conflict": "要求: 使用视觉描述符号，实际: 未使用",
                "suggestion": "在场景开始处添加※符号，在动作描写处添加△符号"
            },
            {
                "dimension": "悬念设置一致性",
                "episode": 4,
                "severity": "critical",
                "description": "第4集结尾缺少【卡黑】悬念标记",
                "conflict": "要求: 每集结尾必须有【卡黑】，实际: 无",
                "suggestion": "在第4集结尾添加悬念钩子，如'就在此时，门外传来一阵急促的脚步声...【卡黑】'"
            }
        ],
        "summary": "第1批次(第1-5集)整体质量良好，但存在3处需要修改的问题，主要集中在节奏控制、视觉化风格和悬念设置方面。"
    },
    "batch_number": 1,
    "episode_range": [1, 5]
}
```

## 3. 在工作流中集成

### 3.1 在 AgentOrchestrator 中使用

```python
# 在 workflow_config 中配置自动触发
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
        },
        {
            "id": "step_3",
            "name": "剧本创作",
            "action": "call_skill",
            "target": "scene_generation"
        },
        {
            "id": "step_4",
            "name": "一致性检查",
            "action": "call_skill",
            "target": "webtoon_aligner",
            "auto_trigger": {
                "after": "step_3",
                "condition": "always"
            }
        }
    ]
}
```

### 3.2 在 API 端点中使用

```python
from fastapi import APIRouter, Depends
from app.ai.skills.skill_loader import SkillLoader

router = APIRouter()

@router.post("/check-breakdown")
async def check_breakdown(
    chapters: List[Dict],
    breakdown_data: Dict,
    adapt_method: Dict
):
    """检查剧情拆解质量"""
    skill_loader = SkillLoader()
    model_adapter = get_model_adapter()  # 获取模型适配器

    context = {
        "chapters": chapters,
        "breakdown_data": breakdown_data,
        "adapt_method": adapt_method,
        "model_adapter": model_adapter
    }

    result = await skill_loader.execute_skill("breakdown_aligner", context)
    return result

@router.post("/check-consistency")
async def check_consistency(
    batch_number: int,
    episode_range: tuple,
    plot_breakdown: Dict,
    adapt_method: Dict,
    episodes_content: List[Dict],
    previous_episode: Dict = None
):
    """检查剧本一致性"""
    skill_loader = SkillLoader()
    model_adapter = get_model_adapter()

    context = {
        "batch_number": batch_number,
        "episode_range": episode_range,
        "plot_breakdown": plot_breakdown,
        "adapt_method": adapt_method,
        "episodes_content": episodes_content,
        "previous_episode": previous_episode,
        "model_adapter": model_adapter
    }

    result = await skill_loader.execute_skill("webtoon_aligner", context)
    return result
```

## 4. 最佳实践

### 4.1 温度参数
两个 Skill 都使用低温度（0.3）确保稳定输出，不建议修改。

### 4.2 错误处理
两个 Skill 都包含 JSON 解析失败的容错机制，会返回 ERROR 状态和原始响应。

### 4.3 批次检查
Webtoon-Aligner 支持批次检查（一次检查多集），建议每批次 3-5 集。

### 4.4 跨集连贯性
当检查非第一批次时，务必提供 `previous_episode` 参数以检查跨集连贯性。

### 4.5 基准文档
- Breakdown-Aligner 依赖 `adapt_method` 配置
- Webtoon-Aligner 依赖 `plot_breakdown` 和 `adapt_method` 配置
- 确保这些配置完整且准确

## 5. 故障排查

### 5.1 Skill 未加载
**问题**: 调用 `get_skill()` 返回 None

**解决方案**:
1. 检查文件名是否以 `_skill.py` 结尾
2. 检查类是否继承自 `BaseSkill`
3. 检查 `__init__()` 方法是否正确调用 `super().__init__()`
4. 运行 `test_skills_loading.py` 查看加载日志

### 5.2 JSON 解析失败
**问题**: 返回 ERROR 状态

**解决方案**:
1. 检查 `raw_response` 字段查看原始响应
2. 检查模型是否正确理解输出格式要求
3. 尝试增加 `max_tokens` 参数
4. 检查 Prompt 是否过长导致截断

### 5.3 检查结果不准确
**问题**: 检查结果与预期不符

**解决方案**:
1. 检查输入数据是否完整
2. 检查 `adapt_method` 和 `plot_breakdown` 配置是否准确
3. 检查模型版本是否支持复杂推理
4. 考虑使用更强大的模型（如 Claude Opus）

## 6. 相关文档

- [Agent 实现机制探索报告](./agent-implementation-analysis.md)
- [Breakdown-Aligner 文档](../docs/05-features/ai-workflow/breakdown-aligner.md)
- [Webtoon-Aligner 文档](../docs/05-features/ai-workflow/webtoon-aligner.md)
- [Skill 开发指南](./skill-development-guide.md)

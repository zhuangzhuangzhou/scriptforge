"""初始化简化的 Skill & Agent 系统

在应用启动时自动创建内置的 Skills 和 Agents。
"""
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.skill import Skill
from app.models.agent import SimpleAgent
import uuid

# 系统内置资源的固定 owner_id
SYSTEM_OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


# ==================== 内置 Skills 定义 ====================

BUILTIN_SKILLS = [
    {
        "name": "conflict_extraction",
        "display_name": "冲突提取",
        "description": "从章节内容中提取主要冲突点",
        "category": "breakdown",
        "prompt_template": """你是一个专业的剧情分析师。请分析以下章节内容，提取其中的主要冲突。

章节内容：
{chapters_text}

请以 JSON 数组格式返回冲突列表，每个冲突包含以下字段：
- type: 冲突类型（如：人物冲突、内心冲突、环境冲突等）
- description: 冲突描述
- participants: 参与者列表
- intensity: 冲突强度（1-10）
- chapter_range: 涉及的章节范围 [起始章节, 结束章节]

示例格式：
[
  {{
    "type": "人物冲突",
    "description": "主角与反派之间的权力斗争",
    "participants": ["主角", "反派"],
    "intensity": 8,
    "chapter_range": [1, 3]
  }}
]

请只返回 JSON 数组，不要包含其他文字。""",
        "input_schema": {
            "chapters_text": {
                "type": "string",
                "description": "章节文本内容"
            }
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "description": {"type": "string"},
                    "participants": {"type": "array"},
                    "intensity": {"type": "number"},
                    "chapter_range": {"type": "array"}
                }
            }
        },
        "model_config": {
            "temperature": 0.7,
            "max_tokens": 2000
        },
        "example_input": {
            "chapters_text": "第1章：重生\n主角张三重生到十年前..."
        },
        "example_output": [
            {
                "type": "内心冲突",
                "description": "重生后的迷茫与决心",
                "participants": ["张三"],
                "intensity": 7,
                "chapter_range": [1, 1]
            }
        ]
    },
    {
        "name": "plot_hook_identification",
        "display_name": "剧情钩子识别",
        "description": "识别章节中的剧情钩子，吸引观众继续观看",
        "category": "breakdown",
        "prompt_template": """你是一个专业的剧情分析师。请分析以下章节内容，识别其中的剧情钩子（吸引读者继续阅读的关键点）。

章节内容：
{chapters_text}

请以 JSON 数组格式返回剧情钩子列表，每个钩子包含以下字段：
- type: 钩子类型（如：悬念、转折、伏笔、高潮等）
- hook: 钩子描述
- chapter: 所在章节
- impact: 影响力（1-10）
- emotion: 情绪类型（如：期待、惊讶、紧张等）

示例格式：
[
  {{
    "type": "悬念",
    "hook": "主角发现了一个神秘的线索",
    "chapter": 2,
    "impact": 7,
    "emotion": "期待"
  }}
]

请只返回 JSON 数组，不要包含其他文字。""",
        "input_schema": {
            "chapters_text": {
                "type": "string",
                "description": "章节文本内容"
            }
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "hook": {"type": "string"},
                    "chapter": {"type": "number"},
                    "impact": {"type": "number"},
                    "emotion": {"type": "string"}
                }
            }
        },
        "model_config": {
            "temperature": 0.7,
            "max_tokens": 2000
        }
    },
    {
        "name": "character_analysis",
        "display_name": "角色分析",
        "description": "分析章节中的人物关系、性格特点和发展轨迹",
        "category": "breakdown",
        "prompt_template": """你是一个专业的剧情分析师。请分析以下章节内容，提取并分析其中的主要角色。

章节内容：
{chapters_text}

请以 JSON 数组格式返回角色列表，每个角色包含以下字段：
- name: 角色名称
- role: 角色定位（如：主角、配角、反派等）
- traits: 性格特征列表
- relationships: 与其他角色的关系（对象格式）
- arc: 角色弧光描述

示例格式：
[
  {{
    "name": "张三",
    "role": "主角",
    "traits": ["勇敢", "善良", "冲动"],
    "relationships": {{"李四": "好友", "王五": "敌人"}},
    "arc": "从懦弱到勇敢的成长"
  }}
]

请只返回 JSON 数组，不要包含其他文字。""",
        "input_schema": {
            "chapters_text": {
                "type": "string",
                "description": "章节文本内容"
            }
        },
        "output_schema": {
            "type": "array"
        },
        "model_config": {
            "temperature": 0.7,
            "max_tokens": 2000
        }
    },
    {
        "name": "scene_identification",
        "display_name": "场景识别",
        "description": "识别章节中的场景，包括地点、时间、氛围等",
        "category": "breakdown",
        "prompt_template": """你是一个专业的剧情分析师。请分析以下章节内容，识别其中的主要场景。

章节内容：
{chapters_text}

请以 JSON 数组格式返回场景列表，每个场景包含以下字段：
- location: 场景地点
- time: 时间（如：白天、夜晚、具体时间等）
- description: 场景描述
- characters: 出现的角色列表
- chapter: 所在章节
- mood: 场景氛围

示例格式：
[
  {{
    "location": "古老的城堡",
    "time": "深夜",
    "description": "月光透过破碎的窗户洒进大厅",
    "characters": ["主角", "神秘人"],
    "chapter": 1,
    "mood": "紧张、神秘"
  }}
]

请只返回 JSON 数组，不要包含其他文字。""",
        "input_schema": {
            "chapters_text": {
                "type": "string",
                "description": "章节文本内容"
            }
        },
        "output_schema": {
            "type": "array"
        },
        "model_config": {
            "temperature": 0.7,
            "max_tokens": 2000
        }
    },
    {
        "name": "emotion_extraction",
        "display_name": "情感提取",
        "description": "提取章节中的情感变化",
        "category": "breakdown",
        "prompt_template": """你是一个专业的剧情分析师。请分析以下章节内容，提取其中的情感变化。

章节内容：
{chapters_text}

请以 JSON 数组格式返回情感列表，每个情感包含以下字段：
- emotion: 情感类型（如：喜悦、悲伤、愤怒、恐惧等）
- intensity: 情感强度（1-10）
- character: 相关角色
- trigger: 触发事件
- chapter: 所在章节

示例格式：
[
  {{
    "emotion": "愤怒",
    "intensity": 8,
    "character": "主角",
    "trigger": "发现被背叛",
    "chapter": 3
  }}
]

请只返回 JSON 数组，不要包含其他文字。""",
        "input_schema": {
            "chapters_text": {
                "type": "string",
                "description": "章节文本内容"
            }
        },
        "output_schema": {
            "type": "array"
        },
        "model_config": {
            "temperature": 0.7,
            "max_tokens": 2000
        }
    },
    {
        "name": "episode_planning",
        "display_name": "剧集规划",
        "description": "基于剧情拆解结果规划剧集结构",
        "category": "script",
        "prompt_template": """你是一个专业的剧集规划师。基于以下剧情拆解结果，智能规划剧集结构。

拆解结果：
冲突：{conflicts}
钩子：{plot_hooks}
角色：{characters}
场景：{scenes}
情感：{emotions}

请规划剧集结构，将章节内容合理分配到不同剧集中。每集应该：
1. 有完整的故事弧线
2. 包含主要冲突和高潮
3. 有吸引人的剧情钩子
4. 时长适中（建议每集包含2-4个章节）

以JSON格式返回：
[
  {{
    "episode_number": 1,
    "title": "第一集标题",
    "main_conflict": "主要冲突描述",
    "key_scenes": ["关键场景1", "关键场景2"],
    "chapter_range": [1, 3],
    "conflicts": [],
    "plot_hooks": [],
    "characters": [],
    "scenes": [],
    "emotions": []
  }}
]

请只返回JSON数组，不要包含其他文字。""",
        "input_schema": {
            "conflicts": {"type": "array"},
            "plot_hooks": {"type": "array"},
            "characters": {"type": "array"},
            "scenes": {"type": "array"},
            "emotions": {"type": "array"}
        },
        "output_schema": {
            "type": "array"
        },
        "model_config": {
            "temperature": 0.7,
            "max_tokens": 3000
        }
    },
    {
        "name": "webtoon_breakdown",
        "display_name": "网文改编剧情拆解",
        "description": "基于网文改编方法论，一次性完成剧情拆解、分集标注、情绪钩子识别",
        "category": "breakdown",
        "is_template_based": True,
        "prompt_template": """你是一名资深的网文改编漫剧编辑。请严格按照以下方法论和格式要求，对小说原文进行剧情拆解。

### 改编方法论
{adapt_method}

### 输出风格
{output_style}

### 格式模板
{template}

### 示例
{example}

### 小说原文（第{start_chapter}-{end_chapter}章）
{chapters_text}

### 任务
请按照上述方法论和格式模板，对原文进行剧情拆解。产出统一格式的剧情点列表。

每个剧情点使用以下 JSON 格式：
{{
  "id": 剧情编号,
  "scene": "场景地点",
  "characters": ["角色A", "角色B"],
  "event": "角色A对角色B做了什么",
  "hook_type": "情绪钩子类型",
  "episode": 集数,
  "status": "unused",
  "source_chapter": 来源章节号
}}

请只返回 JSON 数组，不要包含其他文字。""",
        "input_schema": {
            "chapters_text": {"type": "string", "description": "章节文本内容"},
            "adapt_method": {"type": "string", "description": "改编方法论"},
            "output_style": {"type": "string", "description": "输出风格"},
            "template": {"type": "string", "description": "格式模板"},
            "example": {"type": "string", "description": "示例"},
            "start_chapter": {"type": "integer", "description": "起始章节号"},
            "end_chapter": {"type": "integer", "description": "结束章节号"}
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "scene": {"type": "string"},
                    "characters": {"type": "array"},
                    "event": {"type": "string"},
                    "hook_type": {"type": "string"},
                    "episode": {"type": "integer"},
                    "status": {"type": "string"},
                    "source_chapter": {"type": "integer"}
                }
            }
        },
        "model_config": {"temperature": 0.7, "max_tokens": 4000}
    },
    {
        "name": "breakdown_aligner",
        "display_name": "剧情拆解质量校验",
        "description": "基于改编方法论对剧情拆解进行8维度质量检查，确保拆解符合方法论标准",
        "category": "breakdown",
        "is_template_based": True,
        "prompt_template": """你是"网文改编漫剧剧情拆解质量校验员"，负责检查剧情拆解阶段的质量。你是资深的网文改编专家，精通冲突识别、情绪钩子提取、剧情密度评估、分集策略制定。

### 改编方法论（核心基准）
{adapt_method}

### 小说原文
{chapters_text}

### 待检查的剧情拆解结果（JSON）
{plot_points}

### 检查任务
请对上述剧情拆解结果进行全面的8维度质量检查，以改编方法论为核心基准，结合小说原文进行对比验证。

#### 8个检查维度

**维度1：冲突强度评估**
- 标记为高强度的冲突是否真的"改变主角命运、大幅改变格局"
- 冲突类型标注是否准确（人物对立/力量对比/身份矛盾/情感纠葛/生存危机/真相悬念）

**维度2：情绪钩子识别准确性**
- 情绪钩子类型是否准确（打脸蓄力/碾压爽点/金手指觉醒/虐心痛点/真相揭露等）
- 强度评分是否合理（10分=让观众"卧槽"，8-9分=爽/虐/急，6-7分=有感觉）
- 是否遗漏了原文中的高强度钩子

**维度3：冲突密度达标性**
- 核心冲突数量：高密度(5+)、中密度(2-4)、低密度(0-1需说明原因)
- 高强度钩子(8-10分)数量：高密度(6-8)、中密度(3-5)、低密度(1-2需说明原因)

**维度4：分集标注合理性**
- 每集剧情点数量是否合理(1-3个)
- 高强度钩子(10-9分)是否单独成集
- 每集字数估算是否在500-800字范围内

**维度5：压缩策略正确性**
- 必删内容是否删除：环境描写、心理独白、过渡情节、支线剧情、重复内容
- 必留内容是否保留：冲突对话、动作场景、情绪爆点、悬念设置、关系展示

**维度6：剧情点描述规范性**
- 格式是否完整：场景、角色、事件、情绪钩子类型、集数、状态
- 剧情编号是否连续

**维度7：原文还原准确性**
- 剧情点是否准确反映原文内容，有无曲解或遗漏
- 角色关系、事件因果是否与原文一致

**维度8：类型特性符合度**
- 是否符合该小说类型的特殊要求（玄幻/都市/言情/悬疑/科幻/重生复仇等）
- 是否保留了该类型的"必保留"内容，删除了"必删除"内容

### 输出格式
请以 JSON 格式返回质检报告：
{{
  "status": "PASS 或 FAIL",
  "score": 总分(0-100),
  "dimensions": [
    {{
      "name": "维度名称",
      "passed": true/false,
      "score": 维度得分(0-100),
      "details": "检查详情"
    }}
  ],
  "issues": [
    {{
      "dimension": "所属维度",
      "severity": "critical/major/minor",
      "location": "问题位置（剧情编号或章节）",
      "description": "问题描述",
      "rule_violated": "违反的方法论条款",
      "current": "当前内容",
      "expected": "应该如何"
    }}
  ],
  "fix_instructions": [
    {{
      "priority": "high/medium/low",
      "target": "修改目标（剧情编号）",
      "action": "具体修改建议"
    }}
  ]
}}

请只返回 JSON 对象，不要包含其他文字。""",
        "input_schema": {
            "plot_points": {"type": "string", "description": "JSON格式的剧情点列表"},
            "chapters_text": {"type": "string", "description": "小说原文"},
            "adapt_method": {"type": "string", "description": "改编方法论"}
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["PASS", "FAIL"]},
                "score": {"type": "integer"},
                "dimensions": {"type": "array"},
                "issues": {"type": "array"},
                "fix_instructions": {"type": "array"}
            }
        },
        "model_config": {"temperature": 0.3, "max_tokens": 4000}
    }
]


# ==================== 内置 Agents 定义 ====================

BUILTIN_AGENTS = [
    {
        "name": "breakdown_agent",
        "display_name": "剧情拆解 Agent",
        "description": "执行完整的剧情拆解流程：先进行网文改编剧情拆解，再进行8维度质量校验",
        "category": "breakdown",
        "workflow": {
            "steps": [
                {
                    "id": "step1",
                    "skill": "webtoon_breakdown",
                    "inputs": {
                        "chapters_text": "${context.chapters_text}",
                        "adapt_method": "${context.adapt_method}",
                        "output_style": "${context.output_style}",
                        "template": "${context.template}",
                        "example": "${context.example}",
                        "start_chapter": "${context.start_chapter}",
                        "end_chapter": "${context.end_chapter}"
                    },
                    "output_key": "plot_points",
                    "on_fail": "stop",
                    "max_retries": 0
                },
                {
                    "id": "step2",
                    "skill": "breakdown_aligner",
                    "inputs": {
                        "plot_points": "${step1.plot_points}",
                        "chapters_text": "${context.chapters_text}",
                        "adapt_method": "${context.adapt_method}"
                    },
                    "output_key": "qa_result",
                    "on_fail": "stop",
                    "max_retries": 0
                }
            ]
        }
    }
]


# ==================== 初始化函数 ====================

async def init_simple_system(db: Session):
    """初始化简化的 Skill & Agent 系统"""

    # 1. 初始化内置 Skills
    print("初始化内置 Skills...")
    for skill_data in BUILTIN_SKILLS:
        # 检查是否已存在
        result = await db.execute(
            select(Skill).where(Skill.name == skill_data["name"])
        )
        existing_skill = result.scalar_one_or_none()

        if not existing_skill:
            # 创建新的 Skill
            skill = Skill(
                id=uuid.uuid4(),
                name=skill_data["name"],
                display_name=skill_data["display_name"],
                description=skill_data["description"],
                category=skill_data["category"],
                is_template_based=True,
                prompt_template=skill_data["prompt_template"],
                input_schema=skill_data["input_schema"],
                output_schema=skill_data["output_schema"],
                model_config=skill_data["model_config"],
                example_input=skill_data.get("example_input"),
                example_output=skill_data.get("example_output"),
                visibility="public",
                owner_id=SYSTEM_OWNER_ID,
                is_active=True,
                is_builtin=True,
                # 兼容旧字段
                module_path="app.ai.simple_executor",
                class_name="SimpleSkillExecutor"
            )
            db.add(skill)
            print(f"  ✓ 创建 Skill: {skill_data['display_name']}")
        else:
            print(f"  - Skill 已存在: {skill_data['display_name']}")

    await db.commit()
    print(f"✓ 已初始化 {len(BUILTIN_SKILLS)} 个内置 Skills")

    # 2. 初始化内置 Agents
    print("\n初始化内置 Agents...")
    for agent_data in BUILTIN_AGENTS:
        # 检查是否已存在
        result = await db.execute(
            select(SimpleAgent).where(SimpleAgent.name == agent_data["name"])
        )
        existing_agent = result.scalar_one_or_none()

        if not existing_agent:
            # 创建新的 Agent
            agent = SimpleAgent(
                id=uuid.uuid4(),
                name=agent_data["name"],
                display_name=agent_data["display_name"],
                description=agent_data["description"],
                category=agent_data["category"],
                workflow=agent_data["workflow"],
                visibility="public",
                owner_id=SYSTEM_OWNER_ID,
                is_active=True,
                is_builtin=True
            )
            db.add(agent)
            print(f"  ✓ 创建 Agent: {agent_data['display_name']}")
        else:
            print(f"  - Agent 已存在: {agent_data['display_name']}")

    await db.commit()
    print(f"✓ 已初始化 {len(BUILTIN_AGENTS)} 个内置 Agents")

    print("\n✅ 简化系统初始化完成！")

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
    }
]


# ==================== 内置 Agents 定义 ====================

BUILTIN_AGENTS = [
    {
        "name": "breakdown_agent",
        "display_name": "剧情拆解 Agent",
        "description": "执行完整的剧情拆解流程，包括冲突提取、钩子识别、角色分析等",
        "category": "breakdown",
        "workflow": {
            "steps": [
                {
                    "id": "step1",
                    "skill": "conflict_extraction",
                    "inputs": {
                        "chapters_text": "${context.chapters_text}"
                    },
                    "output_key": "conflicts",
                    "on_fail": "stop",
                    "max_retries": 0
                },
                {
                    "id": "step2",
                    "skill": "plot_hook_identification",
                    "inputs": {
                        "chapters_text": "${context.chapters_text}"
                    },
                    "output_key": "plot_hooks",
                    "on_fail": "stop",
                    "max_retries": 0
                },
                {
                    "id": "step3",
                    "skill": "character_analysis",
                    "inputs": {
                        "chapters_text": "${context.chapters_text}"
                    },
                    "output_key": "characters",
                    "on_fail": "stop",
                    "max_retries": 0
                },
                {
                    "id": "step4",
                    "skill": "scene_identification",
                    "inputs": {
                        "chapters_text": "${context.chapters_text}"
                    },
                    "output_key": "scenes",
                    "on_fail": "stop",
                    "max_retries": 0
                },
                {
                    "id": "step5",
                    "skill": "emotion_extraction",
                    "inputs": {
                        "chapters_text": "${context.chapters_text}"
                    },
                    "output_key": "emotions",
                    "on_fail": "stop",
                    "max_retries": 0
                },
                {
                    "id": "step6",
                    "skill": "episode_planning",
                    "inputs": {
                        "conflicts": "${step1.conflicts}",
                        "plot_hooks": "${step2.plot_hooks}",
                        "characters": "${step3.characters}",
                        "scenes": "${step4.scenes}",
                        "emotions": "${step5.emotions}"
                    },
                    "output_key": "episodes",
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

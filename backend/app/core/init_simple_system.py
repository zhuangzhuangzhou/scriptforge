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
        "name": "webtoon_breakdown",
        "display_name": "网文改编剧情拆解",
        "description": "基于网文改编方法论，一次性完成剧情拆解、分集标注、情绪钩子识别",
        "category": "breakdown",
        "is_template_based": True,
        "system_prompt": "你是资深的网文改编漫剧编辑，输出必须严格符合要求的 JSON 格式，不要解释，不要包含多余文字。",
        "prompt_template": """你是一名资深的网文改编漫剧编辑。请严格按照以下方法论和格式要求，对小说原文进行剧情拆解。

### 改编方法论
{adapt_method}

### 输出风格
{output_style}

### 格式模板
{template}

### 示例
{example}

### 上一轮质量检查反馈（如有）
{qa_feedback}

### 小说原文（第{start_chapter}-{end_chapter}章）
{chapters_text}

### 集数编号规则
**重要**：本批次的集数编号必须从第 {start_episode} 集开始，依次递增。
- 如果 start_episode=1，则本批次拆分的集数为 1, 2, 3...
- 如果 start_episode=4，则本批次拆分的集数为 4, 5, 6...（因为前面的批次已经拆到第3集）

### 任务
请按照上述方法论和格式模板，对原文进行剧情拆解。产出统一格式的剧情点列表。

每个剧情点使用以下 JSON 格式：
{{
  "id": 剧情编号,
  "scene": "场景地点",
  "characters": ["角色A", "角色B"],
  "event": "角色A对角色B做了什么",
  "hook_type": "情绪钩子类型",
  "episode": 集数（从 {start_episode} 开始编号）,
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
            "qa_feedback": {"type": "string", "description": "上一轮质量检查反馈（可选）"},
            "start_chapter": {"type": "integer", "description": "起始章节号"},
            "end_chapter": {"type": "integer", "description": "结束章节号"},
            "start_episode": {"type": "integer", "description": "起始集数（本批次从第几集开始编号）"}
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
        "model_config": {"temperature": 0.7, "max_tokens": 100000}
    },
    {
        "name": "breakdown_aligner",
        "display_name": "剧情拆解质量校验",
        "description": "基于改编方法论对剧情拆解进行8维度质量检查，确保拆解符合方法论标准",
        "category": "breakdown",
        "is_template_based": True,
        "system_prompt": "你是严格的剧情拆解质量校验员，输出必须是 JSON，不要解释，不要添加额外文字。",
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
        "model_config": {"temperature": 0.3, "max_tokens": 100000}
    },
    {
        "name": "webtoon_script",
        "display_name": "单集剧本创作",
        "description": "基于剧情点生成单集漫剧剧本，包含场景、动作、对话、特效标注",
        "category": "script",
        "is_template_based": True,
        "prompt_template": """你是一名资深的网文改编漫剧编剧。请根据以下剧情点和方法论，创作单集剧本。

### 改编方法论
{adapt_method}

### 本集剧情点
{plot_points}

### 原文参考
{chapters_text}

### 集数信息
第 {episode_number} 集

### 剧本格式要求
1. 场景标注：※ 场景名称（时间）
2. 动作描写：△ 动作描述
3. 对话格式：角色名："对话内容"
4. 特效标注：【特效类型】描述
5. 内心独白：【独白】内容
6. 结尾必须：【卡黑】

### 单集结构（起承转钩四段式）
- 【起】开场冲突（100-150字）：3秒抓眼球，瞬间进入冲突
- 【承】推进发展（150-200字）：展示过程，为爽点铺垫
- 【转】反转高潮（200-250字）：核心爽点爆发，情绪达到峰值
- 【钩】悬念结尾（100-150字）：强制卡黑，吸引观众看下一集

### 输出要求
请以 JSON 格式返回剧本：
{{
  "episode_number": {episode_number},
  "title": "本集标题",
  "word_count": 字数统计,
  "structure": {{
    "opening": {{
      "content": "【起】部分内容",
      "word_count": 字数
    }},
    "development": {{
      "content": "【承】部分内容",
      "word_count": 字数
    }},
    "climax": {{
      "content": "【转】部分内容",
      "word_count": 字数
    }},
    "hook": {{
      "content": "【钩】部分内容",
      "word_count": 字数
    }}
  }},
  "full_script": "完整剧本文本",
  "scenes": ["场景1", "场景2"],
  "characters": ["角色1", "角色2"],
  "hook_type": "结尾悬念类型"
}}

请只返回 JSON 对象，不要包含其他文字。""",
        "input_schema": {
            "plot_points": {"type": "string", "description": "JSON格式的本集剧情点"},
            "chapters_text": {"type": "string", "description": "原文参考"},
            "adapt_method": {"type": "string", "description": "改编方法论"},
            "episode_number": {"type": "integer", "description": "集数"}
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "episode_number": {"type": "integer"},
                "title": {"type": "string"},
                "word_count": {"type": "integer"},
                "structure": {"type": "object"},
                "full_script": {"type": "string"},
                "scenes": {"type": "array"},
                "characters": {"type": "array"},
                "hook_type": {"type": "string"}
            }
        },
        "model_config": {"temperature": 0.7, "max_tokens": 100000}
    },
    {
        "name": "webtoon_aligner",
        "display_name": "剧本质检",
        "description": "检查单集剧本是否符合漫剧改编标准，包括字数、结构、节奏、视觉化等",
        "category": "qa",
        "is_template_based": True,
        "prompt_template": """你是一名资深的网文改编漫剧质检专家。请对以下单集剧本进行质量检查。

### 改编方法论
{adapt_method}

### 待检查的剧本
{script}

### 原文参考
{chapters_text}

### 质检维度
1. 字数范围（20%）：总字数是否在500-800字范围内
2. 结构完整（25%）：起承转钩四段式是否完整
3. 开场冲突（15%）：是否3秒进冲突，无铺垫
4. 悬念结尾（20%）：是否有【卡黑】，悬念是否足够
5. 视觉化（10%）：是否无大段心理描写，可转化为画面
6. 对话质量（10%）：对话是否简短有力

### 输出格式
请以 JSON 格式返回质检报告：
{{
  "status": "PASS 或 FAIL",
  "score": 总分(0-100),
  "dimensions": {{
    "word_count": {{"score": 0-10, "issues": [], "actual": 实际字数}},
    "structure": {{"score": 0-10, "issues": []}},
    "opening": {{"score": 0-10, "issues": []}},
    "hook_ending": {{"score": 0-10, "issues": []}},
    "visualization": {{"score": 0-10, "issues": []}},
    "dialogue": {{"score": 0-10, "issues": []}}
  }},
  "fix_instructions": [
    {{
      "target": "修改目标",
      "type": "问题类型",
      "issue": "问题描述",
      "suggestion": "修正建议"
    }}
  ],
  "summary": "整体评价"
}}

请只返回 JSON 对象，不要包含其他文字。""",
        "input_schema": {
            "script": {"type": "string", "description": "JSON格式的剧本"},
            "chapters_text": {"type": "string", "description": "原文参考"},
            "adapt_method": {"type": "string", "description": "改编方法论"}
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "score": {"type": "integer"},
                "dimensions": {"type": "object"},
                "fix_instructions": {"type": "array"},
                "summary": {"type": "string"}
            }
        },
        "model_config": {"temperature": 0.3, "max_tokens": 100000}
    }
]


# ==================== 内置 Agents 定义 ====================

BUILTIN_AGENTS = [
    {
        "name": "breakdown_agent",
        "display_name": "剧情拆解 Agent",
        "description": "智能剧情拆解：拆解 → 质检 → 自动修正循环，直到质量达标",
        "category": "breakdown",
        "workflow": {
            "type": "loop",
            "max_iterations": 3,
            "exit_condition": "qa_result.status == 'PASS' or qa_result.score >= 70",
            "steps": [
                {
                    "id": "breakdown",
                    "skill": "webtoon_breakdown",
                    "inputs": {
                        "chapters_text": "${context.chapters_text}",
                        "adapt_method": "${context.adapt_method}",
                        "output_style": "${context.output_style}",
                        "template": "${context.template}",
                        "example": "${context.example}",
                        "qa_feedback": "",
                        "start_chapter": "${context.start_chapter}",
                        "end_chapter": "${context.end_chapter}",
                        "start_episode": "${context.start_episode}"
                    },
                    "output_key": "plot_points",
                    "on_fail": "stop",
                    "max_retries": 1
                },
                {
                    "id": "qa",
                    "skill": "breakdown_aligner",
                    "inputs": {
                        "plot_points": "${plot_points}",
                        "chapters_text": "${context.chapters_text}",
                        "adapt_method": "${context.adapt_method}"
                    },
                    "output_key": "qa_result",
                    "on_fail": "skip",
                    "max_retries": 0
                },
                {
                    "id": "breakdown_retry",
                    "skill": "webtoon_breakdown",
                    "condition": "qa_result.status != 'PASS' and qa_result.score < 70",
                    "inputs": {
                        "chapters_text": "${context.chapters_text}",
                        "adapt_method": "${context.adapt_method}",
                        "output_style": "${context.output_style}",
                        "template": "${context.template}",
                        "example": "${context.example}",
                        "qa_feedback": "问题列表: ${qa_result.issues}\n修复指引: ${qa_result.fix_instructions}",
                        "start_chapter": "${context.start_chapter}",
                        "end_chapter": "${context.end_chapter}",
                        "start_episode": "${context.start_episode}"
                    },
                    "output_key": "plot_points",
                    "on_fail": "skip",
                    "max_retries": 0
                },
                {
                    "id": "qa_retry",
                    "skill": "breakdown_aligner",
                    "condition": "qa_result.status != 'PASS' and qa_result.score < 70",
                    "inputs": {
                        "plot_points": "${plot_points}",
                        "chapters_text": "${context.chapters_text}",
                        "adapt_method": "${context.adapt_method}"
                    },
                    "output_key": "qa_result",
                    "on_fail": "skip",
                    "max_retries": 0
                }
            ]
        }
    },
    {
        "name": "script_agent",
        "display_name": "剧本创作 Agent",
        "description": "基于剧情点生成高质量单集剧本，支持质检和润色",
        "category": "script",
        "workflow": {
            "type": "loop",
            "max_iterations": 2,
            "exit_condition": "qa_result.status == 'PASS' or qa_result.score >= 80",
            "steps": [
                {
                    "id": "script",
                    "skill": "webtoon_script",
                    "inputs": {
                        "plot_points": "${context.plot_points}",
                        "chapters_text": "${context.chapters_text}",
                        "adapt_method": "${context.adapt_method}",
                        "episode_number": "${context.episode_number}"
                    },
                    "output_key": "script_result",
                    "on_fail": "stop",
                    "max_retries": 1
                },
                {
                    "id": "qa",
                    "skill": "webtoon_aligner",
                    "inputs": {
                        "script": "${script.script_result}",
                        "chapters_text": "${context.chapters_text}",
                        "adapt_method": "${context.adapt_method}"
                    },
                    "output_key": "qa_result",
                    "on_fail": "skip",
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
                system_prompt=skill_data.get("system_prompt"),
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
            # 更新已存在的内置 Skill
            existing_skill.display_name = skill_data["display_name"]
            existing_skill.description = skill_data["description"]
            existing_skill.system_prompt = skill_data.get("system_prompt")
            existing_skill.prompt_template = skill_data["prompt_template"]
            existing_skill.input_schema = skill_data["input_schema"]
            existing_skill.output_schema = skill_data["output_schema"]
            existing_skill.model_config = skill_data["model_config"]
            print(f"  ↻ 更新 Skill: {skill_data['display_name']}")

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
            # 更新已存在的内置 Agent
            existing_agent.display_name = agent_data["display_name"]
            existing_agent.description = agent_data["description"]
            existing_agent.workflow = agent_data["workflow"]
            print(f"  ↻ 更新 Agent: {agent_data['display_name']}")

    await db.commit()
    print(f"✓ 已初始化 {len(BUILTIN_AGENTS)} 个内置 Agents")

    print("\n✅ 简化系统初始化完成！")

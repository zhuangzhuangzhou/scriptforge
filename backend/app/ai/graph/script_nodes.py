from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.plot_breakdown import PlotBreakdown
from app.ai.graph.script_state import ScriptState


async def load_breakdown_node(state: ScriptState, db: AsyncSession) -> Dict[str, Any]:
    """加载Breakdown结果"""
    breakdown_id = state["breakdown_id"]

    # 从数据库加载拆解结果
    result = await db.execute(
        select(PlotBreakdown).where(PlotBreakdown.id == breakdown_id)
    )
    breakdown = result.scalar_one_or_none()

    if not breakdown:
        return {
            "errors": ["拆解结果不存在"],
            "current_step": "load_breakdown",
            "progress": 0
        }

    breakdown_data = {
        "conflicts": breakdown.conflicts,
        "plot_hooks": breakdown.plot_hooks,
        "characters": breakdown.characters,
        "scenes": breakdown.scenes,
        "emotions": breakdown.emotions
    }

    return {
        "breakdown_data": breakdown_data,
        "current_step": "load_breakdown",
        "progress": 10
    }


async def plan_episodes_node(state: ScriptState, model_adapter) -> Dict[str, Any]:
    """规划剧集结构"""
    breakdown_data = state["breakdown_data"]

    prompt = f"""基于以下剧情拆解结果，规划剧集结构。

拆解结果：
- 冲突点：{len(breakdown_data.get('conflicts', []))}个
- 剧情钩子：{len(breakdown_data.get('plot_hooks', []))}个
- 人物：{len(breakdown_data.get('characters', []))}个

请以JSON格式返回剧集规划，包含：
- episode_number: 集数
- title: 标题
- main_conflict: 主要冲突
- key_scenes: 关键场景列表
"""

    response = model_adapter.generate(prompt)

    import json
    try:
        episodes = json.loads(response)
    except:
        episodes = []

    return {
        "episodes": episodes,
        "current_step": "plan_episodes",
        "progress": 30
    }


async def generate_scenes_node(state: ScriptState, model_adapter) -> Dict[str, Any]:
    """生成场景"""
    episodes = state.get("episodes", [])
    breakdown_data = state["breakdown_data"]

    prompt = f"""基于剧集规划和拆解结果，生成详细的场景描述。

场景信息：{breakdown_data.get('scenes', [])}

请以JSON格式返回场景列表，每个场景包含：
- scene_number: 场景号
- location: 地点（内景/外景）
- time: 时间（日/夜）
- description: 场景描述
"""

    response = model_adapter.generate(prompt)

    import json
    try:
        scenes = json.loads(response)
    except:
        scenes = []

    return {
        "scenes": scenes,
        "current_step": "generate_scenes",
        "progress": 50
    }


async def write_dialogues_node(state: ScriptState, model_adapter) -> Dict[str, Any]:
    """编写对话"""
    scenes = state.get("scenes", [])
    characters = state["breakdown_data"].get("characters", [])

    prompt = f"""基于场景和人物信息，编写对话。

人物：{characters}

请以JSON格式返回对话列表，每个对话包含：
- character: 角色名
- text: 对话内容
- emotion: 情绪
"""

    response = model_adapter.generate(prompt)

    import json
    try:
        dialogues = json.loads(response)
    except:
        dialogues = []

    return {
        "dialogues": dialogues,
        "current_step": "write_dialogues",
        "progress": 70
    }


async def save_script_node(state: ScriptState, db: AsyncSession) -> Dict[str, Any]:
    """保存剧本"""
    from app.models.script import Script

    script_content = {
        "version": "1.0",
        "episodes": state.get("episodes", []),
        "scenes": state.get("scenes", []),
        "dialogues": state.get("dialogues", [])
    }

    script = Script(
        batch_id=state["batch_id"],
        project_id=state["project_id"],
        plot_breakdown_id=state["breakdown_id"],
        episode_number=1,
        title="第一集",
        content=script_content,
        word_count=0,
        scene_count=len(state.get("scenes", []))
    )

    db.add(script)
    await db.commit()

    return {
        "current_step": "save_script",
        "progress": 100
    }

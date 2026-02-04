import json
import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.chapter import Chapter
from app.ai.graph.breakdown_state import BreakdownState

logger = logging.getLogger(__name__)


async def load_chapters_node(state: BreakdownState, db: AsyncSession) -> Dict[str, Any]:
    """加载批次的章节内容"""
    batch_id = state["batch_id"]

    # 从数据库加载章节
    result = await db.execute(
        select(Chapter).where(Chapter.batch_id == batch_id).order_by(Chapter.chapter_number)
    )
    chapters = result.scalars().all()

    # 转换为字典格式
    chapters_data = [
        {
            "chapter_number": ch.chapter_number,
            "title": ch.title,
            "content": ch.content,
            "word_count": ch.word_count
        }
        for ch in chapters
    ]

    return {
        "chapters": chapters_data,
        "current_step": "load_chapters",
        "progress": 10
    }


async def extract_conflicts_node(state: BreakdownState, model_adapter) -> Dict[str, Any]:
    """提取冲突点"""
    chapters = state["chapters"]

    # 构建提示词
    chapters_text = "\n\n".join([
        f"第{ch['chapter_number']}章 {ch['title']}\n{ch['content']}"
        for ch in chapters
    ])

    prompt = f"""请分析以下小说章节，提取其中的主要冲突点。

{chapters_text}

请以JSON格式返回冲突点列表，每个冲突点包含：
- type: 冲突类型（人物冲突、内心冲突、环境冲突等）
- description: 冲突描述
- characters: 涉及的人物
- intensity: 冲突强度（1-10）
"""

    response = model_adapter.generate(prompt)

    # 解析响应（简化处理）
    try:
        conflicts = json.loads(response)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}, 原始响应: {response[:500]}")
        conflicts = []

    return {
        "conflicts": conflicts,
        "current_step": "extract_conflicts",
        "progress": 30
    }


async def identify_plot_hooks_node(state: BreakdownState, model_adapter) -> Dict[str, Any]:
    """识别剧情钩子"""
    chapters = state["chapters"]

    chapters_text = "\n\n".join([
        f"第{ch['chapter_number']}章 {ch['title']}\n{ch['content']}"
        for ch in chapters
    ])

    prompt = f"""请分析以下小说章节，识别其中的剧情钩子（吸引读者继续阅读的关键点）。

{chapters_text}

请以JSON格式返回剧情钩子列表，每个钩子包含：
- position: 位置（章节号）
- type: 类型（悬念、转折、冲突升级等）
- description: 描述
- impact: 影响力（1-10）
"""

    response = model_adapter.generate(prompt)

    try:
        plot_hooks = json.loads(response)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}, 原始响应: {response[:500]}")
        plot_hooks = []

    return {
        "plot_hooks": plot_hooks,
        "current_step": "identify_plot_hooks",
        "progress": 50
    }


async def analyze_characters_node(state: BreakdownState, model_adapter) -> Dict[str, Any]:
    """分析人物关系"""
    chapters = state["chapters"]

    chapters_text = "\n\n".join([
        f"第{ch['chapter_number']}章 {ch['title']}\n{ch['content']}"
        for ch in chapters
    ])

    prompt = f"""请分析以下小说章节中的人物及其关系。

{chapters_text}

请以JSON格式返回人物列表，每个人物包含：
- name: 姓名
- role: 角色定位（主角、配角等）
- traits: 性格特点
- relationships: 与其他人物的关系
"""

    response = model_adapter.generate(prompt)

    try:
        characters = json.loads(response)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}, 原始响应: {response[:500]}")
        characters = []

    return {
        "characters": characters,
        "current_step": "analyze_characters",
        "progress": 70
    }


async def identify_scenes_node(state: BreakdownState, model_adapter) -> Dict[str, Any]:
    """识别场景"""
    chapters = state["chapters"]

    chapters_text = "\n\n".join([
        f"第{ch['chapter_number']}章 {ch['title']}\n{ch['content']}"
        for ch in chapters
    ])

    prompt = f"""请识别以下小说章节中的主要场景。

{chapters_text}

请以JSON格式返回场景列表，每个场景包含：
- location: 地点
- time: 时间（日/夜）
- atmosphere: 氛围
- key_events: 关键事件
"""

    response = model_adapter.generate(prompt)

    try:
        scenes = json.loads(response)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}, 原始响应: {response[:500]}")
        scenes = []

    return {
        "scenes": scenes,
        "current_step": "identify_scenes",
        "progress": 85
    }


async def extract_emotions_node(state: BreakdownState, model_adapter) -> Dict[str, Any]:
    """提取情绪点"""
    chapters = state["chapters"]

    chapters_text = "\n\n".join([
        f"第{ch['chapter_number']}章 {ch['title']}\n{ch['content']}"
        for ch in chapters
    ])

    prompt = f"""请识别以下小说章节中的情绪点。

{chapters_text}

请以JSON格式返回情绪点列表，每个情绪点包含：
- position: 位置（章节号）
- emotion: 情绪类型（喜悦、悲伤、愤怒、恐惧等）
- intensity: 强度（1-10）
- trigger: 触发原因
"""

    response = model_adapter.generate(prompt)

    try:
        emotions = json.loads(response)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}, 原始响应: {response[:500]}")
        emotions = []

    return {
        "emotions": emotions,
        "current_step": "extract_emotions",
        "progress": 95
    }


async def save_breakdown_node(state: BreakdownState, db: AsyncSession) -> Dict[str, Any]:
    """保存拆解结果"""
    from app.models.plot_breakdown import PlotBreakdown

    breakdown = PlotBreakdown(
        batch_id=state["batch_id"],
        project_id=state["project_id"],
        conflicts=state.get("conflicts", []),
        plot_hooks=state.get("plot_hooks", []),
        characters=state.get("characters", []),
        scenes=state.get("scenes", []),
        emotions=state.get("emotions", []),
        consistency_status="pending"
    )

    db.add(breakdown)
    await db.commit()

    return {
        "current_step": "save_breakdown",
        "progress": 100
    }

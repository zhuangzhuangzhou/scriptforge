"""剧情拆解工作流节点

支持从用户配置加载自定义提示词，如果没有配置则使用系统默认提示词。
"""
import json
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.chapter import Chapter
from app.models.ai_resource import AIResource
from app.ai.graph.breakdown_state import BreakdownState
from app.ai.consistency_checker import ConsistencyChecker

logger = logging.getLogger(__name__)


# ==================== 默认提示词（硬编码回退） ====================

DEFAULT_PROMPTS = {
    "conflict": """请分析以下小说章节，提取其中的主要冲突点。

## 章节内容
{{chapters_text}}

## 输出要求
请以 JSON 格式返回冲突点列表，每个冲突点包含：
- type: 冲突类型（人物冲突、内心冲突、环境冲突等）
- description: 冲突描述
- characters: 涉及的人物
- intensity: 冲突强度（1-10）""",

    "character": """请分析以下小说章节中的人物及其关系。

## 章节内容
{{chapters_text}}

## 输出要求
请以 JSON 格式返回人物列表，每个人物包含：
- name: 姓名
- role: 角色定位（主角、配角等）
- traits: 性格特点
- relationships: 与其他人物的关系""",

    "scene": """请识别以下小说章节中的主要场景。

## 章节内容
{{chapters_text}}

## 输出要求
请以 JSON 格式返回场景列表，每个场景包含：
- location: 地点
- time: 时间（日/夜）
- atmosphere: 氛围
- key_events: 关键事件""",

    "emotion": """请识别以下小说章节中的情绪点。

## 章节内容
{{chapters_text}}

## 输出要求
请以 JSON 格式返回情绪点列表，每个情绪点包含：
- position: 位置（章节号）
- emotion: 情绪类型（喜悦、悲伤、愤怒、恐惧等）
- intensity: 强度（1-10）
- trigger: 触发原因""",

    "plot_hook": """请分析以下小说章节，识别其中的剧情钩子（吸引读者继续阅读的关键点）。

## 章节内容
{{chapters_text}}

## 输出要求
请以 JSON 格式返回剧情钩子列表，每个钩子包含：
- position: 位置（章节号）
- type: 类型（悬念、转折、冲突升级等）
- description: 描述
- impact: 影响力（1-10）""",
}


# ==================== 提示词加载辅助函数 ====================

async def get_prompt_template(
    step_name: str,
    prompt_config: Optional[Dict[str, Any]],
    db: AsyncSession
) -> str:
    """获取指定步骤的提示词模板

    Args:
        step_name: 步骤名称（conflict/character/scene/emotion/plot_hook）
        prompt_config: 用户提示词配置字典
        db: 数据库会话

    Returns:
        str: 提示词模板内容
    """
    # 1. 尝试从用户配置获取提示词 ID
    prompt_id = None
    if prompt_config:
        prompt_id = prompt_config.get(f"{step_name}_prompt_id")

    # 2. 如果有配置的提示词 ID，从数据库加载
    if prompt_id:
        result = await db.execute(
            select(AIResource).where(AIResource.id == prompt_id)
        )
        resource = result.scalar_one_or_none()
        if resource and resource.content:
            logger.info(f"使用自定义提示词: {resource.display_name} (step={step_name})")
            return resource.content

    # 3. 回退到默认提示词
    logger.debug(f"使用默认提示词 (step={step_name})")
    return DEFAULT_PROMPTS.get(step_name, "")


def render_prompt(template: str, chapters_text: str) -> str:
    """渲染提示词模板，替换变量

    Args:
        template: 提示词模板
        chapters_text: 章节文本内容

    Returns:
        str: 渲染后的提示词
    """
    return template.replace("{{chapters_text}}", chapters_text)


def build_chapters_text(chapters: list) -> str:
    """构建章节文本"""
    return "\n\n".join([
        f"第{ch['chapter_number']}章 {ch['title']}\n{ch['content']}"
        for ch in chapters
    ])


# ==================== 工作流节点 ====================

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


async def extract_conflicts_node(
    state: BreakdownState,
    model_adapter,
    db: AsyncSession,
    prompt_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """提取冲突点"""
    chapters = state["chapters"]
    chapters_text = build_chapters_text(chapters)

    # 获取提示词模板
    template = await get_prompt_template("conflict", prompt_config, db)
    prompt = render_prompt(template, chapters_text)

    response = model_adapter.generate(prompt)

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


async def identify_plot_hooks_node(
    state: BreakdownState,
    model_adapter,
    db: AsyncSession,
    prompt_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """识别剧情钩子"""
    chapters = state["chapters"]
    chapters_text = build_chapters_text(chapters)

    template = await get_prompt_template("plot_hook", prompt_config, db)
    prompt = render_prompt(template, chapters_text)

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


async def analyze_characters_node(
    state: BreakdownState,
    model_adapter,
    db: AsyncSession,
    prompt_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """分析人物关系"""
    chapters = state["chapters"]
    chapters_text = build_chapters_text(chapters)

    template = await get_prompt_template("character", prompt_config, db)
    prompt = render_prompt(template, chapters_text)

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


async def identify_scenes_node(
    state: BreakdownState,
    model_adapter,
    db: AsyncSession,
    prompt_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """识别场景"""
    chapters = state["chapters"]
    chapters_text = build_chapters_text(chapters)

    template = await get_prompt_template("scene", prompt_config, db)
    prompt = render_prompt(template, chapters_text)

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


async def extract_emotions_node(
    state: BreakdownState,
    model_adapter,
    db: AsyncSession,
    prompt_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """提取情绪点"""
    chapters = state["chapters"]
    chapters_text = build_chapters_text(chapters)

    template = await get_prompt_template("emotion", prompt_config, db)
    prompt = render_prompt(template, chapters_text)

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


async def consistency_check_node(state: BreakdownState, model_adapter, db: AsyncSession) -> Dict[str, Any]:
    """一致性检查"""
    project_id = state["project_id"]
    batch_id = state["batch_id"]

    # 构造检查所需的数据
    breakdown_data = {
        "conflicts": state.get("conflicts", []),
        "plot_hooks": state.get("plot_hooks", []),
        "characters": state.get("characters", []),
        "scenes": state.get("scenes", []),
        "emotions": state.get("emotions", [])
    }

    # 实例化检查器
    checker = ConsistencyChecker(model_adapter)

    # 运行全面审计
    audit_results = await checker.run_full_audit(project_id, batch_id, breakdown_data, db)

    return {
        "audit_results": audit_results,
        "overall_score": audit_results.get("overall_score", 0),
        "current_step": "consistency_check",
        "progress": 98
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
        consistency_status=state.get("audit_results", {}).get("status", "pending"),
        consistency_score=state.get("overall_score", 0),
        consistency_results=state.get("audit_results", {})
    )

    db.add(breakdown)
    await db.commit()

    return {
        "current_step": "save_breakdown",
        "progress": 100
    }

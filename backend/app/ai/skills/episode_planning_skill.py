import json
import logging
from typing import Dict, Any
from app.ai.skills.base_skill import BaseSkill

logger = logging.getLogger(__name__)


class EpisodePlanningSkill(BaseSkill):
    """剧集规划Skill"""

    def __init__(self):
        super().__init__(
            name="episode_planning",
            description="基于剧情拆解结果规划剧集结构"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行剧集规划"""
        breakdown_data = context.get("breakdown_data", {})
        model_adapter = context.get("model_adapter")

        if not model_adapter:
            raise ValueError("需要提供model_adapter")

        prompt = f"""基于以下剧情拆解结果，规划剧集结构：

冲突点：{breakdown_data.get('conflicts', [])}
剧情钩子：{breakdown_data.get('plot_hooks', [])}
人物：{breakdown_data.get('characters', [])}

以JSON格式返回：
{{
    "episodes": [
        {{
            "episode_number": 1,
            "title": "标题",
            "main_conflict": "主要冲突",
            "key_scenes": ["关键场景1", "关键场景2"]
        }}
    ]
}}
"""
        response = model_adapter.generate(prompt)

        try:
            result = json.loads(response)
            episodes = result.get("episodes", [])
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 原始响应: {response[:500]}")
            episodes = []

        return {"episodes": episodes}

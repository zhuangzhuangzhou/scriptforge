import json
import logging
from typing import Dict, Any
from app.ai.skills.base_skill import BaseSkill

logger = logging.getLogger(__name__)


class SceneGenerationSkill(BaseSkill):
    """场景生成Skill"""

    def __init__(self):
        super().__init__(
            name="scene_generation",
            description="基于剧集规划和拆解结果生成场景"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行场景生成"""
        breakdown_data = context.get("breakdown_data", {})
        episodes = context.get("episodes", [])
        model_adapter = context.get("model_adapter")

        if not model_adapter:
            raise ValueError("需要提供model_adapter")

        prompt = f"""基于剧集规划和拆解结果，生成详细的场景描述。

剧集规划：{episodes}
场景信息：{breakdown_data.get('scenes', [])}

请以JSON格式返回场景列表，每个场景包含：
- scene_number: 场景号
- location: 地点（内景/外景）
- time: 时间（日/夜）
- description: 场景描述
"""

        response = model_adapter.generate(prompt)

        try:
            result = json.loads(response)
            scenes = result.get("scenes", result)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 原始响应: {response[:500]}")
            scenes = []

        return {"scenes": scenes}

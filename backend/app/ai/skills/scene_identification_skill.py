import json
import logging
from typing import Dict, Any
from app.ai.skills.base_skill import BaseSkill

logger = logging.getLogger(__name__)


class SceneIdentificationSkill(BaseSkill):
    """场景识别Skill"""

    def __init__(self):
        super().__init__(
            name="scene_identification",
            description="识别章节中的场景，包括地点、时间、氛围等"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行场景识别"""
        chapters = context.get("chapters", [])
        model_adapter = context.get("model_adapter")

        if not model_adapter:
            raise ValueError("需要提供model_adapter")

        scenes = []
        for chapter in chapters:
            prompt = f"""请识别以下章节中的场景：

{chapter.get('content', '')}

以JSON格式返回：
{{
    "scenes": [
        {{
            "location": "地点描述",
            "time": "时间（日/夜）",
            "atmosphere": "氛围描述",
            "key_events": ["关键事件"]
        }}
    ]
}}
"""
            response = model_adapter.generate(prompt)

            try:
                result = json.loads(response)
                scenes.extend(result.get("scenes", []))
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}, 原始响应: {response[:500]}")

        return {"scenes": scenes}

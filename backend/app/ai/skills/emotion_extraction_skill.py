import json
import logging
from typing import Dict, Any
from app.ai.skills.base_skill import BaseSkill

logger = logging.getLogger(__name__)


class EmotionExtractionSkill(BaseSkill):
    """情绪点提取Skill"""

    def __init__(self):
        super().__init__(
            name="emotion_extraction",
            description="提取章节中的情绪点，分析情感起伏"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行情绪点提取"""
        chapters = context.get("chapters", [])
        model_adapter = context.get("model_adapter")

        if not model_adapter:
            raise ValueError("需要提供model_adapter")

        emotions = []
        for chapter in chapters:
            prompt = f"""请提取以下章节中的情绪点：

{chapter.get('content', '')}

以JSON格式返回：
{{
    "emotions": [
        {{
            "type": "喜/怒/哀/乐/惊/恐",
            "intensity": "高/中/低",
            "trigger": "触发原因",
            "character": "相关人物"
        }}
    ]
}}
"""
            response = model_adapter.generate(prompt)

            try:
                result = json.loads(response)
                emotions.extend(result.get("emotions", []))
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}, 原始响应: {response[:500]}")

        return {"emotions": emotions}

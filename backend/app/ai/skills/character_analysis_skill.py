from typing import Dict, Any
from app.ai.skills.base_skill import BaseSkill


class CharacterAnalysisSkill(BaseSkill):
    """人物分析Skill"""

    def __init__(self):
        super().__init__(
            name="character_analysis",
            description="分析章节中的人物关系、性格特点和发展轨迹"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行人物分析"""
        chapters = context.get("chapters", [])
        model_adapter = context.get("model_adapter")

        if not model_adapter:
            raise ValueError("需要提供model_adapter")

        characters = []
        for chapter in chapters:
            prompt = f"""请分析以下章节中的人物：

{chapter.get('content', '')}

以JSON格式返回：
{{
    "characters": [
        {{
            "name": "人物名",
            "role": "主角/配角/反派",
            "personality": "性格特点",
            "relationships": ["与其他人物的关系"]
        }}
    ]
}}
"""
            response = model_adapter.generate(prompt)

            import json
            try:
                result = json.loads(response)
                characters.extend(result.get("characters", []))
            except:
                pass

        return {"characters": characters}

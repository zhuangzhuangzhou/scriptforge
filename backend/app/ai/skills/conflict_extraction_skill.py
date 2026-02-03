from typing import Dict, Any
from app.ai.skills.base_skill import BaseSkill


class ConflictExtractionSkill(BaseSkill):
    """冲突点提取Skill"""

    def __init__(self):
        super().__init__(
            name="conflict_extraction",
            description="从章节内容中提取冲突点"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行冲突点提取"""
        chapters = context.get("chapters", [])
        model_adapter = context.get("model_adapter")

        if not model_adapter:
            raise ValueError("需要提供model_adapter")

        conflicts = []
        for chapter in chapters:
            prompt = f"""请从以下章节中提取冲突点：

{chapter.get('content', '')}

以JSON格式返回：
{{
    "conflicts": [
        {{"type": "人物冲突", "description": "描述"}},
        {{"type": "内心冲突", "description": "描述"}}
    ]
}}
"""
            response = model_adapter.generate(prompt)

            import json
            try:
                result = json.loads(response)
                conflicts.extend(result.get("conflicts", []))
            except:
                pass

        return {"conflicts": conflicts}

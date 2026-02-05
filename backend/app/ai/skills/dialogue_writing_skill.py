import json
import logging
from typing import Dict, Any
from app.ai.skills.base_skill import BaseSkill

logger = logging.getLogger(__name__)


class DialogueWritingSkill(BaseSkill):
    """对话生成Skill"""

    def __init__(self):
        super().__init__(
            name="dialogue_writing",
            description="基于场景与人物信息生成对话"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行对话生成"""
        scenes = context.get("scenes", [])
        breakdown_data = context.get("breakdown_data", {})
        characters = breakdown_data.get("characters", [])
        model_adapter = context.get("model_adapter")

        if not model_adapter:
            raise ValueError("需要提供model_adapter")

        prompt = f"""基于场景和人物信息，编写对话。

人物：{characters}
场景：{scenes}

请以JSON格式返回对话列表，每个对话包含：
- character: 角色名
- text: 对话内容
- emotion: 情绪
"""

        response = model_adapter.generate(prompt)

        try:
            result = json.loads(response)
            dialogues = result.get("dialogues", result)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 原始响应: {response[:500]}")
            dialogues = []

        return {"dialogues": dialogues}

import json
import logging
from typing import Dict, Any
from app.ai.skills.base_skill import BaseSkill

logger = logging.getLogger(__name__)


class PlotHookSkill(BaseSkill):
    """剧情钩子识别Skill"""

    def __init__(self):
        super().__init__(
            name="plot_hook_identification",
            description="识别章节中的剧情钩子，吸引观众继续观看"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行剧情钩子识别"""
        chapters = context.get("chapters", [])
        model_adapter = context.get("model_adapter")

        if not model_adapter:
            raise ValueError("需要提供model_adapter")

        plot_hooks = []
        for chapter in chapters:
            prompt = f"""请从以下章节中识别剧情钩子：

{chapter.get('content', '')}

剧情钩子是指能够吸引观众继续观看的悬念、转折或高潮点。

以JSON格式返回：
{{
    "plot_hooks": [
        {{"position": "章节开头/中间/结尾", "description": "描述", "intensity": "高/中/低"}}
    ]
}}
"""
            response = model_adapter.generate(prompt)

            try:
                result = json.loads(response)
                plot_hooks.extend(result.get("plot_hooks", []))
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}, 原始响应: {response[:500]}")

        return {"plot_hooks": plot_hooks}

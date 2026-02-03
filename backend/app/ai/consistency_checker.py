from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.plot_breakdown import PlotBreakdown
from app.models.consistency_check import ConsistencyCheck


class ConsistencyChecker:
    """一致性检查器"""

    def __init__(self, model_adapter):
        self.model_adapter = model_adapter

    async def check_logic_consistency(self, breakdown_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查逻辑一致性"""
        conflicts = breakdown_data.get('conflicts', [])
        plot_hooks = breakdown_data.get('plot_hooks', [])

        prompt = f"""请检查以下剧情拆解的逻辑一致性：

冲突点：{conflicts}
剧情钩子：{plot_hooks}

请分析：
1. 冲突点之间是否存在逻辑矛盾
2. 剧情钩子是否合理衔接
3. 是否存在逻辑漏洞

以JSON格式返回检查结果：
{{
    "status": "passed/failed",
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"]
}}
"""

        response = self.model_adapter.generate(prompt)

        import json
        try:
            result = json.loads(response)
        except:
            result = {"status": "failed", "issues": ["解析失败"], "suggestions": []}

        return result

    async def check_character_consistency(self, breakdown_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查人物一致性"""
        characters = breakdown_data.get('characters', [])

        prompt = f"""请检查以下人物设定的一致性：

人物信息：{characters}

请分析：
1. 人物性格是否前后一致
2. 人物关系是否合理
3. 人物行为是否符合设定

以JSON格式返回检查结果：
{{
    "status": "passed/failed",
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"]
}}
"""

        response = self.model_adapter.generate(prompt)

        import json
        try:
            result = json.loads(response)
        except:
            result = {"status": "failed", "issues": ["解析失败"], "suggestions": []}

        return result

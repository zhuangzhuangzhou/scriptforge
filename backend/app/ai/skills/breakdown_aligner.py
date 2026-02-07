import json
import logging
from typing import Dict, Any, List
from app.ai.skills.base_skill import BaseSkill

logger = logging.getLogger(__name__)

class BreakdownAlignerSkill(BaseSkill):
    """
    剧情拆解对齐器 (Aligner Skill)
    用于根据指定的改编方法论 (Adapt Method) 审核剧情拆解结果的质量与一致性。
    """

    def __init__(self):
        super().__init__(
            name="breakdown_aligner",
            description="审核剧情拆解结果是否符合改编方法论要求"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行对齐审核

        Args:
            context: 包含以下字段:
                - chapters: 章节原始内容 (List[Dict])
                - breakdown_data: 待审核的拆解结果 (Dict)
                - adapt_method: 改编方法论配置 (Dict)
                - model_adapter: AI 模型适配器
        """
        chapters = context.get("chapters", [])
        breakdown_data = context.get("breakdown_data", {})
        adapt_method = context.get("adapt_method", {})
        model_adapter = context.get("model_adapter")

        if not model_adapter:
            raise ValueError("需要提供 model_adapter")

        if not adapt_method:
            logger.warning("未提供 adapt_method，将使用默认审核逻辑")

        # 构建审核 Prompt
        method_desc = adapt_method.get("description", "标准网文适配漫画原则")
        rules = adapt_method.get("rules", [])
        rules_text = "\n".join([f"- {r}" for r in rules]) if rules else "确保内容连贯，冲突明显。"

        # 将章节内容合并为上下文
        chapters_text = "\n\n".join([
            f"第{c.get('number', i+1)}章: {c.get('title', '')}\n{c.get('content', '')}"
            for i, c in enumerate(chapters)
        ])

        prompt = f"""你是一名资深的漫改编辑，负责审核剧情拆解结果是否符合《{method_desc}》的要求。

### 审核准则
{rules_text}

### 原始章节内容
{chapters_text}

### 待审核的剧情拆解结果 (JSON)
{json.dumps(breakdown_data, ensure_ascii=False, indent=2)}

### 任务要求
请根据上述准则对拆解结果进行质量检查，重点关注：
1. 冲突点是否被完整捕捉。
2. 钩子 (Hooks) 是否设置合理。
3. 节奏是否符合漫画改编的需求。
4. 情感曲线是否平滑。

### 输出格式 (JSON)
{{
    "status": "PASS 或 FAIL",
    "score": 0-100的整数分,
    "issues": ["问题1", "问题2"],
    "suggestions": ["改进建议1", "改进建议2"]
}}
"""

        response = await model_adapter.generate_async(prompt)

        try:
            # 尝试提取和解析 JSON
            # 某些模型可能会返回包含在 Markdown 代码块中的 JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            result = json.loads(response)
            return {
                "qa_status": result.get("status", "FAIL"),
                "qa_score": result.get("score", 0),
                "qa_report": result
            }
        except Exception as e:
            logger.error(f"Aligner 响应解析失败: {e}, 原始响应: {response[:500]}")
            return {
                "qa_status": "ERROR",
                "qa_score": 0,
                "qa_report": {"error": str(e), "raw_response": response}
            }

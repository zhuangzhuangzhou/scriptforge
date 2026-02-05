import json
import logging
import inspect
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.plot_breakdown import PlotBreakdown
from app.models.consistency_check import ConsistencyCheck

logger = logging.getLogger(__name__)


class ConsistencyChecker:
    """一致性检查器"""

    def __init__(self, model_adapter):
        self.model_adapter = model_adapter

    async def _generate(self, prompt: str):
        """兼容同步/异步的模型生成"""
        result = self.model_adapter.generate(prompt)
        if inspect.isawaitable(result):
            return await result
        return result

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
    "score": 0-100 (整数评分),
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"]
}}
"""

        try:
            response = await self._generate(prompt)
            result = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in check_logic_consistency: {e}")
            result = {"status": "failed", "score": 0, "issues": ["返回格式解析失败"], "suggestions": []}
        except Exception as e:
            logger.error(f"Error in check_logic_consistency: {e}")
            result = {"status": "failed", "score": 0, "issues": [str(e)], "suggestions": []}

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
    "score": 0-100 (整数评分),
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"]
}}
"""

        try:
            response = await self._generate(prompt)
            result = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in check_character_consistency: {e}")
            result = {"status": "failed", "score": 0, "issues": ["返回格式解析失败"], "suggestions": []}
        except Exception as e:
            logger.error(f"Error in check_character_consistency: {e}")
            result = {"status": "failed", "score": 0, "issues": [str(e)], "suggestions": []}

        return result

    async def check_timeline_consistency(self, breakdown_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查时间线一致性"""
        # 假设 breakdown_data 中包含 timeline 或 scenes 信息
        timeline = breakdown_data.get('timeline', [])
        scenes = breakdown_data.get('scenes', [])

        content_to_check = f"时间线设定: {timeline}\n场景列表: {scenes}"

        prompt = f"""请检查以下剧本的时间线一致性：

{content_to_check}

请分析：
1. 故事发生的时间顺序是否冲突
2. 场景之间的时间流逝是否合理
3. 是否存在时间回溯或跳跃导致的逻辑错误

以JSON格式返回检查结果：
{{
    "status": "passed/failed",
    "score": 0-100 (整数评分),
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"]
}}
"""
        try:
            response = await self._generate(prompt)
            result = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in check_timeline_consistency: {e}")
            result = {"status": "failed", "score": 0, "issues": ["返回格式解析失败"], "suggestions": []}
        except Exception as e:
            logger.error(f"Error in check_timeline_consistency: {e}")
            result = {"status": "failed", "score": 0, "issues": [str(e)], "suggestions": []}

        return result

    async def check_scene_continuity(self, breakdown_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查场景连续性"""
        scenes = breakdown_data.get('scenes', [])

        prompt = f"""请检查以下剧本场景的连续性：

场景信息：{scenes}

请分析：
1. 场景切换是否流畅
2. 人物位置在连续场景中是否合理
3. 道具状态在场景间是否保持一致

以JSON格式返回检查结果：
{{
    "status": "passed/failed",
    "score": 0-100 (整数评分),
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"]
}}
"""
        try:
            response = await self._generate(prompt)
            result = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in check_scene_continuity: {e}")
            result = {"status": "failed", "score": 0, "issues": ["返回格式解析失败"], "suggestions": []}
        except Exception as e:
            logger.error(f"Error in check_scene_continuity: {e}")
            result = {"status": "failed", "score": 0, "issues": [str(e)], "suggestions": []}

        return result

    async def check_dialogue_style(self, breakdown_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查对话风格一致性"""
        characters = breakdown_data.get('characters', [])
        scenes = breakdown_data.get('scenes', [])

        prompt = f"""请检查剧本角色的对话风格一致性：

人物设定：{characters}
场景与对话：{scenes}

请分析：
1. 同一个角色在不同场景中的口吻是否一致
2. 角色的语言风格是否符合其设定（如年龄、职业、性格）
3. 是否存在突然的语言风格突变

以JSON格式返回检查结果：
{{
    "status": "passed/failed",
    "score": 0-100 (整数评分),
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"]
}}
"""
        try:
            response = await self._generate(prompt)
            result = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in check_dialogue_style: {e}")
            result = {"status": "failed", "score": 0, "issues": ["返回格式解析失败"], "suggestions": []}
        except Exception as e:
            logger.error(f"Error in check_dialogue_style: {e}")
            result = {"status": "failed", "score": 0, "issues": [str(e)], "suggestions": []}

        return result

    async def run_full_audit(self, project_id: str, batch_id: str, breakdown_data: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
        """运行全面审计并保存结果"""

        # 1. 运行所有检查
        results = {}

        results['logic'] = await self.check_logic_consistency(breakdown_data)
        results['character'] = await self.check_character_consistency(breakdown_data)
        results['timeline'] = await self.check_timeline_consistency(breakdown_data)
        results['scene'] = await self.check_scene_continuity(breakdown_data)
        results['dialogue'] = await self.check_dialogue_style(breakdown_data)

        # 2. 计算综合得分
        total_score = 0
        count = 0
        for key, res in results.items():
            score = res.get('score', 0)
            # 确保 score 是数字
            if isinstance(score, (int, float)):
                total_score += score
            count += 1

        avg_score = int(total_score / count) if count > 0 else 0

        final_status = "passed" if avg_score >= 60 else "failed"

        # 3. 构造综合结果
        full_result_data = {
            "overall_score": avg_score,
            "status": final_status,
            "details": results
        }

        # 4. 保存到数据库
        check_record = ConsistencyCheck(
            project_id=project_id,
            batch_id=batch_id,
            check_type="full_audit",
            status="completed",
            results=full_result_data
        )

        db.add(check_record)
        await db.commit()
        await db.refresh(check_record)

        return full_result_data

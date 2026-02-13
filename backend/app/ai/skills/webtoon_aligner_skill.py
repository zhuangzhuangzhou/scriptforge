import json
import logging
from typing import Dict, Any, List
from app.ai.skills.base_skill import BaseSkill

logger = logging.getLogger(__name__)

class WebtoonAlignerSkill(BaseSkill):
    """
    网文改编漫剧一致性校验员 (Webtoon Aligner Skill)
    在每一批次创作完成后自动触发，以 plot_breakdown.md 为核心基准，
    结合 adapt-method.md 改编方法论，逐集检查剧情还原、剧情使用、
    跨集连贯、节奏控制、视觉化风格、格式规范、悬念设置等维度的一致性。
    """

    def __init__(self):
        super().__init__(
            name="webtoon_aligner",
            description="检查网文改编漫剧内容的一致性和质量，确保符合改编方法论和剧情拆解要求"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行一致性检查

        Args:
            context: 包含以下字段:
                - batch_number: 批次号 (int)
                - episode_range: 集数范围 (tuple[int, int])，如 (1, 5)
                - plot_breakdown: 剧情拆解数据 (Dict)
                - adapt_method: 改编方法论配置 (Dict)
                - episodes_content: 待检查的剧本内容 (List[Dict])
                - previous_episode: 前一集内容 (Dict, optional)
                - model_adapter: AI 模型适配器
        """
        batch_number = context.get("batch_number", 1)
        episode_range = context.get("episode_range", (1, 1))
        plot_breakdown = context.get("plot_breakdown", {})
        adapt_method = context.get("adapt_method", {})
        episodes_content = context.get("episodes_content", [])
        previous_episode = context.get("previous_episode")
        model_adapter = context.get("model_adapter")

        if not model_adapter:
            raise ValueError("需要提供 model_adapter")

        if not plot_breakdown:
            logger.warning("未提供 plot_breakdown，检查质量可能受影响")

        if not adapt_method:
            logger.warning("未提供 adapt_method，将使用默认检查逻辑")

        # 构建检查 Prompt
        prompt = self._build_check_prompt(
            batch_number=batch_number,
            episode_range=episode_range,
            plot_breakdown=plot_breakdown,
            adapt_method=adapt_method,
            episodes_content=episodes_content,
            previous_episode=previous_episode
        )

        # 调用模型生成检查结果
        response = await model_adapter.generate_async(
            prompt=prompt,
            temperature=0.3,  # 低温度确保稳定输出
            max_tokens=100000
        )

        try:
            # 尝试提取和解析 JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            result = json.loads(response)

            return {
                "check_status": result.get("status", "FAIL"),
                "check_score": result.get("score", 0),
                "check_report": result,
                "batch_number": batch_number,
                "episode_range": episode_range
            }
        except Exception as e:
            logger.error(f"Webtoon Aligner 响应解析失败: {e}, 原始响应: {response[:500]}")
            return {
                "check_status": "ERROR",
                "check_score": 0,
                "check_report": {"error": str(e), "raw_response": response},
                "batch_number": batch_number,
                "episode_range": episode_range
            }

    def _build_check_prompt(
        self,
        batch_number: int,
        episode_range: tuple,
        plot_breakdown: Dict[str, Any],
        adapt_method: Dict[str, Any],
        episodes_content: List[Dict[str, Any]],
        previous_episode: Dict[str, Any] = None
    ) -> str:
        """构建一致性检查 Prompt"""

        start_ep, end_ep = episode_range

        # 提取改编方法论规则
        method_desc = adapt_method.get("description", "标准网文适配漫画原则")
        rules = adapt_method.get("rules", [])
        rules_text = "\n".join([f"- {r}" for r in rules]) if rules else "确保内容连贯，冲突明显。"

        # 提取剧情拆解信息
        plot_points = plot_breakdown.get("plot_points", [])
        plot_points_text = self._format_plot_points(plot_points)

        # 格式化待检查的剧本内容
        episodes_text = self._format_episodes(episodes_content)

        # 格式化前一集内容（如果存在）
        previous_episode_text = ""
        if previous_episode and start_ep > 1:
            previous_episode_text = f"""
### 前一集内容（第{start_ep-1}集）
用于检查跨集连贯性：
{previous_episode.get('content', '')}
"""

        prompt = f"""你是一名资深的漫改编辑和一致性校验员，负责检查网文改编漫剧的一致性和质量。

### 检查任务
第 {batch_number} 批次（第 {start_ep}-{end_ep} 集）的一致性检查。

### 核心基准文档

#### 1. 剧情拆解（plot_breakdown.md）- 最重要的基准
{plot_points_text}

#### 2. 改编方法论（adapt-method.md）
**方法论描述**: {method_desc}

**核心规则**:
{rules_text}

{previous_episode_text}

### 待检查的剧本内容
{episodes_text}

### 检查标准（11 个维度）

请严格按照以下 11 个维度进行检查：

**【维度1】剧情点还原一致性**
- 每集是否按照 plot_breakdown 中的剧情点创作
- 剧情点的场景、角色、事件是否在剧本中体现
- 是否遗漏了应该出现的剧情点
- 是否添加了 plot_breakdown 中没有的重大情节

**【维度2】剧情点使用一致性**
- 该集使用的剧情点编号是否正确
- 是否使用了其他集的剧情点
- 是否重复使用了已在前面集数使用过的剧情点
- 剧情点的情绪钩子类型是否在剧本中体现

**【维度3】跨集连贯性**（仅当第{start_ep}集且{start_ep} > 1时检查）
- 第{start_ep}集开场是否自然接续第{start_ep-1}集结尾的悬念
- 人物状态是否连续
- 场景转换是否合理
- 时间线是否连贯
- 是否有情节断层或突兀感

**【维度4】节奏控制一致性**
- 每集字数是否在 500-800 字范围内
- 场景数是否为 1-3 个（不能超过 3 个）
- 起承转钩结构是否清晰
- 是否 3 秒进冲突，每 30 秒有推进
- 是否有过长的单一画面或拖沓情节

**【维度5】视觉化风格一致性**
- 是否使用了视觉描述符号（※场景、△动作、【特效】等）
- 对话是否简短有力（不超过 20 字/句）
- 动作描写是否具体可视
- 是否有心理描写过多的问题
- 是否有环境描写、铺垫等漫剧禁忌内容

**【维度6】人物行为一致性**
- 人物性格是否前后统一
- 人物能力是否前后一致
- 对话风格是否符合人设
- 人物关系是否符合设定

**【维度7】时间线逻辑一致性**
- 事件发生顺序是否符合逻辑
- 时间跨度是否合理
- 人物位置移动是否合理
- 是否出现时间线矛盾

**【维度8】格式规范一致性**
- 是否有集标题（# 第X集：<集标题>）
- 是否使用 ※ 标注场景
- 是否使用 --- 分隔场景
- 是否有视觉描述符号说明
- 是否有 [注] 说明

**【维度9】悬念设置一致性**
- 每集结尾是否有【卡黑】标记（必须）
- 悬念是否足够吸引人
- 是否有平淡收尾的禁忌
- 悬念设置是否自然，不生硬

**【维度10】类型特性一致性**
根据小说类型检查是否符合特殊要求：
- 玄幻/武侠：境界体系、战力数值、打脸节奏
- 都市/现代：身份对比、打脸方式
- 言情/古言：误会、虐点、甜宠
- 悬疑/推理：线索、反转
- 科幻/末世：危机、异能展示
- 重生：先知优势、前世今生对比、复仇节奏

**【维度11】改编禁忌检查**
- 节奏禁忌：开场慢、铺垫多、过渡长、节奏拖沓
- 内容禁忌：心理描写过多、环境描写、过度文言文、网文万能句
- 结构禁忌：超过 3 个场景、单集超过 800 字或少于 500 字、无【卡黑】
- 改编禁忌：过度忠于原著、保留小说铺垫、心理活动未转化
- 视觉禁忌：无画面感、对话超过 20 字、无视觉符号

### 输出格式（必须严格遵循 JSON 格式）

{{
    "status": "PASS 或 FAIL",
    "score": 0-100的整数分,
    "dimensions": {{
        "plot_restoration": {{"pass": true/false, "issues": ["问题1", "问题2"]}},
        "plot_usage": {{"pass": true/false, "issues": []}},
        "cross_episode_continuity": {{"pass": true/false, "issues": []}},
        "rhythm_control": {{"pass": true/false, "issues": []}},
        "visual_style": {{"pass": true/false, "issues": []}},
        "character_consistency": {{"pass": true/false, "issues": []}},
        "timeline_logic": {{"pass": true/false, "issues": []}},
        "format_compliance": {{"pass": true/false, "issues": []}},
        "suspense_setting": {{"pass": true/false, "issues": []}},
        "genre_characteristics": {{"pass": true/false, "issues": []}},
        "adaptation_taboos": {{"pass": true/false, "issues": []}}
    }},
    "issues": [
        {{
            "dimension": "维度名称",
            "episode": 集数,
            "severity": "critical/warning",
            "description": "问题描述",
            "conflict": "冲突内容对比",
            "suggestion": "修改建议"
        }}
    ],
    "summary": "总体评价"
}}

### 检查要求
1. 严格基于 plot_breakdown 和 adapt_method 作为核心基准
2. 问题描述具体到集数和位置
3. 必须指出冲突的具体内容对比
4. 修改建议明确可执行
5. 只有完全符合标准才能输出 PASS 状态
6. 剧情点还原和使用是重中之重
7. 跨集连贯性是确保批次间衔接的关键

请开始检查。
"""
        return prompt

    def _format_plot_points(self, plot_points: List[Dict[str, Any]]) -> str:
        """格式化剧情点信息"""
        if not plot_points:
            return "（未提供剧情拆解数据）"

        formatted = []
        for i, point in enumerate(plot_points, 1):
            episode = point.get("episode", "未知")
            title = point.get("title", "")
            content = point.get("content", "")
            hook_type = point.get("hook_type", "")

            formatted.append(f"""
【剧情{i}】（第{episode}集）
标题: {title}
内容: {content}
情绪钩子: {hook_type}
""")

        return "\n".join(formatted)

    def _format_episodes(self, episodes: List[Dict[str, Any]]) -> str:
        """格式化剧本内容"""
        if not episodes:
            return "（未提供剧本内容）"

        formatted = []
        for episode in episodes:
            episode_num = episode.get("episode_number", "未知")
            title = episode.get("title", "")
            content = episode.get("content", "")

            formatted.append(f"""
---
## 第 {episode_num} 集：{title}

{content}
---
""")

        return "\n".join(formatted)

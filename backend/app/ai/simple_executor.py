"""简化的 Skill 和 Agent 执行引擎

核心理念：
- Skill = Prompt 模板 + 输入/输出定义
- 执行 = 模板填充 + 模型调用 + JSON 解析
- Agent = 工作流编排 + 循环控制 + 条件执行

模块结构：
1. 正则表达式定义（用于解析 LLM 输出的结构化文本）
2. 解析/格式化函数（剧情点、QA 报告的双向转换）
3. SimpleSkillExecutor（单个 Skill 的执行器）
4. SimpleAgentExecutor（工作流编排的执行器）

数据流：
    调用者 -> execute_skill() -> 模板填充 -> LLM 调用 -> 响应解析 -> 返回结果
                    ↓
            预处理输入（类型转换、格式化）
                    ↓
            填充默认值（可选参数）
"""
import json
from app.core.status import TaskStatus
import re
import logging
from typing import Dict, Any, Optional, List, Union
from sqlalchemy.orm import Session
from app.models.ai_task import AITask
from app.models.project import Project
from app.core.exceptions import TaskCancelledError
from app.ai.llm_logger import llm_context

logger = logging.getLogger(__name__)


# ==================== 结构化文本格式解析/格式化函数 ====================
#
# LLM 输出格式说明：
# 为了提高 LLM 输出的稳定性和可读性，我们使用结构化文本格式而非 JSON。
# 这样 LLM 更容易遵循格式，用户也能直接阅读原始输出。
#
# 支持的格式：
# 1. 新格式（推荐）- 按集分组，每行一个剧情点
# 2. 旧格式（兼容）- 管道符或逗号分隔的单行格式

# -------------------- 预编译正则表达式（性能优化） --------------------

# 策略1：标准管道符格式
# 示例：1|酒店大堂|林浩/陈总|林浩揭穿欺诈|打脸爽点|第1集
PLOT_POINT_PIPE_PATTERN = re.compile(
    r'^(\d+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|第(\d+)集$'
)

# 策略2：带分数的管道符格式（钩子中包含分数）
# 示例：1|xxx|xxx|xxx|危机求助（7分）|第1集
PIPE_WITH_SCORE_PATTERN = re.compile(
    r'^(\d+)\|([^|]+)\|([^|]+)\|(.+?)\|([^|（）\d]+(?:\（\d+分\）)?)\|第(\d+)集$'
)

# 策略3：逗号分隔集数格式
# 示例：1|xxx|xxx|xxx|真相线索，第13集
COMMA_EPISODE_PATTERN = re.compile(
    r'^(\d+)\|([^|]+)\|([^|]+)\|(.+?)\|(.+?)，第(\d+)集$'
)

# 旧格式兼容：按集分组
# 示例：
#   【第1集】
#   场景：酒店大堂 角色：林浩/陈总 剧情：林浩揭穿欺诈 钩子：打脸爽点
EPISODE_HEADER_PATTERN = re.compile(r'【第(\d+)集】')
# -------------------- QA 报告格式正则 --------------------
# QA 评分解析 - 格式：总分：82 或 总分：82/100
QA_SCORE_PATTERN = re.compile(r'总分[：:]\s*(\d+)(?:/(\d+))?')

# QA 状态解析 - 格式：状态：通过 / 状态：不通过
QA_STATUS_PATTERN = re.compile(r'状态[：:]\s*(✅|❌)?\s*(PASS|通过|FAIL|不通过|未通过)')

# QA 维度正则 - 格式：【维度N】名称 评分 XX 通过/未通过
# 优化：更宽松的说明匹配，支持多种格式变体
QA_DIMENSION_PATTERN = re.compile(
    r'【维度(\d+)】\s*(.+?)\s+评分\s*[：:]?\s*(\d+)\s*(通过|未通过|不通过|良好|需调整|基本达标|优秀)'
    r'(?:[\s\n]*说明[：:]\s*(.+?))?(?=\s*\n\s*【维度|\s*\n\s*【修改清单】|\s*\n\s*【问题清单】|\s*$)',
    re.DOTALL
)

# QA 修改项正则 - 格式：1. 【剧情N】修改内容
QA_FIX_ITEM_PATTERN = re.compile(
    r'(?:^|\n)(\d+)[.、]\s*【剧情(\d+)】\s*(.+?)(?=\n\d+[.、]|\s*$)',
    re.DOTALL
)


def parse_text_plot_points(response: str) -> List[Dict[str, Any]]:
    """解析结构化文本格式的剧情点

    格式（管道符分隔，每行一个）：
    1|酒店大堂|林浩/陈总|林浩揭穿欺诈|打脸爽点|第1集

    支持多种格式变体：
    - 标准格式：1|场景|角色|剧情|钩子|第1集
    - 带分数格式：1|场景|角色|剧情|钩子（7分）|第1集
    - 逗号分隔：1|场景|角色|剧情|钩子，第1集
    - 宽松格式：1|场景|角色|剧情|钩子|第1集。（带标点）

    Args:
        response: LLM 输出的结构化文本

    Returns:
        list[dict]: 剧情点 JSON 列表
    """
    if not response:
        return []

    plot_points: List[Dict[str, Any]] = []

    # 预编译宽松格式正则（允许结尾有标点符号）
    LOOSE_PIPE_PATTERN = re.compile(
        r'^(\d+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|第(\d+)集[。.、，,]?$'
    )
    # 更宽松的格式：集数可能用其他方式表示
    VERY_LOOSE_PATTERN = re.compile(
        r'^(\d+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|[第]?(\d+)[集]?[。.、，,]?$'
    )

    lines = response.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue

        point_id = scene = characters_str = event = hook_type = episode = None

        # 策略1：标准管道符格式
        pipe_match = PLOT_POINT_PIPE_PATTERN.match(line)
        if pipe_match:
            point_id = int(pipe_match.group(1))
            scene = pipe_match.group(2).strip()
            characters_str = pipe_match.group(3).strip()
            event = pipe_match.group(4).strip()
            hook_type = pipe_match.group(5).strip()
            episode = int(pipe_match.group(6))

        # 策略2：宽松格式（允许结尾标点）
        if point_id is None:
            loose_match = LOOSE_PIPE_PATTERN.match(line)
            if loose_match:
                point_id = int(loose_match.group(1))
                scene = loose_match.group(2).strip()
                characters_str = loose_match.group(3).strip()
                event = loose_match.group(4).strip()
                hook_type = loose_match.group(5).strip()
                episode = int(loose_match.group(6))

        # 策略3：更宽松格式
        if point_id is None:
            very_loose_match = VERY_LOOSE_PATTERN.match(line)
            if very_loose_match:
                point_id = int(very_loose_match.group(1))
                scene = very_loose_match.group(2).strip()
                characters_str = very_loose_match.group(3).strip()
                event = very_loose_match.group(4).strip()
                hook_type = very_loose_match.group(5).strip()
                episode = int(very_loose_match.group(6))

        # 策略4：逗号分隔集数格式
        if point_id is None:
            comma_match = COMMA_EPISODE_PATTERN.match(line)
            if comma_match:
                point_id = int(comma_match.group(1))
                scene = comma_match.group(2).strip()
                characters_str = comma_match.group(3).strip()
                event = comma_match.group(4).strip()
                hook_type = comma_match.group(5).strip()
                episode = int(comma_match.group(6))

        # 策略5：带分数的管道符格式
        if point_id is None:
            score_match = PIPE_WITH_SCORE_PATTERN.match(line)
            if score_match:
                point_id = int(score_match.group(1))
                scene = score_match.group(2).strip()
                characters_str = score_match.group(3).strip()
                event = score_match.group(4).strip()
                hook_type = score_match.group(5).strip()
                episode = int(score_match.group(6))

        # 如果成功匹配，构建剧情点对象
        if point_id is not None:
            try:
                # 清理钩子类型中的分数，如 "危机求助（7分）" -> "危机求助"
                hook_type = re.sub(r'[（(]\d+分[）)]', '', hook_type).strip()
                # 清理钩子类型中的结尾标点
                hook_type = re.sub(r'[。.、，,]+$', '', hook_type).strip()

                characters = [c.strip() for c in characters_str.split('/') if c.strip()]

                plot_point: Dict[str, Any] = {
                    "id": point_id,
                    "scene": scene,
                    "characters": characters,
                    "event": event,
                    "hook_type": hook_type,
                    "episode": episode,
                    "status": "unused",
                }
                plot_points.append(plot_point)
            except (ValueError, IndexError) as e:
                logger.debug(f"剧情点解析失败: {e}, 行: {line[:50]}")
                continue

    if plot_points:
        logger.info(f"管道符格式解析成功，共 {len(plot_points)} 个剧情点")
    elif '|' in response:
        # 记录更详细的调试信息
        sample_lines = [l.strip() for l in response.split('\n') if '|' in l][:3]
        logger.warning(f"检测到管道符但解析失败，示例行: {sample_lines}")
        logger.warning(f"响应文本前500字符: {response[:500]}")
    else:
        logger.warning(f"未检测到管道符，响应文本前200字符: {response[:200]}")

    return plot_points


def format_plot_points_to_text(plot_points: List[Dict[str, Any]]) -> str:
    """将剧情点 JSON 列表转换为管道符分隔的文本格式

    输出格式（每行一个剧情点）：
    1|酒店大堂|林浩/陈总|林浩揭穿欺诈|打脸爽点|第1集
    2|公司会议室|林浩/秘书小王|林浩展示隐藏实力|碾压爽点|第1集
    3|地下停车场|林浩/神秘女子|神秘女子暗示身份|悬念开场|第2集

    Args:
        plot_points: 剧情点 JSON 列表

    Returns:
        str: 管道符分隔的文本
    """
    if not plot_points:
        logger.warning(f"[格式化] plot_points 为空，返回空字符串")
        return ""

    logger.info(f"[格式化] 开始格式化 {len(plot_points)} 个剧情点")

    lines = []
    for i, point in enumerate(plot_points):
        if isinstance(point, dict):
            point_id = point.get("id", i + 1)
            scene = point.get("scene", "")
            characters = point.get("characters", [])
            event = point.get("event", "")
            hook_type = point.get("hook_type", "")
            episode = point.get("episode", 1)

            # 角色用 / 分隔
            if isinstance(characters, list):
                chars_str = "/".join(characters)
            else:
                chars_str = str(characters)

            line = f"{point_id}|{scene}|{chars_str}|{event}|{hook_type}|第{episode}集"
            lines.append(line)
        elif isinstance(point, str):
            # 已经是文本格式，直接使用
            lines.append(point)

    return "\n".join(lines)


def parse_text_qa_result(response: str) -> Dict[str, Any]:
    """解析 QA 质检结果文本

    输入格式：
    【质检报告】
    总分：75
    状态：不通过

    【维度1】冲突强度评估
    评分：80
    结果：通过
    说明：冲突标注准确

    【维度2】情绪钩子识别
    评分：60
    结果：不通过
    说明：第3个剧情点钩子类型有误
    修改意见：第1集第3个剧情点钩子应为"打脸爽点"

    【修改清单】
    1. 第1集第3个剧情点：钩子类型 悬念开场 → 打脸爽点

    Args:
        response: LLM 输出的 QA 文本报告

    Returns:
        dict: 解析后的 QA 结果
    """
    if not response:
        return {"qa_status": "pending", "qa_score": None}

    result: Dict[str, Any] = {
        "qa_status": "pending",
        "qa_score": None,
        "dimensions": [],
        "issues": [],
        "fix_instructions": []
    }

    # 解析总分
    score_match = QA_SCORE_PATTERN.search(response)
    if score_match:
        result["qa_score"] = int(score_match.group(1))

    # 解析状态
    status_match = QA_STATUS_PATTERN.search(response)
    if status_match:
        emoji = status_match.group(1)
        text_status = status_match.group(2)
        if emoji == "✅" or text_status in ("PASS", "通过"):
            result["qa_status"] = "PASS"
        elif emoji == "❌" or text_status in ("FAIL", "不通过", "未通过"):
            result["qa_status"] = "FAIL"
    elif result["qa_score"] is not None:
        # 根据分数推断状态
        result["qa_status"] = "PASS" if result["qa_score"] >= 70 else "FAIL"

    # 解析各维度 - 格式：【维度N】名称 评分 XX 通过/未通过
    for dim_match in QA_DIMENSION_PATTERN.finditer(response):
        dim_id = int(dim_match.group(1))
        dim_name = dim_match.group(2).strip()
        score = float(dim_match.group(3)) if dim_match.group(3) else None
        result_str = dim_match.group(4).strip()
        passed = result_str in ("通过", "良好", "基本达标", "优秀")
        details = dim_match.group(5).strip() if dim_match.group(5) else ""

        dimension = {
            "id": dim_id,
            "name": dim_name,
            "score": score if score is not None else 0,  # 默认0分，更保守
            "max_score": 12.5,
            "passed": passed,
            "result": result_str,
            "details": details,
        }
        if not passed:
            result["issues"].append({
                "dimension": dimension["name"],
                "description": details
            })
        result["dimensions"].append(dimension)

    # 解析修改清单 - 格式：1. 【剧情N】修改内容
    fix_section_match = re.search(r'【修改清单】\s*\n(.+?)(?=\n【|$)', response, re.DOTALL)
    if fix_section_match:
        fix_text = fix_section_match.group(1)
        for fix_match in QA_FIX_ITEM_PATTERN.finditer(fix_text):
            plot_id = fix_match.group(2)
            action = fix_match.group(3).strip()
            result["fix_instructions"].append({
                "priority": "high",
                "target": f"剧情{plot_id}",
                "plot_id": int(plot_id),
                "action": action
            })

    # 添加别名映射
    result["status"] = result["qa_status"]
    result["score"] = result["qa_score"]

    return result


def format_qa_result_to_text(qa_result: Dict[str, Any]) -> str:
    """将 QA 结果转换为文本格式（用于传给修复 Skill）

    Args:
        qa_result: QA 结果字典

    Returns:
        str: 文本格式的 QA 报告
    """
    if not qa_result:
        return ""

    lines = ["【质检报告】"]

    # 总分和状态
    score = qa_result.get("qa_score")
    status = qa_result.get("qa_status", "pending")
    if score is not None:
        lines.append(f"总分：{score}")
    status_text = "通过" if status == "PASS" else "不通过"
    lines.append(f"状态：{status_text}")
    lines.append("")

    # 各维度
    dimensions = qa_result.get("dimensions", [])
    for dim in dimensions:
        if isinstance(dim, dict):
            dim_id = dim.get("id", dim.get("index", 0))
            name = dim.get("name", "未知维度")
            dim_score = dim.get("score", 0)
            max_score = dim.get("max_score", 12.5)
            passed = dim.get("passed", True)
            result_str = dim.get("result", "通过" if passed else "不通过")
            details = dim.get("details", "")
            fix_suggestion = dim.get("fix_suggestion", "")

            lines.append(f"【维度{dim_id}】{name} {dim_score}/{max_score}分 {result_str}")
            if details:
                lines.append(f"  说明：{details}")
            if fix_suggestion:
                lines.append(f"  修改意见：{fix_suggestion}")
            lines.append("")

    # 修改清单
    fix_instructions = qa_result.get("fix_instructions", [])
    if fix_instructions:
        lines.append("【修改清单】")
        for i, inst in enumerate(fix_instructions, 1):
            if isinstance(inst, dict):
                target = inst.get("target", "")
                action = inst.get("action", inst.get("suggestion", ""))
                lines.append(f"{i}. {target}：{action}")
            else:
                lines.append(f"{i}. {inst}")

    return "\n".join(lines)


def format_qa_feedback_to_text(feedback: Union[str, List, Dict]) -> str:
    """将 QA 反馈转换为文本格式

    Args:
        feedback: QA 反馈（str / list / dict）

    Returns:
        str: 文本格式的反馈
    """
    if isinstance(feedback, str):
        return feedback

    if isinstance(feedback, list):
        lines = []
        for i, item in enumerate(feedback, 1):
            if isinstance(item, dict):
                target = item.get("target", "")
                action = item.get("action", item.get("description", item.get("suggestion", "")))
                if target:
                    lines.append(f"{i}. {target}: {action}")
                else:
                    lines.append(f"{i}. {action}")
            else:
                lines.append(f"{i}. {item}")
        return "\n".join(lines)

    if isinstance(feedback, dict):
        # 处理 QA 报告格式
        parts = []
        if feedback.get("issues"):
            parts.append("问题列表：")
            for i, issue in enumerate(feedback["issues"], 1):
                if isinstance(issue, dict):
                    desc = issue.get("description", issue.get("issue", str(issue)))
                    parts.append(f"  {i}. {desc}")
                else:
                    parts.append(f"  {i}. {issue}")
        if feedback.get("fix_instructions"):
            parts.append("\n修正指令：")
            for i, inst in enumerate(feedback["fix_instructions"], 1):
                if isinstance(inst, dict):
                    action = inst.get("action", inst.get("suggestion", str(inst)))
                    target = inst.get("target", "")
                    if target:
                        parts.append(f"  {i}. {target}: {action}")
                    else:
                        parts.append(f"  {i}. {action}")
                else:
                    parts.append(f"  {i}. {inst}")
        return "\n".join(parts)

    return str(feedback)


def _try_fix_incomplete_json(json_str: str) -> str:
    """尝试修复不完整的 JSON 字符串

    常见问题：
    - 缺少结尾的 } 或 ]
    - 字符串未闭合
    - 尾部有多余字符

    Args:
        json_str: 可能不完整的 JSON 字符串

    Returns:
        修复后的 JSON 字符串
    """
    # 移除尾部的 ``` 标记
    json_str = re.sub(r'`+\s*$', '', json_str)

    # 统计括号
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    open_brackets = json_str.count('[')
    close_brackets = json_str.count(']')

    # 补充缺失的闭合括号
    if open_braces > close_braces:
        # 检查是否在字符串中间被截断（查找未闭合的引号）
        # 简单处理：如果最后一个字符不是 } 或 ]，尝试截断到最后一个完整的值
        last_valid_pos = max(
            json_str.rfind('},'),
            json_str.rfind('}]'),
            json_str.rfind('"}'),
            json_str.rfind('"]'),
            json_str.rfind('" }'),
            json_str.rfind('" ]'),
        )
        if last_valid_pos > 0:
            # 截断到最后一个完整的位置
            json_str = json_str[:last_valid_pos + 1]
            # 重新统计
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            open_brackets = json_str.count('[')
            close_brackets = json_str.count(']')

        # 补充缺失的 }
        json_str += '}' * (open_braces - close_braces)

    if open_brackets > close_brackets:
        json_str += ']' * (open_brackets - close_brackets)

    return json_str


def parse_llm_response(
    response: str,
    default: Any = None,
    logger_obj=None,
    raise_on_empty: bool = False
) -> Any:
    """解析 LLM 响应文本为 JSON（高度容错版本）

    这是统一的 JSON 解析函数，建议在整个项目中优先使用。

    解析策略（按优先级）：
    1. 直接解析整个响应
    2. 提取 ```json ... ``` 代码块
    3. 提取 ``` ... ```（无语言标记）
    4. 提取 { ... } JSON 对象
    5. 提取 [ ... ] JSON 数组
    6. 尝试修复不完整的 JSON
    7. 如果以上都失败，返回默认值

    Args:
        response: LLM 响应文本
        default: 解析失败时返回的默认值（默认为空列表）
        logger_obj: 日志对象，如果提供则记录错误
        raise_on_empty: 是否在空响应时抛出异常

    Returns:
        解析后的 JSON 对象，或默认值

    Raises:
        ValueError: 当 raise_on_empty=True 且响应为空时
    """
    if default is None:
        default = []

    # 检查响应是否为空
    if not response or not isinstance(response, str):
        if raise_on_empty:
            raise ValueError("LLM 返回空响应")
        return default

    response = response.strip()
    if not response:
        if raise_on_empty:
            raise ValueError("LLM 返回空字符串")
        return default

    # 策略1：直接解析
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # 策略2：提取 ```json ... ``` 代码块
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str = _try_fix_incomplete_json(json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    # 策略3：提取 ``` ... ```（无语言标记）
    json_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str = _try_fix_incomplete_json(json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    # 策略4：提取 { ... } 或 [ ... ]
    json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', response)
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str = _try_fix_incomplete_json(json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    # 策略5：检查是否包含空响应关键词
    if any(keyword in response for keyword in ['没有', '无', '空', 'null', 'None', '[]', '{}']):
        return []

    # 解析失败
    if logger_obj:
        logger_obj.error(
            f"JSON 解析失败，响应内容共 {len(response)} 字符:\n"
            f"--- 开始响应 ---\n{response[:500]}\n"
            f"{'... (截断)' if len(response) > 500 else '--- 结束响应 ---'}"
        )
    return default


class SimpleSkillExecutor:
    """简化的 Skill 执行器

    负责执行单个 Skill 的完整流程：
    1. 从数据库加载 Skill 配置（prompt 模板、模型参数等）
    2. 预处理输入参数（类型转换、格式化、填充默认值）
    3. 填充 Prompt 模板
    4. 调用 LLM 模型（支持流式/非流式）
    5. 解析响应（支持 JSON 和结构化文本格式）
    6. 发布执行日志（通过 Redis 推送到前端）

    使用示例：
        executor = SimpleSkillExecutor(db, model_adapter, log_publisher)
        result = executor.execute_skill(
            skill_name="webtoon_breakdown",
            inputs={"chapters_text": "...", "adapt_method": "..."},
            task_id="xxx"
        )
    """

    def __init__(self, db: Session, model_adapter, log_publisher=None):
        """初始化执行器

        Args:
            db: 数据库会话
            model_adapter: 模型适配器
            log_publisher: Redis 日志发布器（可选）
        """
        self.db = db
        self.model_adapter = model_adapter
        self.log_publisher = log_publisher

    def execute_skill(
        self,
        skill_name: str,
        inputs: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行单个 Skill

        Args:
            skill_name: Skill 名称
            inputs: 输入数据
            task_id: 任务 ID（用于日志推送）

        Returns:
            执行结果

        Raises:
            ValueError: Skill 不存在或输入参数错误
        """
        from app.models.skill import Skill

        # 1. 从数据库加载 Skill 配置
        skill = self.db.query(Skill).filter(
            Skill.name == skill_name,
            Skill.is_active == True
        ).first()

        if not skill:
            raise ValueError(f"Skill '{skill_name}' 不存在或未激活")

        # 2. 预处理输入：将非字符串类型转换为适当格式
        # ----------------------------------------------------------------
        # 预处理规则：
        # - 剧情点参数（plot_points, previous_plot_points）-> 结构化文本格式
        # - QA 反馈参数（qa_issues, qa_fix_instructions, qa_feedback）-> 文本格式
        # - 其他列表/字典 -> JSON 字符串
        # - None -> 空字符串
        # ----------------------------------------------------------------
        PLOT_POINTS_PARAMS = {"plot_points", "previous_plot_points"}
        QA_FEEDBACK_PARAMS = {"qa_issues", "qa_fix_instructions", "qa_feedback"}
        # 剧本参数：如果是字典且包含 full_script，提取完整剧本文本
        SCRIPT_PARAMS = {"script", "previous_script"}

        processed_inputs = {}
        for key, value in inputs.items():
            # 1. 处理 None 值
            if value is None:
                processed_inputs[key] = ""
                continue

            # 2. 处理字符串值
            if isinstance(value, str):
                # 检查是否是 JSON 格式的剧情点数据（兼容旧格式）
                if key in PLOT_POINTS_PARAMS and value.strip().startswith('['):
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, list):
                            processed_inputs[key] = format_plot_points_to_text(parsed)
                            continue
                    except json.JSONDecodeError:
                        pass
                processed_inputs[key] = value
                continue

            # 3. 处理列表值
            if isinstance(value, list):
                if key in PLOT_POINTS_PARAMS:
                    processed_inputs[key] = format_plot_points_to_text(value)
                elif key in QA_FEEDBACK_PARAMS:
                    processed_inputs[key] = format_qa_feedback_to_text(value)
                else:
                    processed_inputs[key] = json.dumps(value, ensure_ascii=False, indent=2)
                continue

            # 4. 处理字典值
            if isinstance(value, dict):
                if key in QA_FEEDBACK_PARAMS:
                    processed_inputs[key] = format_qa_feedback_to_text(value)
                elif key in SCRIPT_PARAMS:
                    # 剧本参数：提取 full_script 字段作为质检输入
                    full_script = value.get("full_script", "")
                    if full_script:
                        processed_inputs[key] = full_script
                    else:
                        # 如果没有 full_script，尝试从 structure 拼接
                        structure = value.get("structure", {})
                        if structure:
                            parts = []
                            for section in ["opening", "development", "climax", "hook"]:
                                section_data = structure.get(section, {})
                                content = section_data.get("content", "")
                                if content:
                                    parts.append(content)
                            processed_inputs[key] = "\n\n".join(parts)
                        else:
                            processed_inputs[key] = json.dumps(value, ensure_ascii=False, indent=2)
                else:
                    processed_inputs[key] = json.dumps(value, ensure_ascii=False, indent=2)
                continue

            # 5. 其他类型转字符串
            processed_inputs[key] = str(value)

        # 2.5 为 input_schema 中定义但未传入的参数提供默认空值
        # ----------------------------------------------------------------
        # 解决问题：Prompt 模板中的可选参数（如 previous_plot_points、qa_feedback）
        # 如果调用者未传入，str.format() 会抛出 KeyError。
        # 解决方案：遍历 input_schema，为缺失的参数填充空字符串。
        # 这样可选参数在首次调用时不会报错，LLM 会理解"如有"的语义。
        # ----------------------------------------------------------------
        if skill.input_schema:
            for param_name in skill.input_schema.keys():
                if param_name not in processed_inputs:
                    processed_inputs[param_name] = ""

        # 3. 填充 Prompt 模板
        try:
            prompt = skill.prompt_template.format(**processed_inputs)
        except KeyError as e:
            available_keys = list(processed_inputs.keys())
            raise ValueError(
                f"Skill '{skill_name}' 缺少必需的输入参数: {e}，"
                f"已提供的参数: {available_keys}"
            )

        # 3.5 清理空参数段落
        # ----------------------------------------------------------------
        # 问题：当 previous_plot_points、qa_feedback 等可选参数为空时，
        # 提示词中会出现空白段落，可能让 LLM 困惑。
        # 解决：移除标题后紧跟空内容的段落及其相关说明。
        # ----------------------------------------------------------------
        # 清理上轮拆解结果空段落
        prompt = re.sub(r'###\s*上轮拆解结果\s*\n\s*\n', '', prompt)
        # 清理质检反馈空段落及其相关注意事项
        prompt = re.sub(
            r'###\s*质检反馈[^\n]*\n\s*\n\s*\*\*注意\*\*[^\n]*\n',
            '',
            prompt
        )
        # 回退：如果上面没匹配到，单独清理质检反馈标题
        prompt = re.sub(r'###\s*质检反馈[^\n]*\n\s*\n', '', prompt)
        # 清理连续的分隔符（--- 后紧跟 ---）
        prompt = re.sub(r'---\s*\n\s*---', '---', prompt)
        # 清理连续的空行（超过2个换行符合并为2个）
        prompt = re.sub(r'\n{3,}', '\n\n', prompt)

        system_prompt = skill.system_prompt or ""

        # 4. 发布步骤开始（统一显示名称）
        step_display_name = self._normalize_step_name(skill.display_name or skill.name)
        if task_id:
            try:
                from app.core.progress import update_task_progress_sync
                progress_value = None
                if skill.name == "webtoon_breakdown":
                    progress_value = 20
                elif skill.name == "breakdown_aligner":
                    progress_value = 70
                update_task_progress_sync(
                    self.db,
                    task_id,
                    progress=progress_value,
                    current_step=f"{step_display_name}中..."
                )
            except Exception as log_err:
                logger.debug(f"进度更新失败（非关键）: {log_err}")

        if self.log_publisher and task_id:
            self.log_publisher.publish_step_start(
                task_id,
                step_display_name
            )

        if task_id and self._is_task_cancelled(task_id):
            raise TaskCancelledError("任务已取消，停止执行")

        # 5. 调用模型
        # ----------------------------------------------------------------
        # 配置优先级：Skill 配置 > 模型默认配置 > 硬编码默认值
        # - temperature: 控制输出随机性，拆解用 0.7，质检用 0.3
        # - max_tokens: 最大输出长度，长文本任务需要较大值
        # ----------------------------------------------------------------
        skill_config = skill.model_config or {}

        # 从 model_adapter 获取模型默认配置
        model_defaults = getattr(self.model_adapter, 'model_config', {}) or {}
        model_max_output = model_defaults.get('max_output_tokens') or model_defaults.get('max_tokens')
        model_temperature = model_defaults.get('temperature_default') or model_defaults.get('temperature')

        # 合并配置：Skill 覆盖 > 模型默认 > 硬编码默认
        temperature = skill_config.get("temperature") or model_temperature or 0.7
        max_tokens = skill_config.get("max_tokens") or model_max_output or 1000000

        # 确保 temperature 是 float 类型
        if hasattr(temperature, '__float__'):
            temperature = float(temperature)

        task_context = self._get_llm_task_context(task_id, skill)

        try:
            # 尝试使用流式生成
            full_response = ""
            stream_failed = False

            # 初始化流式 JSON 解析器（用于实时格式化输出）
            from app.utils.stream_json_parser import StreamJsonParser
            from app.utils.log_formatter import format_json_object, detect_content_type

            json_parser = StreamJsonParser()
            step_display_name = self._normalize_step_name(skill.display_name or skill.name)
            content_type = detect_content_type(step_display_name)
            formatted_index = 0

            try:
                with llm_context(**task_context):
                    for chunk in self.model_adapter.stream_generate(
                        prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens
                    ):
                        if task_id and self._is_task_cancelled(task_id):
                            raise TaskCancelledError("任务已取消，停止流式输出")
                        if chunk:  # 确保 chunk 不为 None
                            if self.log_publisher and task_id:
                                # 发送原始 JSON 片段
                                self.log_publisher.publish_stream_chunk(
                                    task_id,
                                    step_display_name,
                                    chunk
                                )

                                # 解析并发送格式化内容
                                parsed_objects = json_parser.feed(chunk)
                                for obj in parsed_objects:
                                    formatted_text = format_json_object(
                                        obj, content_type, formatted_index
                                    )
                                    self.log_publisher.publish_formatted_chunk(
                                        task_id,
                                        step_display_name,
                                        formatted_text + "\n"
                                    )
                                    formatted_index += 1

                            full_response += chunk
            except TaskCancelledError:
                # 任务取消应直接抛出，不回退到非流式
                raise
            except Exception as stream_error:
                # 其他异常：流式调用失败，回退到非流式
                logger.warning(f"流式调用失败，回退到非流式: {stream_error}")
                stream_failed = True

            # 如果流式失败或响应为空，使用非流式调用
            if stream_failed or not (full_response and full_response.strip()):
                logger.info("使用非流式调用...")
                if task_id and self._is_task_cancelled(task_id):
                    raise TaskCancelledError("任务已取消，停止非流式调用")
                with llm_context(**task_context):
                    full_response = self.model_adapter.generate(
                        prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                # 确保响应是字符串
                if isinstance(full_response, dict) and "content" in full_response:
                    full_response = full_response["content"]

            # 6. 解析 JSON 响应
            result = self._parse_json(full_response)

            # 若流式未产出任何格式化内容，则补发格式化日志，保证 Console 可见
            # 注意：不要重复发送原始内容，因为流式输出已经发送过了
            if formatted_index == 0 and self.log_publisher and task_id:
                try:
                    # 只补发格式化内容，不重复发送原始流式内容
                    items = None
                    if isinstance(result, list):
                        items = result
                    elif isinstance(result, dict) and "plot_points" in result:
                        items = result.get("plot_points") or []
                    elif result is not None:
                        items = [result]

                    if items is not None:
                        formatted_index = 0
                        for obj in items:
                            formatted_text = format_json_object(
                                obj, content_type, formatted_index
                            )
                            self.log_publisher.publish_formatted_chunk(
                                task_id,
                                step_display_name,
                                formatted_text + "\n"
                            )
                            formatted_index += 1
                except Exception as log_err:
                    logger.debug(f"流式日志格式化失败（非关键）: {log_err}")

            # 7. 发布步骤结束
            if self.log_publisher and task_id:
                self.log_publisher.publish_step_end(
                    task_id,
                    step_display_name,
                    {"status": "success"}
                )

            return result

        except Exception as e:
            if isinstance(e, TaskCancelledError):
                raise
            # 获取模型信息
            model_info = ""
            if hasattr(self.model_adapter, 'model_name'):
                model_info = f" [模型: {self.model_adapter.model_name}]"
            if hasattr(self.model_adapter, 'provider_name'):
                model_info += f" [提供商: {self.model_adapter.provider_name}]"

            error_msg = f"执行失败: {str(e)}{model_info}"

            # 发布错误
            if self.log_publisher and task_id:
                self.log_publisher.publish_error(
                    task_id,
                    error_msg,
                    error_code="SKILL_EXECUTION_ERROR",
                    step_name=step_display_name
                )
            raise Exception(error_msg) from e

    def _is_task_cancelled(self, task_id: str) -> bool:
        try:
            task = self.db.query(AITask).filter(AITask.id == task_id).first()
            if not task:
                return False
            return task.status in (TaskStatus.CANCELLING, TaskStatus.CANCELED, "cancelled")
        except Exception:
            return False

    def _normalize_step_name(self, name: str) -> str:
        # 规范化 step_name 输出（Console / WS / 进度一致）
        # 规则：
        # - 任何“质量校验/质量检查/质检/剧情拆解质量校验” => “质量检查”
        # - 任何“网文改编剧情拆解/剧情拆解/剧集拆解” => “剧集拆解”
        if not name:
            return name
        if any(key in name for key in ["剧情拆解质量校验", "质量校验", "质量检查", "质检"]):
            return "质量检查"
        if any(key in name for key in ["网文改编剧情拆解", "剧情拆解", "剧集拆解"]):
            return "剧集拆解"
        return name

    def _get_llm_task_context(self, task_id: Optional[str], skill) -> Dict[str, Any]:
        if not task_id:
            return {
                "task_id": None,
                "user_id": None,
                "project_id": None,
                "skill_name": skill.name,
                "stage": skill.display_name or skill.name
            }
        try:
            task = self.db.query(AITask).filter(AITask.id == task_id).first()
            project_id = None
            user_id = None
            if task and task.project_id:
                project_id = str(task.project_id)
                project = self.db.query(Project).filter(Project.id == task.project_id).first()
                if project:
                    user_id = str(project.user_id)
            return {
                "task_id": str(task_id),
                "user_id": user_id,
                "project_id": project_id,
                "skill_name": skill.name,
                "stage": skill.display_name or skill.name
            }
        except Exception:
            return {
                "task_id": str(task_id),
                "user_id": None,
                "project_id": None,
                "skill_name": skill.name,
                "stage": skill.display_name or skill.name
            }

    def _parse_json(self, response: str) -> Any:
        """解析响应（支持结构化文本和 JSON 格式）

        解析策略：
        1. 优先检测 QA 报告格式（【质检报告】标记）
        2. 检测剧情点格式（管道符）
        3. 尝试 JSON 解析
        4. 解析失败直接报错

        Args:
            response: AI 模型的响应文本

        Returns:
            解析后的 JSON 对象（列表或字典）

        Raises:
            ValueError: 响应为空或解析失败
        """
        if not response or not response.strip():
            raise ValueError("LLM 返回空响应")

        # 1. 优先检测 QA 报告格式（支持多种格式）
        # - 旧格式：【质检报告】
        # - 新格式：# 漫剧剧本质检报告 或 ## 整体评估
        is_qa_report = (
            '【质检报告】' in response or
            '质检报告' in response or
            ('总分' in response and '状态' in response and ('通过' in response or '不通过' in response))
        )
        if is_qa_report and not response.strip().startswith('{'):
            qa_result = parse_text_qa_result(response)
            if qa_result.get("qa_status") or qa_result.get("qa_score") is not None:
                logger.info(f"QA 报告解析成功，状态: {qa_result.get('qa_status')}, 分数: {qa_result.get('qa_score')}")
                return qa_result
            else:
                raise ValueError("QA 报告格式检测到但解析失败")

        # 2. 优先尝试 JSON 解析（剧本等结构化数据）
        _PARSE_FAILED = object()
        result = parse_llm_response(
            response=response,
            default=_PARSE_FAILED,
            logger_obj=logger,
            raise_on_empty=False
        )

        if result is not _PARSE_FAILED and isinstance(result, (dict, list)):
            return result

        # 3. JSON 解析失败后，检测剧情点格式（管道符）
        if '|' in response and '第' in response and '集' in response:
            text_result = parse_text_plot_points(response)
            if text_result:
                logger.info(f"剧情点解析成功，共 {len(text_result)} 个")
                return text_result

        raise ValueError("无法解析 LLM 响应")


class SimpleAgentExecutor:
    """增强的 Agent 执行器 - 工作流编排引擎

    Agent 是多个 Skill 的编排容器，支持：
    - sequential（顺序执行）：按顺序执行所有步骤
    - loop（循环执行）：循环执行直到满足退出条件或达到最大迭代次数

    工作流配置示例：
        {
            "type": "loop",
            "max_iterations": 3,
            "exit_condition": "qa_result.status == 'PASS' or qa_result.score >= 70",
            "steps": [
                {"id": "breakdown", "skill": "webtoon_breakdown", ...},
                {"id": "qa", "skill": "breakdown_aligner", ...}
            ]
        }

    步骤特性：
    - condition: 条件执行（表达式为真时才执行）
    - on_fail: 失败处理策略（stop=停止/skip=跳过）
    - max_retries: 最大重试次数（实现重试功能）
    - output_key: 输出结果的键名（用于后续步骤引用）
    - transform: 结果转换表达式

    变量引用语法：
    - ${context.xxx}: 引用初始上下文
    - ${step_id.xxx}: 引用某步骤的输出
    - ${qa_result.status}: 嵌套属性访问

    安全限制：
    - 子 Agent 调用深度限制为 5 层，防止无限递归
    """

    # 最大子 Agent 调用深度，防止无限递归
    MAX_AGENT_DEPTH = 5

    def __init__(self, db: Session, model_adapter, log_publisher=None, _depth: int = 0):
        """初始化执行器

        Args:
            db: 数据库会话
            model_adapter: 模型适配器
            log_publisher: Redis 日志发布器（可选）
            _depth: 当前调用深度（内部使用，防止无限递归）
        """
        self.db = db
        self.model_adapter = model_adapter
        self.skill_executor = SimpleSkillExecutor(db, model_adapter, log_publisher)
        self.log_publisher = log_publisher
        self._depth = _depth

    def execute_agent(
        self,
        agent_name: str,
        context: Dict[str, Any],
        task_id: Optional[str] = None,
        max_iterations_override: Optional[int] = None
    ) -> Dict[str, Any]:
        """执行 Agent 工作流

        Args:
            agent_name: Agent 名称
            context: 初始上下文数据
            task_id: 任务 ID（用于日志推送）
            max_iterations_override: 覆盖工作流的 max_iterations（用于控制循环次数）

        Returns:
            执行结果，包含所有步骤的输出

        Raises:
            ValueError: Agent 不存在或配置错误
            RecursionError: 子 Agent 调用深度超过限制
        """
        # 0. 检查调用深度，防止无限递归
        if self._depth >= self.MAX_AGENT_DEPTH:
            raise RecursionError(
                f"子 Agent 调用深度超过限制 ({self.MAX_AGENT_DEPTH})，"
                f"可能存在循环调用: {agent_name}"
            )

        from app.models.agent import SimpleAgent

        # 1. 加载 Agent 配置
        agent = self.db.query(SimpleAgent).filter(
            SimpleAgent.name == agent_name,
            SimpleAgent.is_active == True
        ).first()

        if not agent:
            raise ValueError(f"Agent '{agent_name}' 不存在或未激活")

        # 2. 解析工作流配置
        workflow = agent.workflow
        if not workflow or "steps" not in workflow:
            raise ValueError(f"Agent '{agent_name}' 的工作流配置无效")

        workflow_type = workflow.get("type", "sequential")

        # 发布 Agent 开始
        if self.log_publisher and task_id:
            self.log_publisher.publish_info(
                task_id,
                f"🤖 启动智能流程：{agent.display_name or agent.name}"
            )

        # 3. 根据工作流类型执行
        if workflow_type == "loop":
            results = self._execute_loop_workflow(workflow, context, task_id, max_iterations_override)
        else:
            results = self._execute_sequential_workflow(workflow, context, task_id)

        # 发布 Agent 完成
        if self.log_publisher and task_id:
            self.log_publisher.publish_success(
                task_id,
                f"🎉 {agent.display_name or agent.name} 完成"
            )

        return results

    def _execute_sequential_workflow(
        self,
        workflow: Dict[str, Any],
        context: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行顺序工作流

        按顺序执行所有步骤，支持条件执行。

        Args:
            workflow: 工作流配置
            context: 初始上下文
            task_id: 任务 ID

        Returns:
            执行结果
        """
        steps = workflow.get("steps", [])
        results = {"context": context}

        for step in steps:
            step_result = self._execute_step(step, results, task_id)
            if step_result is not None:
                # 合并步骤结果到 results
                results.update(step_result)

        return results

    def _execute_loop_workflow(
        self,
        workflow: Dict[str, Any],
        context: Dict[str, Any],
        task_id: Optional[str] = None,
        max_iterations_override: Optional[int] = None
    ) -> Dict[str, Any]:
        """执行循环工作流

        循环执行步骤直到满足退出条件或达到最大迭代次数。

        Args:
            workflow: 工作流配置
            context: 初始上下文
            task_id: 任务 ID
            max_iterations_override: 覆盖工作流的 max_iterations

        Returns:
            执行结果
        """
        steps = workflow.get("steps", [])
        max_iterations = max_iterations_override if max_iterations_override is not None else workflow.get("max_iterations", 3)
        exit_condition = workflow.get("exit_condition", "false")

        results = {"context": context, "_iteration": 0, "plot_points": [], "qa_result": {}}

        for iteration in range(max_iterations):
            results["_iteration"] = iteration + 1

            if self.log_publisher and task_id:
                # 发送结构化的轮次信息（供前端标题栏显示）
                self.log_publisher.publish_round_info(
                    task_id,
                    current_round=iteration + 1,
                    total_rounds=max_iterations
                )
                # 同时发送文本日志
                self.log_publisher.publish_info(
                    task_id,
                    f"🔄 第 {iteration + 1} 轮处理（共 {max_iterations} 轮）"
                )

            # 执行所有步骤
            for step in steps:
                step_result = self._execute_step(step, results, task_id)
                if step_result is not None:
                    results.update(step_result)

            # 检查退出条件
            # 调试日志：记录 qa_result 的内容
            if "qa_result" in results:
                qa_result = results["qa_result"]
                logger.info(f"[退出条件] qa_result 类型: {type(qa_result)}")
                if isinstance(qa_result, dict):
                    logger.info(f"[退出条件] qa_result.keys: {list(qa_result.keys())}")
                    logger.info(f"[退出条件] status={qa_result.get('status')}, qa_status={qa_result.get('qa_status')}")
                    logger.info(f"[退出条件] score={qa_result.get('score')}, qa_score={qa_result.get('qa_score')}")

            condition_met = self._evaluate_condition(exit_condition, results)
            logger.info(f"[退出条件] 条件: {exit_condition}")
            logger.info(f"[退出条件] 评估结果: {condition_met}")

            if condition_met:
                if self.log_publisher and task_id:
                    self.log_publisher.publish_success(
                        task_id,
                        f"✅ 质量检查通过，第 {iteration + 1} 轮完成"
                    )
                break
        else:
            # 达到最大迭代次数
            if self.log_publisher and task_id:
                self.log_publisher.publish_warning(
                    task_id,
                    f"⚠️ 已完成 {max_iterations} 轮处理，结果可能需要人工复核"
                )

        # 清理内部变量
        results.pop("_iteration", None)
        return results

    def _execute_step(
        self,
        step: Dict[str, Any],
        results: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """执行单个步骤

        支持：
        - 条件执行（condition）
        - Skill 调用（skill）
        - 子 Agent 调用（agent）
        - 失败处理（on_fail）
        - 重试机制（max_retries）
        - 结果转换（transform）

        Args:
            step: 步骤配置
            results: 当前结果集
            task_id: 任务 ID

        Returns:
            步骤执行结果，如果跳过则返回 None
        """
        step_id = step.get("id", "unknown")
        condition = step.get("condition")
        skill_name = step.get("skill")
        agent_name = step.get("agent")
        input_template = step.get("inputs", {})
        output_key = step.get("output_key", step_id)
        on_fail = step.get("on_fail", "stop")
        max_retries = step.get("max_retries", 0)
        transform = step.get("transform")

        # 1. 检查条件
        if condition and not self._evaluate_condition(condition, results):
            logger.info(f"步骤 {step_id} 条件不满足，跳过")
            # 条件不满足时不发布日志，避免用户困惑
            return None

        # 2. 确定执行类型
        if not skill_name and not agent_name:
            logger.warning(f"步骤 {step_id} 缺少 skill 或 agent 字段，跳过")
            return None

        # 3. 解析输入
        try:
            inputs = self._resolve_inputs(input_template, results)
        except Exception as e:
            logger.error(f"步骤 {step_id} 解析输入失败: {e}")
            if on_fail == "stop":
                raise
            return None
        
        if self.log_publisher and task_id and step_id == "breakdown_retry":
            qa_feedback = inputs.get("qa_feedback")
            fb_len = len(qa_feedback) if isinstance(qa_feedback, str) else 0
            self.log_publisher.publish_info(
                task_id,
                f"🧩 修复输入检查: qa_feedback_len={fb_len}"
            )

        # 4. 执行（支持重试）
        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                if skill_name:
                    if self.log_publisher and task_id:
                        self.log_publisher.publish_info(
                            task_id,
                            f"▶️ 执行步骤: {step_id} (skill={skill_name})"
                        )
                    # 执行 Skill
                    result = self.skill_executor.execute_skill(
                        skill_name=skill_name,
                        inputs=inputs,
                        task_id=task_id
                    )
                else:
                    if self.log_publisher and task_id:
                        self.log_publisher.publish_info(
                            task_id,
                            f"▶️ 执行步骤: {step_id} (agent={agent_name})"
                        )
                    # 执行子 Agent（递归调用，深度 +1）
                    child_executor = SimpleAgentExecutor(
                        self.db, self.model_adapter, self.log_publisher,
                        _depth=self._depth + 1
                    )
                    result = child_executor.execute_agent(
                        agent_name=agent_name,
                        context=inputs,
                        task_id=task_id
                    )

                # 5. 应用结果转换
                if transform:
                    result = self._apply_transform(transform, result, results)

                # 兼容 QA 输出为单元素数组的情况，避免条件评估失败
                if output_key in ("qa_result", "qa") and isinstance(result, list):
                    if len(result) == 1 and isinstance(result[0], dict):
                        result = result[0]
                    elif len(result) == 0:
                        result = {}

                # 6. 返回结果
                return {
                    output_key: result,
                    step_id: result
                }

            except Exception as e:
                retry_count += 1
                last_error = e
                logger.error(
                    f"步骤 {step_id} 执行失败 (尝试 {retry_count}/{max_retries + 1}): {e}"
                )

                if retry_count <= max_retries:
                    # 继续重试
                    if self.log_publisher and task_id:
                        self.log_publisher.publish_warning(
                            task_id,
                            f"🔁 正在重试...（第 {retry_count} 次）"
                        )
                else:
                    # 超过最大重试次数
                    if on_fail == "stop":
                        raise
                    elif on_fail == "skip":
                        logger.warning(f"跳过步骤 {step_id}")
                        if self.log_publisher and task_id:
                            self.log_publisher.publish_warning(
                                task_id,
                                f"⚠️ 部分步骤未完成，继续处理..."
                            )
                        return None

    def _evaluate_condition(
        self,
        condition: str,
        results: Dict[str, Any]
    ) -> bool:
        """评估条件表达式

        支持的表达式：
        - 简单比较：qa_result.status == 'PASS'
        - 数值比较：qa_result.score >= 70
        - 逻辑运算：status == 'PASS' or score >= 60
        - 存在检查：qa_result.fix_instructions
        - 否定：not qa_result.has_errors

        Args:
            condition: 条件表达式字符串
            results: 当前结果集

        Returns:
            条件是否满足
        """
        if not condition:
            return True

        try:
            # 构建安全的评估环境
            eval_context = self._flatten_results(results)

            # 替换变量引用为实际值
            evaluated_condition = self._substitute_variables(condition, eval_context)

            # 安全评估
            return self._safe_eval(evaluated_condition, eval_context)
        except Exception as e:
            logger.warning(f"条件评估失败 '{condition}': {e}")
            return False

    def _flatten_results(self, results: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """扁平化结果字典，用于条件评估

        将嵌套字典转换为点分隔的键，如：
        {"qa_result": {"status": "PASS"}} -> {"qa_result.status": "PASS", "qa_result": {...}}

        Args:
            results: 结果字典
            prefix: 键前缀

        Returns:
            扁平化后的字典
        """
        flat = {}
        for key, value in results.items():
            full_key = f"{prefix}{key}" if prefix else key
            flat[full_key] = value

            if isinstance(value, dict):
                # 递归扁平化
                nested = self._flatten_results(value, f"{full_key}.")
                flat.update(nested)

        return flat

    def _substitute_variables(self, expression: str, context: Dict[str, Any]) -> str:
        """替换表达式中的变量引用

        Args:
            expression: 表达式字符串
            context: 变量上下文

        Returns:
            替换后的表达式
        """
        # 匹配变量名（支持点分隔）
        var_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\b'

        def replace_var(match):
            var_name = match.group(1)
            # 跳过 Python 关键字和布尔值
            if var_name in ('and', 'or', 'not', 'True', 'False', 'None', 'in', 'is'):
                return var_name

            if var_name in context:
                value = context[var_name]
                if isinstance(value, str):
                    return f"'{value}'"
                elif value is None:
                    return 'None'
                elif isinstance(value, bool):
                    return str(value)
                elif isinstance(value, (int, float)):
                    return str(value)
                elif isinstance(value, (list, dict)):
                    return repr(value)
                else:
                    return repr(value)
            return var_name

        return re.sub(var_pattern, replace_var, expression)

    def _safe_eval(self, expression: str, context: Dict[str, Any]) -> bool:
        """安全地评估表达式

        只允许基本的比较和逻辑运算。

        安全措施：
        1. 禁用 __builtins__
        2. 检查表达式中是否包含危险模式（如 __class__、__import__）
        3. 只允许白名单中的函数

        Args:
            expression: 表达式字符串
            context: 变量上下文

        Returns:
            评估结果
        """
        # 安全检查：拒绝包含危险模式的表达式
        dangerous_patterns = [
            '__', 'import', 'exec', 'eval', 'compile', 'open', 'file',
            'input', 'raw_input', 'globals', 'locals', 'vars', 'dir',
            'getattr', 'setattr', 'delattr', 'hasattr'
        ]
        expression_lower = expression.lower()
        for pattern in dangerous_patterns:
            if pattern in expression_lower:
                logger.warning(f"表达式包含危险模式 '{pattern}'，拒绝执行: {expression}")
                return False

        # 允许的操作符和函数（白名单）
        allowed_names = {
            'True': True,
            'False': False,
            'None': None,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
        }

        # 添加上下文变量（只添加安全的基本类型）
        for key, value in context.items():
            # 跳过可能危险的键名
            if key.startswith('_'):
                continue
            # 只允许基本类型
            if isinstance(value, (str, int, float, bool, type(None), list, dict)):
                allowed_names[key] = value

        try:
            # 使用 eval 但限制可用的名称
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return bool(result)
        except Exception as e:
            logger.warning(f"表达式评估失败 '{expression}': {e}")
            return False

    def _apply_transform(
        self,
        transform: str,
        result: Any,
        results: Dict[str, Any]
    ) -> Any:
        """应用结果转换

        支持简单的属性访问和方法调用。

        安全措施：与 _safe_eval 相同，检查危险模式。

        Args:
            transform: 转换表达式
            result: 原始结果
            results: 当前结果集

        Returns:
            转换后的结果
        """
        if not transform:
            return result

        # 安全检查：拒绝包含危险模式的表达式
        dangerous_patterns = [
            '__', 'import', 'exec', 'eval', 'compile', 'open', 'file',
            'input', 'raw_input', 'globals', 'locals', 'vars', 'dir',
            'getattr', 'setattr', 'delattr', 'hasattr'
        ]
        transform_lower = transform.lower()
        for pattern in dangerous_patterns:
            if pattern in transform_lower:
                logger.warning(f"转换表达式包含危险模式 '{pattern}'，拒绝执行: {transform}")
                return result

        try:
            # 构建评估上下文（只添加安全的基本类型）
            context = {
                "result": result,
                "results": results,
            }
            for key, value in results.items():
                if not key.startswith('_'):
                    context[key] = value

            # 安全评估转换表达式
            return eval(transform, {"__builtins__": {}}, context)
        except Exception as e:
            logger.warning(f"结果转换失败 '{transform}': {e}")
            return result

    def _resolve_inputs(
        self,
        input_template: Dict[str, Any],
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析输入模板中的变量引用

        支持：
        - ${context.chapters_text} - 引用初始上下文
        - ${step1.conflicts} - 引用步骤结果
        - ${conflicts} - 引用结果中的顶级键
        - ${qa_result.fix_instructions} - 嵌套属性访问

        Args:
            input_template: 输入模板
            results: 当前结果集

        Returns:
            解析后的输入数据

        Raises:
            ValueError: 变量不存在
        """
        # 调试日志：记录输入模板和当前结果
        logger.debug(f"_resolve_inputs: input_template keys = {list(input_template.keys())}")
        logger.debug(f"_resolve_inputs: results keys = {list(results.keys())}")

        def resolve_value(value):
            if isinstance(value, str) and "${" in value and "}" in value:
                # 支持字符串内插（例如："问题列表: ${qa_result.issues}"）
                def resolve_path(path: str):
                    parts = path.split(".")
                    current = results
                    for part in parts:
                        if isinstance(current, dict):
                            current = current.get(part)
                        elif hasattr(current, part):
                            current = getattr(current, part)
                        else:
                            # 变量路径无效时返回 None，不抛异常
                            # 这对于循环工作流的第一轮很重要，因为某些变量还不存在
                            logger.debug(f"变量 '{path}' 的路径无效，返回 None")
                            return None
                        if current is None:
                            logger.debug(f"变量 '{path}' 的值为 None")
                            return None
                    return current

                def repl(match):
                    path = match.group(1)
                    current = resolve_path(path)
                    if current is None:
                        return ""
                    # 对于列表和字典，直接返回原始对象的字符串表示
                    # 注意：这里返回的是字符串，但 execute_skill 的预处理逻辑
                    # 会检测 plot_points 等参数并调用 format_plot_points_to_text
                    # 所以这里需要返回 JSON 字符串，让预处理逻辑能正确识别
                    if isinstance(current, (dict, list)):
                        return json.dumps(current, ensure_ascii=False)
                    return str(current)

                # 检查是否整个值就是一个变量引用（如 "${plot_points}"）
                # 如果是，直接返回原始值而不是 JSON 字符串，以便后续正确处理
                single_var_match = re.match(r'^\$\{([^}]+)\}$', value)
                if single_var_match:
                    path = single_var_match.group(1)
                    resolved = resolve_path(path)
                    # 返回原始值，None 也保持为 None（由 execute_skill 统一处理）
                    return resolved

                return re.sub(r"\$\{([^}]+)\}", repl, value)
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(v) for v in value]
            else:
                return value

        return {k: resolve_value(v) for k, v in input_template.items()}

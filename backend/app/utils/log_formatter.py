"""日志格式化工具

将 JSON 格式的 LLM 输出转换为人类可读的格式化文本。

支持的格式化类型：
- 剧情点（plot_point）：格式化为 【第X集】场景：xxx 角色：xxx
- 质检维度（qa_dimension）：格式化为 【维度名】评分 X 通过/未通过
"""
from typing import Union


def format_plot_point(point: dict, index: int = 0) -> str:
    """格式化单个剧情点

    Args:
        point: 剧情点字典，包含 episode/scene/characters/event 等字段
        index: 剧情点索引（当 episode 字段缺失时使用）

    Returns:
        str: 格式化后的文本
    """
    # 提取集数
    episode = point.get("episode") or point.get("集数") or index + 1

    # 提取场景
    scene = point.get("scene") or point.get("场景") or "未知场景"

    # 提取角色（支持列表或字符串）
    characters_raw = point.get("characters") or point.get("角色") or []
    if isinstance(characters_raw, list):
        characters = "、".join(characters_raw) if characters_raw else "未知角色"
    else:
        characters = str(characters_raw) or "未知角色"

    # 提取事件/剧情
    event = point.get("event") or point.get("事件") or point.get("剧情") or ""

    # 提取情绪钩子类型
    hook_type = (
        point.get("hook_type") or
        point.get("emotion_hook") or
        point.get("情绪钩子") or
        point.get("悬疑钩子") or
        ""
    )

    # 构建格式化文本
    lines = [f"【第{episode}集】场景：{scene} 角色：{characters}"]

    if event:
        # 截断过长的事件描述
        event_display = event[:80] + "..." if len(event) > 80 else event
        lines.append(f"  剧情：{event_display}")

    if hook_type:
        lines.append(f"  情绪钩子：{hook_type}")

    return "\n".join(lines)


def format_qa_dimension(result: dict) -> str:
    """格式化质检维度结果

    Args:
        result: 质检维度结果字典

    Returns:
        str: 格式化后的文本
    """
    dimension = result.get("dimension") or result.get("维度") or "未知维度"
    score = result.get("score") or result.get("得分") or 0
    passed = result.get("passed") or result.get("pass") or result.get("通过")

    if passed is None:
        # 根据分数判断是否通过
        passed = score >= 60 if isinstance(score, (int, float)) else False

    status = "✓ 通过" if passed else "✗ 未通过"

    return f"【{dimension}】评分 {score} {status}"


def format_json_object(obj: dict, obj_type: str = "auto", index: int = 0) -> str:
    """根据对象类型自动选择格式化方法

    Args:
        obj: JSON 对象
        obj_type: 对象类型（auto/plot_point/qa_dimension）
        index: 对象索引

    Returns:
        str: 格式化后的文本
    """
    if obj_type == "auto":
        # 自动检测对象类型
        if any(key in obj for key in ["episode", "集数", "scene", "场景", "event", "事件"]):
            obj_type = "plot_point"
        elif any(key in obj for key in ["dimension", "维度", "passed", "pass"]):
            obj_type = "qa_dimension"
        else:
            obj_type = "unknown"

    if obj_type == "plot_point":
        return format_plot_point(obj, index)
    elif obj_type == "qa_dimension":
        return format_qa_dimension(obj)
    else:
        # 未知类型，返回简化的 key-value 格式
        return _format_generic_object(obj)


def _format_generic_object(obj: dict) -> str:
    """格式化通用 JSON 对象

    Args:
        obj: JSON 对象

    Returns:
        str: 格式化后的文本
    """
    lines = []
    for key, value in obj.items():
        if isinstance(value, list):
            value_str = "、".join(str(v) for v in value[:5])
            if len(value) > 5:
                value_str += f"...（共{len(value)}项）"
        elif isinstance(value, dict):
            value_str = f"{{...{len(value)}个字段}}"
        else:
            value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:50] + "..."

        lines.append(f"  {key}: {value_str}")

    return "\n".join(lines)


def detect_content_type(step_name: str) -> str:
    """根据步骤名称检测内容类型

    Args:
        step_name: 步骤名称

    Returns:
        str: 内容类型（plot_point/qa_dimension/unknown）
    """
    step_lower = step_name.lower() if step_name else ""

    if any(keyword in step_lower for keyword in ["拆解", "breakdown", "剧情", "plot"]):
        return "plot_point"
    elif any(keyword in step_lower for keyword in ["质检", "qa", "检查", "aligner"]):
        return "qa_dimension"
    else:
        return "unknown"

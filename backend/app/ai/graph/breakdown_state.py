from typing import TypedDict, List, Dict, Any


class BreakdownState(TypedDict):
    """Breakdown工作流状态"""

    # 输入数据
    batch_id: str
    project_id: str
    chapters: List[Dict[str, Any]]

    # 提取的元素
    conflicts: List[Dict[str, Any]]
    plot_hooks: List[Dict[str, Any]]
    characters: List[Dict[str, Any]]
    scenes: List[Dict[str, Any]]
    emotions: List[Dict[str, Any]]

    # 进度和错误
    current_step: str
    progress: int
    errors: List[str]

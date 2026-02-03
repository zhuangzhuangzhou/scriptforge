from typing import TypedDict, List, Dict, Any


class ScriptState(TypedDict):
    """Script工作流状态"""

    # 输入数据
    batch_id: str
    project_id: str
    breakdown_id: str
    breakdown_data: Dict[str, Any]

    # 生成的剧本元素
    episodes: List[Dict[str, Any]]
    scenes: List[Dict[str, Any]]
    dialogues: List[Dict[str, Any]]

    # 进度和错误
    current_step: str
    progress: int
    errors: List[str]

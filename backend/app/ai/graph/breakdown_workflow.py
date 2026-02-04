from langgraph.graph import StateGraph, END
from app.ai.graph.breakdown_state import BreakdownState
from app.ai.graph.breakdown_nodes import (
    load_chapters_node,
    extract_conflicts_node,
    identify_plot_hooks_node,
    analyze_characters_node,
    identify_scenes_node,
    extract_emotions_node,
    consistency_check_node,
    save_breakdown_node
)


def create_breakdown_workflow(model_adapter, db):
    """创建Breakdown工作流"""

    # 创建状态图
    workflow = StateGraph(BreakdownState)

    # 添加节点
    workflow.add_node("load_chapters", lambda state: load_chapters_node(state, db))
    workflow.add_node("extract_conflicts", lambda state: extract_conflicts_node(state, model_adapter))
    workflow.add_node("identify_plot_hooks", lambda state: identify_plot_hooks_node(state, model_adapter))
    workflow.add_node("analyze_characters", lambda state: analyze_characters_node(state, model_adapter))
    workflow.add_node("identify_scenes", lambda state: identify_scenes_node(state, model_adapter))
    workflow.add_node("extract_emotions", lambda state: extract_emotions_node(state, model_adapter))
    workflow.add_node("consistency_check", lambda state: consistency_check_node(state, model_adapter, db))
    workflow.add_node("save_breakdown", lambda state: save_breakdown_node(state, db))

    # 设置入口点
    workflow.set_entry_point("load_chapters")

    # 添加边（定义节点执行顺序）
    workflow.add_edge("load_chapters", "extract_conflicts")
    workflow.add_edge("extract_conflicts", "identify_plot_hooks")
    workflow.add_edge("identify_plot_hooks", "analyze_characters")
    workflow.add_edge("analyze_characters", "identify_scenes")
    workflow.add_edge("identify_scenes", "extract_emotions")
    workflow.add_edge("extract_emotions", "consistency_check")
    workflow.add_edge("consistency_check", "save_breakdown")
    workflow.add_edge("save_breakdown", END)

    return workflow.compile()

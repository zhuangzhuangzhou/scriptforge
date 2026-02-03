from langgraph.graph import StateGraph, END
from app.ai.graph.script_state import ScriptState
from app.ai.graph.script_nodes import (
    load_breakdown_node,
    plan_episodes_node,
    generate_scenes_node,
    write_dialogues_node,
    save_script_node
)


def create_script_workflow(model_adapter, db):
    """创建Script工作流"""

    # 创建状态图
    workflow = StateGraph(ScriptState)

    # 添加节点
    workflow.add_node("load_breakdown", lambda state: load_breakdown_node(state, db))
    workflow.add_node("plan_episodes", lambda state: plan_episodes_node(state, model_adapter))
    workflow.add_node("generate_scenes", lambda state: generate_scenes_node(state, model_adapter))
    workflow.add_node("write_dialogues", lambda state: write_dialogues_node(state, model_adapter))
    workflow.add_node("save_script", lambda state: save_script_node(state, db))

    # 设置入口点
    workflow.set_entry_point("load_breakdown")

    # 添加边
    workflow.add_edge("load_breakdown", "plan_episodes")
    workflow.add_edge("plan_episodes", "generate_scenes")
    workflow.add_edge("generate_scenes", "write_dialogues")
    workflow.add_edge("write_dialogues", "save_script")
    workflow.add_edge("save_script", END)

    return workflow.compile()

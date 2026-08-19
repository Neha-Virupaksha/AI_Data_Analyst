from langgraph.graph import StateGraph, END

from agents.state import GraphState
from agents.planner import planner_node
from agents.coder import coder_node
from agents.executor import executor_node
from agents.critic import critic_node, route_after_critic
from agents.writer import writer_node


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("planner", planner_node)
    graph.add_node("coder", coder_node)
    graph.add_node("executor", executor_node)
    graph.add_node("critic", critic_node)
    graph.add_node("writer", writer_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "coder")
    graph.add_edge("coder", "executor")
    graph.add_edge("executor", "critic")
    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {"retry": "coder", "proceed": "writer"},
    )
    graph.add_edge("writer", END)

    return graph.compile()

from langgraph.graph import StateGraph, END
from .state import EligibilityState
from .nodes.check_eligibility import check_eligibility_node
from .nodes.generate_question import generate_question_node
from .nodes.merge_user_input import merge_user_input_node
from .nodes.is_done import is_done_node


def build_eligibility_graph() -> StateGraph:
    """
    Builds and returns the LangGraph for interactive eligibility checking.
    """
    # Create the graph
    graph = StateGraph(EligibilityState)

    # Add all nodes
    graph.add_node("check_eligibility", check_eligibility_node)
    graph.add_node("generate_question", generate_question_node)
    graph.add_node("merge_user_input", merge_user_input_node)
    graph.add_node("is_done", is_done_node)

    # Entry point
    graph.set_entry_point("check_eligibility")

    # Flow control
    graph.add_conditional_edges(
        "check_eligibility",
        is_done_node,
        {
            "done": END,
            "ask": "generate_question"
        }
    )
    graph.add_edge("generate_question", "merge_user_input")
    graph.add_edge("merge_user_input", "check_eligibility")

    return graph.compile()

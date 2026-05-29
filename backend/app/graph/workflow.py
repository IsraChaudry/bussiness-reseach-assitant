from langgraph.graph import StateGraph, END

from app.graph.state import AgentState
from app.graph.nodes import clarity_agent, research_agent, validator_agent, synthesis_agent


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def route_after_clarity(state: AgentState) -> str:
    if state.get("needs_clarification"):
        return "clarification"
    return "research"


def route_after_research(state: AgentState) -> str:
    score = state.get("confidence_score", 0)
    if score >= 6:
        return "synthesis"
    return "validator"


def route_after_validator(state: AgentState) -> str:
    result = state.get("validation_result", "sufficient")
    attempts = state.get("attempts", 1)
    if result == "insufficient" and attempts < 3:
        return "research"
    return "synthesis"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("clarity", clarity_agent)
    graph.add_node("research", research_agent)
    graph.add_node("validator", validator_agent)
    graph.add_node("synthesis", synthesis_agent)

    graph.set_entry_point("clarity")

    graph.add_conditional_edges(
        "clarity",
        route_after_clarity,
        {
            "clarification": END,
            "research": "research",
        },
    )

    graph.add_conditional_edges(
        "research",
        route_after_research,
        {
            "validator": "validator",
            "synthesis": "synthesis",
        },
    )

    graph.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "research": "research",
            "synthesis": "synthesis",
        },
    )

    graph.add_edge("synthesis", END)

    return graph.compile()


# Compiled graph singleton
_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_graph(state: AgentState) -> AgentState:
    """Run the compiled LangGraph and return the final state."""
    graph = get_graph()
    result = graph.invoke(state)
    return result

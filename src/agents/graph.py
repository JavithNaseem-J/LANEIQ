import logging
from langgraph.graph import END, START, StateGraph
from src.agents.exception import exception_node
from src.agents.planner import planner_node
from src.agents.report import report_node
from src.agents.route import route_node
from src.agents.state import AgentState

logger = logging.getLogger(__name__)


def build_graph() -> StateGraph:
    """Construct and compile the LangGraph agent pipeline."""

    graph = StateGraph(AgentState)

    # ── Register nodes
    graph.add_node("planner", planner_node)
    graph.add_node("route", route_node)
    graph.add_node("exception", exception_node)
    graph.add_node("report", report_node)

    # ── Wire edges (linear sequence)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "route")
    graph.add_edge("route", "exception")
    graph.add_edge("exception", "report")
    graph.add_edge("report", END)

    return graph.compile()


# Module-level singleton — import this in tests and the API layer
pipeline = build_graph()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    dummy_state: AgentState = {
        "shipment_brief": "Ship 500 kg of electronics from Chennai to Jebel Ali by June 20.",
        "decomposed_tasks": [],
        "route_options": [],
        "selected_route": None,
        "exceptions": [],
        "final_report": None,
        "error": None,
    }

    print("Running graph on dummy state...")
    result = pipeline.invoke(dummy_state)
    print("Graph traversal complete.")
    print("Keys in result:", list(result.keys()))

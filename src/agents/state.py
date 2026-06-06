from typing import Any, Optional, TypedDict


class AgentState(TypedDict, total=False):

    shipment_brief: str  # Free-text shipment description from the user

    decomposed_tasks: list[dict[str, Any]]  # Structured fields extracted from brief

    route_options: list[dict[str, Any]]  # All solver results with costs
    selected_route: Optional[dict[str, Any]]  # Best route chosen by the agent

    exceptions: list[dict[str, Any]]  # Detected delays / disruptions

    final_report: Optional[str]  # Human-readable summary of the routing decision

    error: Optional[str]  # Set by any node on failure; downstream nodes check this

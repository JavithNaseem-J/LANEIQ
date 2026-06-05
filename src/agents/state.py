"""
Agent state definition for the LANEIQ multi-agent system.

All fields are Optional so every agent node only needs to
populate the fields it is responsible for.
"""

from typing import Any, Optional, TypedDict


class AgentState(TypedDict, total=False):
    """Shared state that flows through the LangGraph pipeline."""

    # ── Input ────────────────────────────────────────────────────────────
    shipment_brief: str  # Free-text shipment description from the user

    # ── Planner output ────────────────────────────────────────────────────
    decomposed_tasks: list[dict[str, Any]]  # Structured fields extracted from brief

    # ── Route Agent output ────────────────────────────────────────────────
    route_options: list[dict[str, Any]]  # All solver results with costs
    selected_route: Optional[dict[str, Any]]  # Best route chosen by the agent

    # ── Exception Agent output ────────────────────────────────────────────
    exceptions: list[dict[str, Any]]  # Detected delays / disruptions

    # ── Report Agent output ───────────────────────────────────────────────
    final_report: Optional[str]  # Human-readable summary of the routing decision

    # ── Error handling ────────────────────────────────────────────────────
    error: Optional[str]  # Set by any node on failure; downstream nodes check this

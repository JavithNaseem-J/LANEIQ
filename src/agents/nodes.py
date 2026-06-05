"""
Stub agent nodes — each node logs its name and passes state
through unchanged. These will be replaced one-by-one in Days 9-12.
"""

import logging

from src.agents.state import AgentState

logger = logging.getLogger(__name__)


def planner_node(state: AgentState) -> AgentState:
    """
    Planner Agent (stub).
    Day 9: will decompose shipment_brief into structured decomposed_tasks.
    """
    logger.info("[planner_node] received state — passing through (stub)")
    return state


def route_node(state: AgentState) -> AgentState:
    """
    Route Agent (stub).
    Day 10: will call OR-Tools VRP and populate route_options / selected_route.
    """
    logger.info("[route_node] received state — passing through (stub)")
    return state


def exception_node(state: AgentState) -> AgentState:
    """
    Exception Agent (stub).
    Day 11: will check vessel/flight ETAs and re-route on detected delays.
    """
    logger.info("[exception_node] received state — passing through (stub)")
    return state


def report_node(state: AgentState) -> AgentState:
    """
    Report Agent (stub).
    Day 12: will generate a human-readable final_report.
    """
    logger.info("[report_node] received state — passing through (stub)")
    return state

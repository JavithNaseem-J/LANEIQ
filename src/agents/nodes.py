import logging

from src.agents.state import AgentState

logger = logging.getLogger(__name__)


def planner_node(state: AgentState) -> AgentState:

    logger.info("[planner_node] received state — passing through (stub)")
    return state


def route_node(state: AgentState) -> AgentState:

    logger.info("[route_node] received state — passing through (stub)")
    return state


def exception_node(state: AgentState) -> AgentState:

    logger.info("[exception_node] received state — passing through (stub)")
    return state


def report_node(state: AgentState) -> AgentState:

    logger.info("[report_node] received state — passing through (stub)")
    return state

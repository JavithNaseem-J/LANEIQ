import logging
from datetime import datetime, timezone

from src.agents.state import AgentState
from src.data.vessel_api import get_vessel_eta

logger = logging.getLogger(__name__)


def _parse_deadline(deadline_str: str) -> datetime:
    """Parse ISO deadline string to timezone-aware datetime."""
    dt = datetime.fromisoformat(deadline_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _tighten_time_window(routing_input: dict, delay_hours: int) -> dict:
    """
    Re-route a single shipment by reducing the deadline by the detected delay.
    This forces the solver to find a faster (likely air) mode.
    """
    tw = routing_input["time_window"]
    new_deadline = max(tw["deadline_hours"] - delay_hours, tw["ready_hours"] + 1)
    return {
        **routing_input,
        "time_window": {**tw, "deadline_hours": new_deadline},
    }


def exception_node(state: AgentState) -> AgentState:
    """
    Exception Agent node.

    For each shipment in state['selected_route']['routes']:
      - Calls vessel_api to get expected ETA.
      - If delayed: records the exception, tightens the time window,
        calls the baseline solver to find a faster fallback mode,
        and records the resolution.

    Appends exception events to state['exceptions'].
    Never blocks the pipeline — errors are logged and skipped.
    """
    if state.get("error"):
        logger.warning("[exception_node] upstream error detected — skipping.")
        return state

    selected = state.get("selected_route")
    tasks = state.get("decomposed_tasks", [])

    if not selected or not tasks:
        logger.info("[exception_node] no selected_route or tasks — nothing to check.")
        return {**state, "exceptions": []}

    exceptions = []

    # Build a quick lookup of task details by shipment_id
    task_map = {t.get("shipment_id", "AGENT-001"): t for t in tasks}

    routes = selected.get("routes", [])

    for route in routes:
        shipment_id = route.get("shipment_id") or route.get("vehicle_id", "AGENT-001")
        mode = route.get("mode", "sea")  # baseline routes have 'mode'; VRP routes may not

        # Find the matching decomposed task for deadline info
        task = task_map.get(shipment_id) or (tasks[0] if tasks else None)
        if not task:
            continue

        try:
            deadline_dt = _parse_deadline(task["deadline"])
            dest_port = task["destination_port"]

            eta_info = get_vessel_eta(
                shipment_id=shipment_id,
                destination_port=dest_port,
                deadline_dt=deadline_dt,
                mode=mode,
            )

            if not eta_info["delayed"]:
                logger.debug("[exception_node] %s — on time (ETA %s).", shipment_id, eta_info["eta"])
                continue

            delay_hours = eta_info["delay_hours"]
            logger.info(
                "[exception_node] DELAY detected on %s — %d hrs late. Triggering re-route.",
                shipment_id,
                delay_hours,
            )

            # ── Re-route with tightened deadline ──────────────────────────
            from src.agents.route import _task_to_routing_input
            from src.solver import baseline as baseline_solver

            routing_input = _task_to_routing_input(task)
            tightened_input = _tighten_time_window(routing_input, delay_hours)
            reroute_res = baseline_solver.solve([tightened_input])

            resolution_route = reroute_res["routes"][0] if reroute_res["routes"] else {}
            resolution_mode = resolution_route.get("mode", "air")
            resolution_cost = resolution_route.get("cost", 0.0)

            exception_event = {
                "shipment_id": shipment_id,
                "exception_type": "vessel_delay",
                "detected_at": datetime.now(tz=timezone.utc).isoformat(),
                "delay_hours": delay_hours,
                "original_mode": mode,
                "resolution": {
                    "action": "re_routed",
                    "new_mode": resolution_mode,
                    "new_cost": resolution_cost,
                    "tightened_deadline_hours": tightened_input["time_window"]["deadline_hours"],
                },
                "eta_source": eta_info["source"],
            }
            exceptions.append(exception_event)
            logger.info(
                "[exception_node] %s re-routed %s -> %s (cost $%.2f).",
                shipment_id,
                mode,
                resolution_mode,
                resolution_cost,
            )

        except Exception as exc:
            logger.error("[exception_node] error processing %s: %s", shipment_id, exc)
            continue

    logger.info("[exception_node] %d exception(s) detected and resolved.", len(exceptions))
    return {**state, "exceptions": exceptions}

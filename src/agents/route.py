import logging
from datetime import datetime, timezone
from pathlib import Path

import mlflow

from src.agents.state import AgentState
from src.features.transform import PORT_COORDS, haversine
from src.solver import baseline, vrp

logger = logging.getLogger(__name__)

COST_COEFFICIENTS = {"sea": 1.2, "air": 4.5, "road": 2.0}

_repo_root = Path(__file__).resolve().parents[2]
_DB_PATH = _repo_root / "models" / "mlflow" / "mlflow.db"


def _task_to_routing_input(task: dict) -> dict:
    """
    Convert a single decomposed_task dict (from Planner) into the
    routing_inputs schema consumed by the VRP and baseline solvers.

    Time windows are built relative to 'now' so the solver can reason
    about urgency even without a full dataset epoch reference.
    """
    origin = task["origin_port"]
    dest = task["destination_port"]
    weight = float(task["cargo_weight_kg"])

    olat, olon = PORT_COORDS[origin]
    dlat, dlon = PORT_COORDS[dest]
    dist_km = haversine(olat, olon, dlat, dlon)

    now = datetime.now(tz=timezone.utc)
    deadline = datetime.fromisoformat(task["deadline"])
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    ready_hours = 0
    deadline_hours = max(int((deadline - now).total_seconds() / 3600), 1)

    return {
        "shipment_id": task.get("shipment_id", "AGENT-001"),
        "origin": origin,
        "destination": dest,
        "distance_km": round(dist_km, 2),
        "time_window": {"ready_hours": ready_hours, "deadline_hours": deadline_hours},
        "weight_kg": weight,
        "costs": {
            "sea": round(weight * COST_COEFFICIENTS["sea"], 2),
            "air": round(weight * COST_COEFFICIENTS["air"], 2),
            "road": round(weight * COST_COEFFICIENTS["road"], 2),
        },
    }


def route_node(state: AgentState) -> AgentState:
    """
    Route Agent node.
    Reads state["decomposed_tasks"], runs both VRP and baseline solvers,
    populates state["route_options"] and state["selected_route"].
    Logs cost_reduction to MLflow.
    """
    if state.get("error"):
        logger.warning("[route_node] upstream error detected — skipping.")
        return state

    tasks = state.get("decomposed_tasks", [])
    if not tasks:
        logger.warning("[route_node] decomposed_tasks is empty — skipping.")
        return {**state, "error": "decomposed_tasks is empty", "route_options": [], "selected_route": None}

    logger.info("[route_node] building routing inputs for %d task(s).", len(tasks))

    try:
        routing_inputs = [_task_to_routing_input(t) for t in tasks]

        # ── Run both solvers ──────────────────────────────────────────────
        baseline_res = baseline.solve(routing_inputs)
        vrp_res = vrp.solve(routing_inputs)

        baseline_cost = baseline_res["total_cost"]
        vrp_cost = vrp_res["total_cost"]

        cost_reduction = 0.0
        if baseline_cost > 0:
            cost_reduction = round((baseline_cost - vrp_cost) / baseline_cost * 100, 2)

        # ── Build route_options ───────────────────────────────────────────
        route_options = [
            {
                "strategy": "greedy_baseline",
                "total_cost": baseline_cost,
                "computation_time": baseline_res["computation_time"],
                "routes": baseline_res["routes"],
                "cost_reduction_vs_baseline": 0.0,
            },
            {
                "strategy": "ortools_vrp",
                "total_cost": vrp_cost,
                "computation_time": vrp_res["computation_time"],
                "routes": vrp_res["routes"],
                "cost_reduction_vs_baseline": cost_reduction,
            },
        ]

        # ── Select best option (lowest cost) ──────────────────────────────
        selected_route = min(route_options, key=lambda r: r["total_cost"])

        logger.info(
            "[route_node] baseline=$%.2f  vrp=$%.2f  reduction=%.1f%%  selected=%s",
            baseline_cost,
            vrp_cost,
            cost_reduction,
            selected_route["strategy"],
        )

        # ── Log to MLflow ─────────────────────────────────────────────────
        try:
            mlflow.set_tracking_uri(f"sqlite:///{_DB_PATH}")
            mlflow.set_experiment("FreightSolver-Optimisation")
            with mlflow.start_run(run_name="route_agent"):
                mlflow.log_metric("greedy_cost", baseline_cost)
                mlflow.log_metric("vrp_cost", vrp_cost)
                mlflow.log_metric("cost_reduction_pct", cost_reduction)
                mlflow.set_tag("source", "route_agent")
        except Exception as mlflow_exc:
            logger.warning("[route_node] MLflow logging failed (non-fatal): %s", mlflow_exc)

        return {
            **state,
            "route_options": route_options,
            "selected_route": selected_route,
            "error": None,
        }

    except Exception as exc:
        logger.error("[route_node] error: %s", exc)
        return {**state, "route_options": [], "selected_route": None, "error": str(exc)}

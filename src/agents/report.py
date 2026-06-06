import json
import logging
from groq import Groq
from api.schemas.result import ExceptionSummary, OptimisationResult, RouteOption
from config.settings import settings
from src.agents.state import AgentState

logger = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"

_SYSTEM_PROMPT = """You are a freight logistics analyst writing a concise, professional shipment report.

You will receive a JSON object containing the routing optimisation results for a shipment.
Write a clear 2-3 paragraph summary that covers:
1. The shipment origin, destination, cargo type and weight.
2. The selected routing strategy, its total cost, and how it compares to the greedy baseline.
3. Any exceptions (vessel delays) detected and how they were resolved.

Rules:
- Use only the values provided in the JSON — do NOT hallucinate any numbers.
- Be concise and professional. No bullet points — prose paragraphs only.
- Always state currency as USD.
- If no exceptions were detected, say so clearly.
"""


def _build_context(state: AgentState) -> dict:
    """Assemble the context dict passed to the LLM."""
    task = (state.get("decomposed_tasks") or [{}])[0]
    selected = state.get("selected_route") or {}
    options = state.get("route_options") or []
    exceptions = state.get("exceptions") or []

    # Cost reduction vs baseline
    baseline_opt = next((o for o in options if o.get("strategy") == "greedy_baseline"), None)
    baseline_cost = baseline_opt["total_cost"] if baseline_opt else 0.0
    selected_cost = selected.get("total_cost", 0.0)
    reduction_pct = 0.0
    if baseline_cost > 0:
        reduction_pct = round((baseline_cost - selected_cost) / baseline_cost * 100, 2)

    return {
        "shipment": {
            "origin": task.get("origin_port", "unknown"),
            "destination": task.get("destination_port", "unknown"),
            "cargo_type": task.get("cargo_type", "unknown"),
            "weight_kg": task.get("cargo_weight_kg", 0),
            "deadline": task.get("deadline", "unknown"),
            "preferred_mode": task.get("preferred_mode", "unknown"),
        },
        "selected_route": {
            "strategy": selected.get("strategy", "unknown"),
            "total_cost_usd": selected_cost,
            "num_routes": len(selected.get("routes", [])),
        },
        "baseline_cost_usd": baseline_cost,
        "cost_reduction_pct": reduction_pct,
        "exceptions": [
            {
                "shipment_id": e.get("shipment_id"),
                "delay_hours": e.get("delay_hours"),
                "original_mode": e.get("original_mode"),
                "new_mode": e.get("resolution", {}).get("new_mode"),
                "new_cost_usd": e.get("resolution", {}).get("new_cost"),
            }
            for e in exceptions
        ],
    }


def _build_result(state: AgentState, report_text: str) -> OptimisationResult:
    """Serialise full pipeline state into the OptimisationResult Pydantic schema."""
    options = state.get("route_options") or []
    selected = state.get("selected_route") or {}
    exceptions = state.get("exceptions") or []

    baseline_cost = next((o["total_cost"] for o in options if o.get("strategy") == "greedy_baseline"), 0.0)
    selected_cost = selected.get("total_cost", 0.0)
    reduction_pct = 0.0
    if baseline_cost > 0:
        reduction_pct = round((baseline_cost - selected_cost) / baseline_cost * 100, 2)

    route_options = [
        RouteOption(
            strategy=o.get("strategy", ""),
            total_cost=o.get("total_cost", 0.0),
            cost_reduction_vs_baseline=o.get("cost_reduction_vs_baseline", 0.0),
        )
        for o in options
    ]

    exception_summaries = [
        ExceptionSummary(
            shipment_id=e.get("shipment_id", ""),
            exception_type=e.get("exception_type", "vessel_delay"),
            delay_hours=e.get("delay_hours", 0),
            original_mode=e.get("original_mode", ""),
            new_mode=e.get("resolution", {}).get("new_mode", ""),
            new_cost=e.get("resolution", {}).get("new_cost", 0.0),
        )
        for e in exceptions
    ]

    return OptimisationResult(
        selected_strategy=selected.get("strategy", "unknown"),
        selected_cost_usd=selected_cost,
        cost_reduction_pct=reduction_pct,
        num_vehicles_used=len(selected.get("routes", [])),
        exceptions_detected=len(exceptions),
        exception_summaries=exception_summaries,
        all_options=route_options,
        final_report=report_text,
        error=state.get("error"),
    )


def report_node(state: AgentState) -> AgentState:
    """
    Report Agent node.
    Reads the full pipeline state, calls Groq to generate a plain-English summary,
    serialises everything to OptimisationResult, and sets state['final_report'].
    """
    if state.get("error"):
        logger.warning("[report_node] upstream error detected — skipping.")
        return state

    logger.info("[report_node] generating final report.")

    try:
        context = _build_context(state)
        context_json = json.dumps(context, indent=2)

        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Routing result:\n{context_json}"},
            ],
            temperature=0.3,
            max_tokens=512,
        )

        report_text = response.choices[0].message.content.strip()
        result = _build_result(state, report_text)
        final_report_str = result.model_dump_json(indent=2)

        logger.info("[report_node] report generated (%d chars).", len(report_text))
        return {**state, "final_report": final_report_str, "error": None}

    except Exception as exc:
        logger.error("[report_node] error: %s", exc)
        return {**state, "final_report": None, "error": str(exc)}

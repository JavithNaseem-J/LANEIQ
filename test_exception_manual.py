"""
Quick smoke test: run the full Planner -> Route -> Exception pipeline
and confirm at least one synthetic delay is detected and resolved.
"""
import json
import logging
import sys

logging.basicConfig(level=logging.INFO)
sys.path.insert(0, "f:/DSML/LANEIQ")

from src.agents.graph import pipeline

# Use a sea shipment — only sea routes have vessel delay checks
brief = (
    "Ship 1200 kg of machinery from Chennai to Jebel Ali by July 15, 2026. "
    "Sea freight preferred."
)

initial_state = {
    "shipment_brief": brief,
    "decomposed_tasks": [],
    "route_options": [],
    "selected_route": None,
    "exceptions": [],
    "final_report": None,
    "error": None,
}

print("Running full pipeline (Planner -> Route -> Exception -> Report stub)...\n")
result = pipeline.invoke(initial_state)

print("\n=== PIPELINE RESULT ===")
print(f"Error      : {result.get('error')}")
print(f"Tasks      : {len(result.get('decomposed_tasks', []))} extracted")
print(f"Selected   : {result.get('selected_route', {}).get('strategy')}")
cost = result.get("selected_route", {}).get("total_cost", 0)
print(f"Cost       : ${cost:,.2f}")
exceptions = result.get("exceptions", [])
print(f"Exceptions : {len(exceptions)} detected")
for exc in exceptions:
    res = exc.get("resolution", {})
    print(
        f"  - {exc['shipment_id']}: {exc['exception_type']} "
        f"(+{exc['delay_hours']}h) -> re-routed {exc['original_mode']} -> {res.get('new_mode')}"
    )

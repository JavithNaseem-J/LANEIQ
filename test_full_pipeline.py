"""
Day 12 — Full 4-node pipeline smoke test.
Runs Planner -> Route -> Exception -> Report on 3 different briefs.
"""
import json
import logging
import sys

logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, "f:/DSML/LANEIQ")

from src.agents.graph import pipeline

BRIEFS = [
    "Ship 500 kg of electronics from Chennai to Jebel Ali by June 20, 2026. Prefer air freight.",
    "Move 2000 kg of textiles from NSICT Mumbai to Abu Dhabi by July 5, 2026. Sea freight.",
    "Urgent: 150 kg of perishables from Delhi ICD to Jebel Ali, must arrive by June 15, 2026.",
]

for idx, brief in enumerate(BRIEFS, 1):
    print(f"\n{'='*70}")
    print(f"BRIEF {idx}: {brief}")
    print("="*70)

    result = pipeline.invoke({
        "shipment_brief": brief,
        "decomposed_tasks": [],
        "route_options": [],
        "selected_route": None,
        "exceptions": [],
        "final_report": None,
        "error": None,
    })

    if result.get("error"):
        print(f"ERROR: {result['error']}")
        continue

    final = result.get("final_report")
    if final:
        data = json.loads(final)
        print(f"Strategy : {data['selected_strategy']}")
        print(f"Cost     : ${data['selected_cost_usd']:,.2f}")
        print(f"Reduction: {data['cost_reduction_pct']:.1f}%")
        print(f"Exceptions: {data['exceptions_detected']}")
        print(f"\nReport:\n{data['final_report']}")
    else:
        print("No final_report generated.")

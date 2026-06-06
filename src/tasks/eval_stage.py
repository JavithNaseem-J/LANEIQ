"""
DVC pipeline evaluation stage.
Runs the full LangGraph agent pipeline on 20 representative test briefs,
computes cost-reduction statistics, and writes data/processed/eval_results.json.
"""

import json
import logging
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.WARNING)

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.agents.graph import pipeline  # noqa: E402

OUTPUT_PATH = repo_root / "data" / "processed" / "eval_results.json"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

TEST_BRIEFS = [
    "Ship 500 kg of electronics from Chennai to Jebel Ali by June 20, 2026. Prefer air freight.",
    "Move 2000 kg of textiles from NSICT Mumbai to Abu Dhabi by July 5, 2026. Sea freight.",
    "Urgent: 150 kg of perishables from Delhi ICD to Jebel Ali, must arrive by June 15, 2026.",
    "Send 3500 kg of machinery from Chennai to Jebel Ali via sea. Deadline August 1, 2026.",
    "Road shipment of 800 kg chemicals from Abu Dhabi to NSICT Mumbai by June 30, 2026.",
    "Ship 1200 kg of electronics from NSICT Mumbai to Jebel Ali by July 10, 2026. Air preferred.",
    "Move 600 kg of perishables from Chennai to Abu Dhabi urgently, deadline June 12, 2026.",
    "Transport 4000 kg of machinery from NSICT Mumbai to Jebel Ali by sea, deadline Sept 1, 2026.",
    "Ship 250 kg of textiles from Delhi ICD to Abu Dhabi by July 20, 2026. Road freight.",
    "Urgent air shipment: 100 kg of chemicals from Chennai to Jebel Ali, arrive by June 10, 2026.",
    "Move 1800 kg of electronics from Abu Dhabi to NSICT Mumbai by August 15, 2026. Sea freight.",
    "Ship 700 kg of perishables from NSICT Mumbai to Delhi ICD by June 18, 2026. Road freight.",
    "Transport 2500 kg of machinery from Jebel Ali to Chennai by sea, deadline October 1, 2026.",
    "Ship 400 kg of textiles from Chennai to Abu Dhabi by July 25, 2026. Air freight preferred.",
    "Move 900 kg of chemicals from Delhi ICD to Jebel Ali by July 1, 2026. Sea freight.",
    "Urgent: 200 kg of electronics from NSICT Mumbai to Abu Dhabi, must arrive by June 8, 2026.",
    "Transport 3000 kg of machinery from Abu Dhabi to Chennai by sea, deadline November 1, 2026.",
    "Ship 1500 kg of textiles from Jebel Ali to NSICT Mumbai by August 20, 2026. Sea freight.",
    "Move 350 kg of perishables from Chennai to Delhi ICD by June 22, 2026. Road freight.",
    "Ship 2200 kg of electronics from NSICT Mumbai to Jebel Ali by September 10, 2026. Air freight.",
]

results = []
errors = []
cost_reductions = []
start_ts = datetime.now(tz=timezone.utc).isoformat()

print(f"Running {len(TEST_BRIEFS)} evaluation briefs...")

for idx, brief in enumerate(TEST_BRIEFS, 1):
    t0 = time.time()
    try:
        result = pipeline.invoke({
            "shipment_brief": brief,
            "decomposed_tasks": [],
            "route_options": [],
            "selected_route": None,
            "exceptions": [],
            "final_report": None,
            "error": None,
        })

        elapsed = round(time.time() - t0, 2)

        if result.get("error"):
            errors.append({"brief_idx": idx, "error": result["error"]})
            print(f"  [{idx:02d}] ERROR: {result['error'][:60]}")
            continue

        final_str = result.get("final_report", "{}")
        data = json.loads(final_str) if final_str else {}

        reduction = data.get("cost_reduction_pct", 0.0)
        cost = data.get("selected_cost_usd", 0.0)
        cost_reductions.append(reduction)

        results.append({
            "brief_idx": idx,
            "brief_snippet": brief[:60] + "...",
            "selected_strategy": data.get("selected_strategy", "unknown"),
            "selected_cost_usd": cost,
            "cost_reduction_pct": reduction,
            "exceptions_detected": data.get("exceptions_detected", 0),
            "elapsed_s": elapsed,
        })
        print(f"  [{idx:02d}] OK  strategy={data.get('selected_strategy','?'):<20}  "
              f"cost=${cost:>8,.0f}  reduction={reduction:>+6.1f}%  ({elapsed}s)")

    except Exception as exc:
        elapsed = round(time.time() - t0, 2)
        errors.append({"brief_idx": idx, "error": str(exc)})
        print(f"  [{idx:02d}] EXCEPTION: {str(exc)[:60]}")

# ── Summary statistics ────────────────────────────────────────────────────────
summary = {
    "total_briefs": len(TEST_BRIEFS),
    "successful": len(results),
    "errors": len(errors),
    "cost_reduction_pct": {
        "mean": round(statistics.mean(cost_reductions), 2) if cost_reductions else None,
        "median": round(statistics.median(cost_reductions), 2) if cost_reductions else None,
        "min": round(min(cost_reductions), 2) if cost_reductions else None,
        "max": round(max(cost_reductions), 2) if cost_reductions else None,
    },
    "run_at": start_ts,
}

output = {"summary": summary, "results": results, "errors": errors}

with open(OUTPUT_PATH, "w") as f:
    json.dump(output, f, indent=2)

print(f"\nEval complete — {summary['successful']}/{summary['total_briefs']} succeeded")
print(f"Cost reduction: mean={summary['cost_reduction_pct']['mean']}%  "
      f"median={summary['cost_reduction_pct']['median']}%")
print(f"Output: {OUTPUT_PATH}")

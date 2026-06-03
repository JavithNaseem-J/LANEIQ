import json
import time
from pathlib import Path

TRANSIT_HOURS = {"sea": 336, "air": 72, "road": 48}


def solve(inputs):
    start_time = time.time()

    routes = []
    total_cost = 0.0

    for m in inputs:
        best_mode = None
        best_cost = float("inf")

        available_hours = m["time_window"]["deadline_hours"] - m["time_window"]["ready_hours"]

        for mode, cost in m["costs"].items():
            if TRANSIT_HOURS.get(mode, 999999) <= available_hours:
                if cost < best_cost:
                    best_cost = cost
                    best_mode = mode

        if best_mode is None:
            # Fallback to the fastest mode (air) if none fit
            best_mode = "air"
            best_cost = m["costs"]["air"]

        routes.append(
            {
                "shipment_id": m["shipment_id"],
                "mode": best_mode,
                "cost": best_cost,
                "transit_time": TRANSIT_HOURS.get(best_mode, 0),
            }
        )
        total_cost += best_cost

    comp_time = time.time() - start_time

    return {"routes": routes, "total_cost": round(total_cost, 2), "computation_time": comp_time}


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[2]
    input_path = repo_root / "data" / "features" / "routing_inputs.json"
    with open(input_path, "r") as f:
        data = json.load(f)

    res = solve(data[:50])
    print("Baseline Total Cost ($):", res["total_cost"])
    print("Baseline Comp Time (s):", res["computation_time"])

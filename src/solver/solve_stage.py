"""
DVC pipeline entry-point for the 'solve' stage.
Reads data/features/routing_inputs.json, runs the VRP solver in
batches of 500, and writes data/processed/routes.json.
"""

import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.solver import vrp

BATCH = 500

input_path = repo_root / "data" / "features" / "routing_inputs.json"
output_path = repo_root / "data" / "processed" / "routes.json"
output_path.parent.mkdir(parents=True, exist_ok=True)

with open(input_path) as f:
    all_inputs = json.load(f)

all_routes = []
total_cost = 0.0
total_distance = 0.0

for i in range(0, len(all_inputs), BATCH):
    chunk = all_inputs[i : i + BATCH]
    res = vrp.solve(chunk)
    all_routes.extend(res["routes"])
    total_cost += res["total_cost"]
    total_distance += res["total_distance"]
    print(
        f"Batch {i // BATCH + 1}/{-(-len(all_inputs) // BATCH)}: "
        f"{len(res['routes'])} vehicles, cost=${res['total_cost']:,.0f}"
    )

output = {
    "total_cost": round(total_cost, 2),
    "total_distance": round(total_distance, 2),
    "num_routes": len(all_routes),
    "routes": all_routes,
}

with open(output_path, "w") as f:
    json.dump(output, f, indent=2)

print(f"\nRoutes written -> {output_path}")
print(f"Total cost: ${total_cost:,.2f}  |  Total distance: {total_distance:,.0f} km  |  Vehicles: {len(all_routes)}")

import json
from pathlib import Path
from src.solver import baseline
from src.solver import vrp


def main():
    repo_root = Path(__file__).resolve().parents[2]
    input_path = repo_root / "data" / "features" / "routing_inputs.json"

    with open(input_path, "r") as f:
        data = json.load(f)

    subset = data[:50]

    print(f"Running solvers on {len(subset)} manifests...\n")

    # Run Baseline
    baseline_res = baseline.solve(subset)
    print("--- BASELINE (GREEDY) ---")
    print(f"Total Cost ($): {baseline_res['total_cost']:,.2f}")
    print(f"Computation Time: {baseline_res['computation_time']:.4f} seconds")
    print(f"Routes Generated: {len(baseline_res['routes'])} (one per shipment)\n")

    # Run VRP
    vrp_res = vrp.solve(subset)
    print("--- OR-TOOLS VRP ---")
    print(f"Total Distance (km): {vrp_res['total_distance']:,.2f}")
    print(f"Total Cost ($): {vrp_res['total_cost']:,.2f}")
    print(f"Computation Time: {vrp_res['computation_time']:.4f} seconds")
    print(f"Active Vehicles Used: {len(vrp_res['routes'])}")
    print(f"Dropped/Unroutable Nodes: {len(vrp_res['dropped_nodes'])}")


if __name__ == "__main__":
    main()

"""Standalone validation of best config across full 5000 manifests."""
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent
sys.path.insert(0, str(repo_root))

import mlflow
from src.solver import baseline, vrp
from src.solver.constraints import STRATEGIES

db_path = repo_root / "models" / "mlflow" / "mlflow.db"
mlflow.set_tracking_uri(f"sqlite:///{db_path}")
mlflow.set_experiment("FreightSolver-Optimisation")

best_cfg_obj = {**STRATEGIES["PATH_CHEAPEST_ARC"], "time_limit": 30}
BATCH = 500

with open(repo_root / "data" / "features" / "routing_inputs.json") as f:
    all_data = json.load(f)

print(f"Validating on {len(all_data)} manifests in batches of {BATCH}...")
baseline_total = 0.0
vrp_total = 0.0

for i in range(0, len(all_data), BATCH):
    chunk = all_data[i:i + BATCH]
    b = baseline.solve(chunk)
    v = vrp.solve(chunk, config=best_cfg_obj)
    baseline_total += b["total_cost"]
    vrp_total += v["total_cost"]
    b_cost = b["total_cost"]
    v_cost = v["total_cost"]
    print(f"  Batch {i // BATCH + 1}: baseline=${b_cost:,.0f}  vrp=${v_cost:,.0f}")

reduction = (baseline_total - vrp_total) / baseline_total

with mlflow.start_run(run_name="validation_5000_manifests"):
    mlflow.set_tag("strategy", "PATH_CHEAPEST_ARC")
    mlflow.set_tag("dataset_size", len(all_data))
    mlflow.log_metric("greedy_cost", baseline_total)
    mlflow.log_metric("ortools_cost", vrp_total)
    mlflow.log_metric("cost_reduction_pct", reduction * 100)

print(f"\n{'='*50}")
print(f"VALIDATION on {len(all_data)} manifests")
print(f"  Baseline cost : ${baseline_total:,.2f}")
print(f"  VRP cost      : ${vrp_total:,.2f}")
print(f"  Reduction     : {reduction*100:.1f}%")
print("  [PASS] - Target hit (>=12%)" if reduction >= 0.12 else "  [FAIL] - Below target")

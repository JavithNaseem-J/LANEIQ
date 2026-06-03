"""
Day 6 — Solver Optimisation Experiment
Sweeps all strategies × time limits, logs every run to MLflow,
identifies the best config, writes it to models/solver_configs/best_config.json,
and confirms ≥12 % cost reduction holds on all 500 manifests.
"""

import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import mlflow
import mlflow.tracking

from src.solver import baseline, vrp
from src.solver.constraints import STRATEGIES, TIME_LIMITS

TRUCK_COST_PER_KM = 1.50
MLFLOW_EXPERIMENT = "FreightSolver-Optimisation"
REDUCTION_TARGET = 0.12  # 12 %


def run_experiment(inputs_100, inputs_500):
    mlflow_dir = repo_root / "models" / "mlflow"
    mlflow_dir.mkdir(parents=True, exist_ok=True)
    db_path = mlflow_dir / "mlflow.db"
    tracking_uri = f"sqlite:///{db_path}"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(MLFLOW_EXPERIMENT)

    # ── Baseline (once, on 100 manifests) ──────────────────────────────────
    baseline_res = baseline.solve(inputs_100)
    baseline_cost = baseline_res["total_cost"]
    print(f"\nBaseline cost on 100 manifests: ${baseline_cost:,.2f}\n")

    results = []

    # ── Strategy × time-limit sweep ────────────────────────────────────────
    for strategy_name, strategy_cfg in STRATEGIES.items():
        for tl in TIME_LIMITS:
            config = {**strategy_cfg, "time_limit": tl}
            print(f"Running  strategy={strategy_name}  time_limit={tl}s ...", end=" ", flush=True)

            with mlflow.start_run(run_name=f"{strategy_name}_tl{tl}"):
                mlflow.set_tag("strategy", strategy_name)
                mlflow.set_tag("time_limit_s", tl)
                mlflow.log_metric("greedy_cost", baseline_cost)

                res = vrp.solve(inputs_100, config=config)
                vrp_cost = res["total_cost"]
                reduction = (baseline_cost - vrp_cost) / baseline_cost

                mlflow.log_metric("ortools_cost", vrp_cost)
                mlflow.log_metric("cost_reduction_pct", reduction * 100)
                mlflow.log_metric("computation_time_s", res["computation_time"])
                mlflow.log_metric("active_vehicles", len(res["routes"]))
                mlflow.log_metric("dropped_nodes", len(res["dropped_nodes"]))

            print(f"cost=${vrp_cost:,.2f}  reduction={reduction*100:.1f}%")
            results.append(
                {
                    "strategy": strategy_name,
                    "time_limit": tl,
                    "vrp_cost": vrp_cost,
                    "reduction": reduction,
                    "computation_time": res["computation_time"],
                }
            )

    # ── Find best config ───────────────────────────────────────────────────
    # Filter out zero-cost results (strategy produced no valid routes)
    valid_results = [r for r in results if r["vrp_cost"] > 0]
    if not valid_results:
        raise RuntimeError("All strategies returned zero cost — check VRP formulation.")

    # Primary: highest reduction; secondary: fastest computation
    best = max(valid_results, key=lambda r: (r["reduction"], -r["computation_time"]))

    print(f"\n{'='*60}")
    print(f"Best config -> strategy={best['strategy']}  time_limit={best['time_limit']}s")
    print(f"  VRP cost (100): ${best['vrp_cost']:,.2f}")
    print(f"  Reduction:       {best['reduction']*100:.1f}%")

    # ── Write best config to disk ──────────────────────────────────────────
    config_dir = repo_root / "models" / "solver_configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    best_config_path = config_dir / "best_config.json"

    best_config = {
        "strategy": best["strategy"],
        "time_limit": best["time_limit"],
        "truck_cost_per_km": TRUCK_COST_PER_KM,
        "vehicle_capacity_kg": 6000,
        "num_vehicles": 15,
        "reduction_on_100": round(best["reduction"] * 100, 2),
    }
    with open(best_config_path, "w") as f:
        json.dump(best_config, f, indent=2)
    print(f"\nBest config written -> {best_config_path}")

    # ── Register in MLflow Model Registry ─────────────────────────────────
    with mlflow.start_run(run_name="best_config_registration"):
        mlflow.set_tag("strategy", best["strategy"])
        mlflow.set_tag("time_limit_s", best["time_limit"])
        mlflow.log_metric("greedy_cost_100", baseline_cost)
        mlflow.log_metric("ortools_cost_100", best["vrp_cost"])
        mlflow.log_metric("reduction_pct_100", best["reduction"] * 100)
        mlflow.log_artifact(str(best_config_path))
        run_id = mlflow.active_run().info.run_id

    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
    try:
        client.create_registered_model("FreightSolver-v1")
    except Exception:
        pass  # already exists
    client.create_model_version(
        name="FreightSolver-v1",
        source=f"runs:/{run_id}/best_config.json",
        run_id=run_id,
    )
    print("Registered model 'FreightSolver-v1' in MLflow Model Registry.")

    # ── Full-dataset validation (all manifests in batches of 500) ─────────
    BATCH = 500
    print(f"\nValidating on all {len(inputs_500)} manifests in batches of {BATCH} ...")

    best_cfg_obj = {
        **STRATEGIES[best["strategy"]],
        "time_limit": best["time_limit"],
    }

    baseline_cost_total = 0.0
    vrp_cost_total = 0.0

    for i in range(0, len(inputs_500), BATCH):
        chunk = inputs_500[i : i + BATCH]
        b_res = baseline.solve(chunk)
        v_res = vrp.solve(chunk, config=best_cfg_obj)
        baseline_cost_total += b_res["total_cost"]
        vrp_cost_total += v_res["total_cost"]
        print(f"  Batch {i//BATCH + 1}: baseline=${b_res['total_cost']:,.0f}  vrp=${v_res['total_cost']:,.0f}")

    reduction_full = (baseline_cost_total - vrp_cost_total) / baseline_cost_total

    with mlflow.start_run(run_name=f"validation_{len(inputs_500)}_manifests"):
        mlflow.set_tag("strategy", best["strategy"])
        mlflow.set_tag("dataset_size", len(inputs_500))
        mlflow.log_metric("greedy_cost", baseline_cost_total)
        mlflow.log_metric("ortools_cost", vrp_cost_total)
        mlflow.log_metric("cost_reduction_pct", reduction_full * 100)

    print(f"\n{'='*60}")
    print(f"VALIDATION on {len(inputs_500)} manifests ({len(inputs_500)//BATCH} batches x {BATCH})")
    print(f"  Baseline cost : ${baseline_cost_total:,.2f}")
    print(f"  VRP cost      : ${vrp_cost_total:,.2f}")
    print(f"  Reduction     : {reduction_full*100:.1f}%")

    if reduction_full >= REDUCTION_TARGET:
        print(f"  [PASS]  Target hit (>={REDUCTION_TARGET*100:.0f}%)")
    else:
        print(f"  [FAIL]  Below target -- need >={REDUCTION_TARGET*100:.0f}%")

    return best_config


if __name__ == "__main__":
    input_path = repo_root / "data" / "features" / "routing_inputs.json"
    with open(input_path, "r") as f:
        all_data = json.load(f)

    run_experiment(all_data[:100], all_data)

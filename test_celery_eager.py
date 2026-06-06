"""
Test Celery task in CELERY_TASK_ALWAYS_EAGER mode (no Redis required).
This validates the task logic end-to-end without a running worker.
"""
import json
import os
import sys

sys.path.insert(0, "f:/DSML/LANEIQ")

# Force eager execution (in-process, no broker needed)
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "1"
os.environ["CELERY_TASK_EAGER_PROPAGATES"] = "1"

from src.tasks.celery_app import app, run_optimization

app.conf.update(task_always_eager=True, task_eager_propagates=True)

BRIEF = "Ship 500 kg of electronics from Chennai to Jebel Ali by June 20, 2026. Prefer air freight."

print("Submitting task (eager mode — in-process)...")
task = run_optimization.delay(BRIEF)
result = task.get(timeout=120)

print(f"\nTask status : {task.status}")
print(f"Result status: {result.get('status')}")
print(f"Error        : {result.get('error')}")
print(f"Strategy     : {result.get('selected_strategy')}")
print(f"Cost USD     : ${result.get('selected_cost_usd', 0):,.2f}")
print(f"Reduction    : {result.get('cost_reduction_pct', 0):.1f}%")
print(f"Exceptions   : {result.get('exceptions_detected', 0)}")

# Validate result schema
from api.schemas.result import OptimisationResult

schema_keys = {"selected_strategy", "selected_cost_usd", "cost_reduction_pct",
               "num_vehicles_used", "exceptions_detected", "final_report"}
assert schema_keys.issubset(result.keys()), f"Missing keys: {schema_keys - result.keys()}"
assert isinstance(result["final_report"], str) and len(result["final_report"]) > 0

print("\nSchema validation: PASSED")
print("Celery eager-mode task test: COMPLETE")

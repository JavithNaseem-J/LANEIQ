import json
from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.solver import baseline, vrp


def _load_inputs(n=10):
    data_path = repo_root / "data" / "features" / "routing_inputs.json"
    with open(data_path) as f:
        return json.load(f)[:n]


def test_vrp_returns_valid_structure():
    """VRP result must contain routes, total_cost, total_distance, computation_time, dropped_nodes."""
    inputs = _load_inputs(10)
    res = vrp.solve(inputs)

    assert isinstance(res, dict)
    assert "routes" in res
    assert "total_cost" in res
    assert "total_distance" in res
    assert "computation_time" in res
    assert "dropped_nodes" in res


def test_vrp_routes_have_required_fields():
    """Each route must have vehicle_id, distance_km, and shipments list."""
    inputs = _load_inputs(10)
    res = vrp.solve(inputs)

    for route in res["routes"]:
        assert "vehicle_id" in route
        assert "distance_km" in route
        assert "shipments" in route
        assert isinstance(route["shipments"], list)


def test_vrp_cost_less_than_greedy():
    """VRP total cost must show at least 12% reduction vs greedy on 50 manifests."""
    inputs = _load_inputs(50)
    baseline_res = baseline.solve(inputs)
    vrp_res = vrp.solve(inputs)

    reduction = (baseline_res["total_cost"] - vrp_res["total_cost"]) / baseline_res["total_cost"]
    assert reduction >= 0.12, (
        f"VRP cost reduction {reduction*100:.1f}% is below the 12% target. "
        f"Baseline=${baseline_res['total_cost']:,.2f}  VRP=${vrp_res['total_cost']:,.2f}"
    )


def test_vrp_cost_is_non_negative():
    """Total cost must always be >= 0."""
    inputs = _load_inputs(10)
    res = vrp.solve(inputs)
    assert res["total_cost"] >= 0
    assert res["total_distance"] >= 0


def test_vrp_computation_time_is_positive():
    """Computation time must be recorded and positive."""
    inputs = _load_inputs(10)
    res = vrp.solve(inputs)
    assert res["computation_time"] > 0

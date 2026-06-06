"""
Day 27 — SHAP analysis for OR-Tools cost explainability.
Trains lightweight XGBoost on routing features, generates SHAP bar chart.
Output: data/processed/shap_values.json
"""
import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTES_PATH = REPO_ROOT / "data" / "processed" / "routes.json"
OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "shap_values.json"

FEATURES = ["distance_km", "weight_kg", "cost_sea", "cost_air", "cost_road"]


def run_shap_analysis() -> dict:
    """Train XGBoost on route data and compute SHAP feature importances."""
    try:
        import shap
        import xgboost as xgb
    except ImportError:
        logger.warning("shap/xgboost not installed — skipping SHAP analysis.")
        return {"error": "shap or xgboost not installed"}

    if not ROUTES_PATH.exists():
        logger.warning("routes.json not found — skipping.")
        return {"error": "no_routes_data"}

    with open(ROUTES_PATH) as f:
        routes_data = json.load(f)

    routes = routes_data.get("routes", [])
    if not routes:
        return {"error": "empty_routes"}

    # Build feature matrix
    rows = []
    targets = []
    for route in routes:
        dist = route.get("distance_km", 0)
        weight = route.get("weight_kg", 0)
        cost = route.get("cost", 0)
        rows.append([
            dist,
            weight,
            weight * 1.2,  # sea
            weight * 4.5,  # air
            weight * 2.0,  # road
        ])
        targets.append(cost)

    X = np.array(rows)
    y = np.array(targets)

    model = xgb.XGBRegressor(n_estimators=100, max_depth=4, random_state=42, verbosity=0)
    model.fit(X, y)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    mean_abs_shap = np.abs(shap_values).mean(axis=0).tolist()

    result = {
        "features": FEATURES,
        "mean_abs_shap": mean_abs_shap,
        "ranked": sorted(
            zip(FEATURES, mean_abs_shap),
            key=lambda x: x[1],
            reverse=True,
        ),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump({"features": FEATURES, "mean_abs_shap": mean_abs_shap}, f, indent=2)

    logger.info("[shap] Top feature: %s (%.3f)", result["ranked"][0][0], result["ranked"][0][1])
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_shap_analysis()
    if "ranked" in result:
        print("\nSHAP Feature Importance:")
        for feat, val in result["ranked"]:
            print(f"  {feat:<25} {val:.3f}")

"""
Day 19 — Evidently drift detection.
Compares reference routing_inputs vs current batch, generates HTML report.
"""
import json
import logging
from pathlib import Path

import pandas as pd
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_PATH = REPO_ROOT / "data" / "processed" / "reference.json"
CURRENT_PATH = REPO_ROOT / "data" / "features" / "routing_inputs.json"
REPORT_PATH = REPO_ROOT / "data" / "processed" / "drift_report.html"

DRIFT_THRESHOLD = 0.30  # alert if >30% of features drift

NUMERIC_COLS = ["distance_km", "weight_kg", "costs_sea", "costs_air", "costs_road",
                "time_window_deadline_hours"]


def _load_dataframe(path: Path) -> pd.DataFrame:
    with open(path) as f:
        records = json.load(f)
    rows = []
    for r in records:
        rows.append({
            "distance_km": r.get("distance_km", 0),
            "weight_kg": r.get("weight_kg", 0),
            "costs_sea": r.get("costs", {}).get("sea", 0),
            "costs_air": r.get("costs", {}).get("air", 0),
            "costs_road": r.get("costs", {}).get("road", 0),
            "time_window_deadline_hours": r.get("time_window", {}).get("deadline_hours", 0),
        })
    return pd.DataFrame(rows)


def run_drift_report() -> dict:
    """
    Load reference and current datasets, run Evidently report,
    save HTML, return summary dict.
    """
    if not REFERENCE_PATH.exists():
        logger.warning("[drift] reference.json not found — skipping.")
        return {"drift_detected": False, "error": "no_reference"}

    if not CURRENT_PATH.exists():
        logger.warning("[drift] routing_inputs.json not found — skipping.")
        return {"drift_detected": False, "error": "no_current"}

    reference = _load_dataframe(REFERENCE_PATH)
    current = _load_dataframe(CURRENT_PATH)

    # Limit current to last 500 rows for performance
    current = current.tail(500)

    column_mapping = ColumnMapping(numerical_features=NUMERIC_COLS)

    report = Report(metrics=[DataDriftPreset(), DataQualityPreset()])
    report.run(reference_data=reference, current_data=current, column_mapping=column_mapping)

    # Save HTML
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report.save_html(str(REPORT_PATH))
    logger.info("[drift] report saved to %s", REPORT_PATH)

    # Extract drift summary
    report_dict = report.as_dict()
    drift_results = report_dict.get("metrics", [])

    drifted_features = 0
    total_features = 0
    for metric in drift_results:
        result = metric.get("result", {})
        if "number_of_drifted_columns" in result:
            drifted_features = result["number_of_drifted_columns"]
            total_features = result.get("number_of_columns", 1)
            break

    drift_rate = drifted_features / max(total_features, 1)
    drift_detected = drift_rate > DRIFT_THRESHOLD

    summary = {
        "drift_detected": drift_detected,
        "drifted_features": drifted_features,
        "total_features": total_features,
        "drift_rate": round(drift_rate, 3),
        "threshold": DRIFT_THRESHOLD,
        "report_path": str(REPORT_PATH),
    }

    if drift_detected:
        logger.warning("[drift] DRIFT DETECTED — %.0f%% of features drifted (threshold %.0f%%)",
                       drift_rate * 100, DRIFT_THRESHOLD * 100)
    else:
        logger.info("[drift] No significant drift detected (%.0f%% features drifted)",
                    drift_rate * 100)

    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_drift_report()
    print(json.dumps(result, indent=2))

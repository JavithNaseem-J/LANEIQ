"""
Day 25 — Scheduled drift detection for live deployment.
Runs as a cron job on EC2: */30 * * * * python /app/src/monitoring/scheduled_drift.py
Logs CloudWatch metric 'drift_detected' (0 or 1).
"""
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.monitoring.drift import run_drift_report  # noqa: E402


def publish_cloudwatch_metric(drift_detected: bool) -> None:
    """Publish drift_detected metric to CloudWatch (requires boto3 + IAM role)."""
    try:
        import boto3
        cw = boto3.client("cloudwatch", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        cw.put_metric_data(
            Namespace="LANEIQ/Monitoring",
            MetricData=[{
                "MetricName": "DriftDetected",
                "Value": 1.0 if drift_detected else 0.0,
                "Unit": "None",
            }],
        )
        logger.info("[scheduled_drift] CloudWatch metric published: drift_detected=%s", drift_detected)
    except Exception as exc:
        logger.warning("[scheduled_drift] CloudWatch publish failed (non-fatal): %s", exc)


if __name__ == "__main__":
    logger.info("[scheduled_drift] Running drift check...")
    summary = run_drift_report()
    publish_cloudwatch_metric(summary.get("drift_detected", False))
    print(json.dumps(summary, indent=2))

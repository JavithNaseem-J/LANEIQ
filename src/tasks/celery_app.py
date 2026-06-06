"""
Celery application for LANEIQ async task execution.

Broker / backend: Redis (configured via REDIS_URL in settings).
Fallback: if Redis is unavailable, tasks run in-process via CELERY_TASK_ALWAYS_EAGER=1.
"""

import json
import logging

from celery import Celery

from config.settings import settings

logger = logging.getLogger(__name__)

app = Celery(
    "laneiq",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Retry connection rather than crashing on broker unavailability
    broker_connection_retry_on_startup=True,
)


@app.task(name="laneiq.run_optimization", bind=True, max_retries=2)
def run_optimization(self, shipment_brief: str) -> dict:
    """
    Async Celery task: runs the full 4-node LangGraph pipeline.

    Args:
        shipment_brief: Free-text shipment description from the user.

    Returns:
        Serialised OptimisationResult dict (same schema as api/schemas/result.py).
    """
    # Import here to avoid circular imports at module load time
    from src.agents.graph import pipeline

    logger.info("[run_optimization] starting task for brief: %s", shipment_brief[:80])

    try:
        initial_state = {
            "shipment_brief": shipment_brief,
            "decomposed_tasks": [],
            "route_options": [],
            "selected_route": None,
            "exceptions": [],
            "final_report": None,
            "error": None,
        }

        result = pipeline.invoke(initial_state)

        if result.get("error"):
            logger.error("[run_optimization] pipeline returned error: %s", result["error"])
            return {
                "status": "error",
                "error": result["error"],
                "final_report": None,
            }

        final_report_str = result.get("final_report") or ""
        final_report_data = json.loads(final_report_str) if final_report_str else {}

        logger.info("[run_optimization] task complete — cost $%.2f",
                    final_report_data.get("selected_cost_usd", 0))

        return {
            "status": "success",
            "error": None,
            **final_report_data,
        }

    except Exception as exc:
        logger.error("[run_optimization] unexpected error: %s", exc)
        raise self.retry(exc=exc, countdown=5)

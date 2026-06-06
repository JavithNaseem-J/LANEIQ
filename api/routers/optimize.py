import logging

from fastapi import APIRouter, Request
from api.schemas.shipment import ShipmentRequest
from api.middleware.rate_limit import limiter
from src.tasks.celery_app import run_optimization

logger = logging.getLogger(__name__)
router = APIRouter(tags=["optimize"])


@router.post("/optimize")
@limiter.limit("10/minute")
def submit_optimization(request: Request, body: ShipmentRequest) -> dict:
    """
    Submit a shipment brief for async optimisation.
    Returns a Celery task_id immediately — poll /status/{task_id} for the result.
    """
    task = run_optimization.delay(body.shipment_brief)
    logger.info("[optimize] task submitted: %s  brief=%s", task.id, body.shipment_brief[:60])
    return {"task_id": task.id, "status": "queued"}

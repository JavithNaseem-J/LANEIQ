import logging

from celery.result import AsyncResult
from fastapi import APIRouter

from src.tasks.celery_app import app as celery_app

logger = logging.getLogger(__name__)
router = APIRouter(tags=["status"])


@router.get("/status/{task_id}")
def get_status(task_id: str) -> dict:
    """
    Poll the status of a submitted optimisation task.
    Returns task state and result when complete.
    """
    result: AsyncResult = celery_app.AsyncResult(task_id)
    state = result.state

    if state == "PENDING":
        return {"task_id": task_id, "state": "pending", "result": None}
    elif state == "SUCCESS":
        return {"task_id": task_id, "state": "success", "result": result.get()}
    elif state == "FAILURE":
        return {"task_id": task_id, "state": "failure", "result": {"error": str(result.info)}}
    else:
        return {"task_id": task_id, "state": state.lower(), "result": None}

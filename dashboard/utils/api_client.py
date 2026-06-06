"""LANEIQ Dashboard — shared API client."""
import os
import time

import httpx

API_URL = os.environ.get("API_URL", "http://localhost:8000")
POLL_INTERVAL = 2  # seconds
POLL_TIMEOUT = 120  # seconds


def submit_optimization(brief: str) -> str:
    """Submit brief to /optimize, return task_id."""
    r = httpx.post(f"{API_URL}/optimize", json={"shipment_brief": brief}, timeout=10)
    r.raise_for_status()
    return r.json()["task_id"]


def poll_status(task_id: str, timeout: int = POLL_TIMEOUT) -> dict:
    """Poll /status/{task_id} until SUCCESS or FAILURE, return result dict."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = httpx.get(f"{API_URL}/status/{task_id}", timeout=10)
        r.raise_for_status()
        data = r.json()
        if data["state"] in ("success", "failure"):
            return data
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Task {task_id} did not complete in {timeout}s")


def check_health() -> bool:
    try:
        r = httpx.get(f"{API_URL}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False

"""
API integration tests — uses httpx.TestClient (no real Celery broker needed).
The Celery task is patched to return a canned result synchronously.
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app, raise_server_exceptions=False)

VALID_BRIEF = "Ship 500 kg of electronics from Chennai to Jebel Ali by June 20, 2026."
SHORT_BRIEF = "Ship"
LONG_BRIEF = "x" * 501

CANNED_RESULT = {
    "status": "success",
    "selected_strategy": "greedy_baseline",
    "selected_cost_usd": 1000.0,
    "cost_reduction_pct": 0.0,
    "num_vehicles_used": 1,
    "exceptions_detected": 0,
    "exception_summaries": [],
    "all_options": [],
    "final_report": "Test report.",
    "error": None,
}


class TestHealth:
    def test_health_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_body(self):
        r = client.get("/health")
        assert r.json()["status"] == "ok"
        assert "version" in r.json()


class TestOptimize:
    def _mock_task(self):
        mock = MagicMock()
        mock.id = "test-task-id-1234"
        return mock

    def test_valid_brief_returns_task_id(self):
        with patch("api.routers.optimize.run_optimization") as mock_task:
            mock_task.delay.return_value = self._mock_task()
            r = client.post("/optimize", json={"shipment_brief": VALID_BRIEF})
        assert r.status_code == 200
        assert "task_id" in r.json()

    def test_short_brief_returns_422(self):
        r = client.post("/optimize", json={"shipment_brief": SHORT_BRIEF})
        assert r.status_code == 422

    def test_long_brief_returns_422(self):
        r = client.post("/optimize", json={"shipment_brief": LONG_BRIEF})
        assert r.status_code == 422

    def test_empty_brief_returns_422(self):
        r = client.post("/optimize", json={"shipment_brief": ""})
        assert r.status_code == 422

    def test_missing_body_returns_422(self):
        r = client.post("/optimize", json={})
        assert r.status_code == 422

    def test_blank_whitespace_brief_returns_422(self):
        r = client.post("/optimize", json={"shipment_brief": "   "})
        assert r.status_code == 422


class TestStatus:
    def test_unknown_task_returns_pending(self):
        with patch("api.routers.status.celery_app") as mock_app:
            mock_result = MagicMock()
            mock_result.state = "PENDING"
            mock_app.AsyncResult.return_value = mock_result
            r = client.get("/status/non-existent-task-id")
        assert r.status_code == 200
        assert r.json()["state"] == "pending"

    def test_success_task_returns_result(self):
        with patch("api.routers.status.celery_app") as mock_app:
            mock_result = MagicMock()
            mock_result.state = "SUCCESS"
            mock_result.get.return_value = CANNED_RESULT
            mock_app.AsyncResult.return_value = mock_result
            r = client.get("/status/test-task-id-1234")
        assert r.status_code == 200
        data = r.json()
        assert data["state"] == "success"
        assert data["result"]["selected_strategy"] == "greedy_baseline"

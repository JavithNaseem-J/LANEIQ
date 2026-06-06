

class TestExceptionNode:
    """Tests for the Exception Agent node."""

    def _routed_state(self) -> dict:
        """Build a state with decomposed_tasks + selected_route via Planner + Route."""
        from src.agents.planner import planner_node
        from src.agents.route import route_node

        brief = "Ship 1200 kg of machinery from Chennai to Jebel Ali by July 15, 2026. Sea freight."
        s1 = planner_node({"shipment_brief": brief, "decomposed_tasks": [], "error": None})
        s2 = route_node(s1)
        return s2

    def test_exception_returns_exceptions_list(self):
        """Exception node must always return a list in state['exceptions']."""
        from src.agents.exception import exception_node

        state = self._routed_state()
        result = exception_node(state)
        assert isinstance(result["exceptions"], list)

    def test_exception_propagates_upstream_error(self):
        """Exception Agent must skip if upstream error is set."""
        from src.agents.exception import exception_node

        state = {"error": "upstream failure", "selected_route": None, "decomposed_tasks": []}
        result = exception_node(state)
        assert result["error"] == "upstream failure"

    def test_exception_no_error_on_clean_run(self):
        """Exception node must not set error state on a normal routed state."""
        from src.agents.exception import exception_node

        state = self._routed_state()
        result = exception_node(state)
        assert result.get("error") is None

    def test_vessel_api_synthetic_delay_rate(self):
        """Synthetic ETA must produce ~20% delays across many shipment IDs."""
        from datetime import datetime, timezone
        from src.data.vessel_api import _synthetic_eta

        deadline = datetime(2026, 7, 15, tzinfo=timezone.utc)
        delayed = sum(
            1 for i in range(100)
            if _synthetic_eta(deadline, f"SHP-LOAD-{i:04d}")["delayed"]
        )
        assert 10 <= delayed <= 30, f"Delay rate {delayed}% outside 10-30% tolerance"

    def test_vessel_api_non_sea_mode_always_on_time(self):
        """Air and road routes must always be reported as on-time."""
        from datetime import datetime, timezone
        from src.data.vessel_api import get_vessel_eta

        deadline = datetime(2026, 7, 15, tzinfo=timezone.utc)
        for mode in ("air", "road"):
            result = get_vessel_eta("TEST-001", "Jebel Ali", deadline, mode=mode)
            assert not result["delayed"], f"Mode {mode} should never be delayed"

    def test_synthetic_delay_is_deterministic(self):
        """Same shipment_id must always produce the same delay result."""
        from datetime import datetime, timezone
        from src.data.vessel_api import _synthetic_eta

        deadline = datetime(2026, 7, 15, tzinfo=timezone.utc)
        r1 = _synthetic_eta(deadline, "SHP-TEST-0000")
        r2 = _synthetic_eta(deadline, "SHP-TEST-0000")
        assert r1["delayed"] == r2["delayed"]
        assert r1["delay_hours"] == r2["delay_hours"]

    def test_full_graph_planner_route_exception(self):
        """End-to-end: full 4-node graph must run without error and have exceptions list."""
        from src.agents.graph import pipeline

        initial_state = {
            "shipment_brief": (
                "Ship 1200 kg of machinery from Chennai to Jebel Ali by July 15, 2026. Sea freight."
            ),
            "decomposed_tasks": [],
            "route_options": [],
            "selected_route": None,
            "exceptions": [],
            "final_report": None,
            "error": None,
        }
        result = pipeline.invoke(initial_state)
        assert result.get("error") is None
        assert isinstance(result["exceptions"], list)

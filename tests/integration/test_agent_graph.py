"""
Integration tests for the LangGraph agent pipeline.
These tests make a live Groq API call — they are intentionally
separate from unit tests so CI can skip them when no API key is set.
"""

from src.agents.graph import pipeline
from src.agents.planner import planner_node


HARDCODED_BRIEF = (
    "Ship 500 kg of electronics from Chennai to Jebel Ali by June 20, 2026. Prefer air freight."
)

REQUIRED_TASK_KEYS = {
    "origin_port",
    "destination_port",
    "cargo_type",
    "cargo_weight_kg",
    "deadline",
    "preferred_mode",
}


class TestPlannerNode:
    """Tests for the Planner Agent node in isolation."""

    def test_planner_returns_non_empty_tasks(self):
        """Planner must extract at least one task from a clear brief."""
        state = {"shipment_brief": HARDCODED_BRIEF, "decomposed_tasks": [], "error": None}
        result = planner_node(state)
        assert result.get("error") is None, f"Planner returned error: {result.get('error')}"
        assert len(result["decomposed_tasks"]) > 0

    def test_planner_task_has_required_fields(self):
        """Each extracted task must contain all required schema fields."""
        state = {"shipment_brief": HARDCODED_BRIEF, "decomposed_tasks": [], "error": None}
        result = planner_node(state)
        task = result["decomposed_tasks"][0]
        missing = REQUIRED_TASK_KEYS - set(task.keys())
        assert not missing, f"Missing fields in extracted task: {missing}"

    def test_planner_extracts_correct_origin(self):
        """Planner must extract the correct origin port."""
        state = {"shipment_brief": HARDCODED_BRIEF, "decomposed_tasks": [], "error": None}
        result = planner_node(state)
        assert result["decomposed_tasks"][0]["origin_port"] == "Chennai"

    def test_planner_extracts_correct_destination(self):
        """Planner must extract the correct destination port."""
        state = {"shipment_brief": HARDCODED_BRIEF, "decomposed_tasks": [], "error": None}
        result = planner_node(state)
        assert result["decomposed_tasks"][0]["destination_port"] == "Jebel Ali"

    def test_planner_handles_empty_brief(self):
        """Planner must set error when shipment_brief is empty."""
        state = {"shipment_brief": "", "decomposed_tasks": [], "error": None}
        result = planner_node(state)
        assert result["error"] is not None
        assert result["decomposed_tasks"] == []

    def test_planner_propagates_upstream_error(self):
        """Planner must skip processing if an upstream error already exists."""
        state = {
            "shipment_brief": HARDCODED_BRIEF,
            "decomposed_tasks": [],
            "error": "upstream failure",
        }
        result = planner_node(state)
        assert result["error"] == "upstream failure"
        assert result["decomposed_tasks"] == []


class TestFullGraphWithPlanner:
    """End-to-end graph traversal with the real Planner node."""

    def test_graph_traversal_populates_decomposed_tasks(self):
        """Full graph run must populate decomposed_tasks via the Planner node."""
        initial_state = {
            "shipment_brief": HARDCODED_BRIEF,
            "decomposed_tasks": [],
            "route_options": [],
            "selected_route": None,
            "exceptions": [],
            "final_report": None,
            "error": None,
        }
        result = pipeline.invoke(initial_state)
        assert result.get("error") is None
        assert isinstance(result["decomposed_tasks"], list)
        assert len(result["decomposed_tasks"]) > 0


class TestRouteNode:
    """Tests for the Route Agent node."""

    def _planner_state(self) -> dict:
        """Run the real Planner to get a valid state with decomposed_tasks."""
        from src.agents.planner import planner_node

        state = {"shipment_brief": HARDCODED_BRIEF, "decomposed_tasks": [], "error": None}
        return planner_node(state)

    def test_route_populates_route_options(self):
        """Route Agent must return at least two route options (baseline + vrp)."""
        from src.agents.route import route_node

        state = self._planner_state()
        result = route_node(state)
        assert result.get("error") is None, f"Route Agent returned error: {result.get('error')}"
        assert isinstance(result["route_options"], list)
        assert len(result["route_options"]) >= 2

    def test_route_populates_selected_route(self):
        """selected_route must be non-None and have a total_cost."""
        from src.agents.route import route_node

        state = self._planner_state()
        result = route_node(state)
        assert result["selected_route"] is not None
        assert "total_cost" in result["selected_route"]
        assert result["selected_route"]["total_cost"] >= 0

    def test_route_cost_reduction_is_a_float(self):
        """VRP cost_reduction_vs_baseline must be a numeric value (can be negative on single shipment)."""
        from src.agents.route import route_node

        state = self._planner_state()
        result = route_node(state)
        vrp_option = next(r for r in result["route_options"] if r["strategy"] == "ortools_vrp")
        # On a single shipment the truck flat-rate can exceed per-kg greedy cost;
        # the assertion is that the field exists and is a number, not that it's positive.
        assert isinstance(vrp_option["cost_reduction_vs_baseline"], (int, float))

    def test_route_propagates_upstream_error(self):
        """Route Agent must skip if upstream error is set."""
        from src.agents.route import route_node

        state = {
            "decomposed_tasks": [],
            "error": "upstream failure",
            "route_options": [],
            "selected_route": None,
        }
        result = route_node(state)
        assert result["error"] == "upstream failure"

    def test_full_graph_planner_to_route(self):
        """End-to-end: Planner -> Route must populate both decomposed_tasks and selected_route."""
        initial_state = {
            "shipment_brief": HARDCODED_BRIEF,
            "decomposed_tasks": [],
            "route_options": [],
            "selected_route": None,
            "exceptions": [],
            "final_report": None,
            "error": None,
        }
        result = pipeline.invoke(initial_state)
        assert result.get("error") is None, f"Pipeline error: {result.get('error')}"
        assert len(result["decomposed_tasks"]) > 0
        assert result["selected_route"] is not None
        assert result["selected_route"]["total_cost"] >= 0



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


class TestReportNode:
    """Tests for the Report Agent node and schema validation."""

    def _full_state(self, brief: str = None) -> dict:
        """Run Planner + Route + Exception to get a fully populated state."""
        from src.agents.exception import exception_node
        from src.agents.planner import planner_node
        from src.agents.route import route_node

        if brief is None:
            brief = "Ship 500 kg of electronics from Chennai to Jebel Ali by June 20, 2026. Prefer air freight."
        s1 = planner_node({"shipment_brief": brief, "decomposed_tasks": [], "error": None})
        s2 = route_node(s1)
        s3 = exception_node(s2)
        return s3

    def test_report_returns_non_empty_final_report(self):
        """Report Agent must produce a non-empty final_report string."""
        from src.agents.report import report_node

        state = self._full_state()
        result = report_node(state)
        assert result.get("error") is None, f"Report error: {result.get('error')}"
        assert isinstance(result["final_report"], str)
        assert len(result["final_report"]) > 50

    def test_report_final_report_is_valid_json(self):
        """final_report must be a valid JSON string (serialised OptimisationResult)."""
        import json
        from src.agents.report import report_node

        state = self._full_state()
        result = report_node(state)
        data = json.loads(result["final_report"])
        assert "selected_strategy" in data
        assert "selected_cost_usd" in data
        assert "final_report" in data

    def test_report_schema_validates(self):
        """final_report JSON must validate against OptimisationResult schema."""
        import json
        from src.agents.report import report_node
        from api.schemas.result import OptimisationResult

        state = self._full_state()
        result = report_node(state)
        data = json.loads(result["final_report"])
        parsed = OptimisationResult(**data)
        assert parsed.selected_cost_usd >= 0
        assert isinstance(parsed.final_report, str)
        assert len(parsed.final_report) > 0

    def test_report_propagates_upstream_error(self):
        """Report Agent must skip if upstream error is set."""
        from src.agents.report import report_node

        state = {"error": "upstream failure", "final_report": None}
        result = report_node(state)
        assert result["error"] == "upstream failure"
        assert result.get("final_report") is None

    def test_full_graph_all_four_nodes(self):
        """End-to-end: all 4 nodes must produce a schema-valid final_report."""
        import json
        from src.agents.graph import pipeline
        from api.schemas.result import OptimisationResult

        initial_state = {
            "shipment_brief": "Move 2000 kg of textiles from NSICT Mumbai to Abu Dhabi by July 5, 2026. Sea freight.",
            "decomposed_tasks": [],
            "route_options": [],
            "selected_route": None,
            "exceptions": [],
            "final_report": None,
            "error": None,
        }
        result = pipeline.invoke(initial_state)
        assert result.get("error") is None, f"Pipeline error: {result.get('error')}"
        assert isinstance(result["final_report"], str)
        data = json.loads(result["final_report"])
        parsed = OptimisationResult(**data)
        assert len(parsed.final_report) > 0
        assert isinstance(parsed.exceptions_detected, int)



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

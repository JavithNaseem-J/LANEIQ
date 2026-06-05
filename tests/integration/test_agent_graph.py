"""
Integration tests for the LangGraph agent pipeline.
These tests make a live Groq API call — they are intentionally
separate from unit tests so CI can skip them when no API key is set.
"""

import pytest
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

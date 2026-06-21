from src.agents.state import AgentState


REQUIRED_KEYS = {
    "shipment_brief",
    "decomposed_tasks",
    "route_options",
    "selected_route",
    "exceptions",
    "final_report",
    "error",
}


def _make_full_state() -> AgentState:
    return AgentState(
        shipment_brief="Ship 500 kg of electronics from Chennai to Jebel Ali by June 20.",
        decomposed_tasks=[],
        route_options=[],
        selected_route=None,
        exceptions=[],
        final_report=None,
        error=None,
    )


def test_state_instantiation():
    """AgentState can be created as a plain dict with all required keys."""
    state = _make_full_state()
    assert isinstance(state, dict)


def test_all_required_keys_present():
    """All required state keys must be present."""
    state = _make_full_state()
    assert REQUIRED_KEYS.issubset(state.keys()), (
        f"Missing keys: {REQUIRED_KEYS - state.keys()}"
    )


def test_shipment_brief_is_string():
    state = _make_full_state()
    assert isinstance(state["shipment_brief"], str)


def test_list_fields_are_lists():
    state = _make_full_state()
    assert isinstance(state["decomposed_tasks"], list)
    assert isinstance(state["route_options"], list)
    assert isinstance(state["exceptions"], list)


def test_optional_fields_default_to_none():
    state = _make_full_state()
    assert state["selected_route"] is None
    assert state["final_report"] is None
    assert state["error"] is None


def test_partial_state_allowed():
    """total=False means a partial state (only shipment_brief) is valid."""
    partial: AgentState = {"shipment_brief": "Test brief"}
    assert partial["shipment_brief"] == "Test brief"

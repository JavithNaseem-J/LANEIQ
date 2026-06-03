import json
from pathlib import Path

def test_routing_inputs_schema():
    data_path = Path(__file__).resolve().parents[2] / "data" / "features" / "routing_inputs.json"
    assert data_path.exists(), "routing_inputs.json does not exist"
    
    with open(data_path, "r") as f:
        data = json.load(f)
        
    assert isinstance(data, list)
    assert len(data) > 0
    
    first = data[0]
    expected_keys = {"shipment_id", "origin", "destination", "distance_km", "time_window", "weight_kg", "costs"}
    assert set(first.keys()) == expected_keys
    
    assert "ready_hours" in first["time_window"]
    assert "deadline_hours" in first["time_window"]
    
    assert "sea" in first["costs"]
    assert "air" in first["costs"]
    assert "road" in first["costs"]
    
    assert isinstance(first["distance_km"], (int, float))

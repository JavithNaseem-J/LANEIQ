import pytest
from src.data.generator import generate_shipments
from src.data.validator import ShipmentManifest
from pydantic import ValidationError

def test_generator_schema_validity():
    """Validate generator output against Pydantic schema on 100 records."""
    records = generate_shipments(100)
    assert len(records) == 100
    
    for record in records:
        try:
            ShipmentManifest.model_validate(record)
        except ValidationError as e:
            pytest.fail(f"Schema validation failed for record: {record}\nError: {e}")

def test_generator_logic():
    """Test standard logic invariants."""
    records = generate_shipments(10)
    for record in records:
        assert record["origin_port"] != record["destination_port"]
        assert record["cargo_weight_kg"] > 0
        assert record["estimated_value_usd"] > 0
        assert record["ready_datetime"] < record["deadline_datetime"]

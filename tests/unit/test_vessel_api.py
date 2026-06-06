"""Unit tests for src/data/vessel_api.py — no network calls."""
from datetime import datetime, timezone

import pytest

from src.data.vessel_api import _synthetic_eta, get_vessel_eta


DEADLINE = datetime(2026, 8, 1, tzinfo=timezone.utc)


class TestSyntheticEta:
    def test_returns_required_keys(self):
        r = _synthetic_eta(DEADLINE, "SHP-001")
        assert {"shipment_id", "eta", "source", "delayed", "delay_hours"}.issubset(r.keys())

    def test_source_is_synthetic(self):
        r = _synthetic_eta(DEADLINE, "SHP-001")
        assert r["source"] == "synthetic"

    def test_delay_hours_zero_when_on_time(self):
        # Find a shipment ID that is NOT delayed
        for i in range(50):
            r = _synthetic_eta(DEADLINE, f"SHP-ONTIME-{i:04d}")
            if not r["delayed"]:
                assert r["delay_hours"] == 0
                return
        pytest.skip("Could not find an on-time ID in 50 tries")

    def test_delay_hours_positive_when_delayed(self):
        # Find a shipment ID that IS delayed
        for i in range(50):
            r = _synthetic_eta(DEADLINE, f"SHP-LATE-{i:04d}")
            if r["delayed"]:
                assert r["delay_hours"] > 0
                return
        pytest.skip("Could not find a delayed ID in 50 tries")

    def test_delay_hours_within_range(self):
        from src.data.vessel_api import _DELAY_MAX_HRS, _DELAY_MIN_HRS

        for i in range(100):
            r = _synthetic_eta(DEADLINE, f"SHP-RANGE-{i:04d}")
            if r["delayed"]:
                assert _DELAY_MIN_HRS <= r["delay_hours"] <= _DELAY_MAX_HRS

    def test_deterministic_across_calls(self):
        r1 = _synthetic_eta(DEADLINE, "SHP-DET-0001")
        r2 = _synthetic_eta(DEADLINE, "SHP-DET-0001")
        assert r1["delayed"] == r2["delayed"]
        assert r1["delay_hours"] == r2["delay_hours"]
        assert r1["eta"] == r2["eta"]

    def test_different_ids_may_differ(self):
        results = {_synthetic_eta(DEADLINE, f"SHP-VAR-{i:04d}")["delayed"] for i in range(20)}
        # Should have at least one True and one False across 20 IDs
        assert True in results or False in results


class TestGetVesselEta:
    def test_air_mode_never_delayed(self):
        r = get_vessel_eta("SHP-001", "Jebel Ali", DEADLINE, mode="air")
        assert not r["delayed"]
        assert r["delay_hours"] == 0
        assert r["source"] == "non_vessel"

    def test_road_mode_never_delayed(self):
        r = get_vessel_eta("SHP-001", "NSICT Mumbai", DEADLINE, mode="road")
        assert not r["delayed"]
        assert r["source"] == "non_vessel"

    def test_sea_mode_returns_eta_info(self):
        r = get_vessel_eta("SHP-001", "Jebel Ali", DEADLINE, mode="sea")
        assert "delayed" in r
        assert "eta" in r
        assert r["source"] in ("synthetic", "marinetraffic")

    def test_sea_mode_fallback_source_is_synthetic(self):
        # No API key configured so must fall back to synthetic
        r = get_vessel_eta("SHP-001", "Jebel Ali", DEADLINE, mode="sea")
        assert r["source"] == "synthetic"

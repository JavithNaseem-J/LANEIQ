import logging
import random
from datetime import datetime, timedelta

import requests

from config.settings import settings

logger = logging.getLogger(__name__)

# Probability that a sea route is synthetically delayed
_SYNTHETIC_DELAY_RATE = 0.20
# Delay range in hours when a synthetic delay is generated
_DELAY_MIN_HRS = 24
_DELAY_MAX_HRS = 72

# MarineTraffic free-tier base URL
_MARINETRAFFIC_BASE = "https://services.marinetraffic.com/api/expectedarrivals"


def _synthetic_eta(deadline_dt: datetime, shipment_id: str) -> dict:
    """
    Generate a synthetic ETA event.
    Uses seeded randomness so the same shipment always produces the same result
    across a single pipeline run (deterministic for testing).
    """
    rng = random.Random(hash(shipment_id) % (2**32))
    delayed = rng.random() < _SYNTHETIC_DELAY_RATE
    if delayed:
        delay_hours = rng.randint(_DELAY_MIN_HRS, _DELAY_MAX_HRS)
        eta = deadline_dt + timedelta(hours=delay_hours)
    else:
        # Arrive 2-12 hours before deadline
        buffer_hours = rng.randint(2, 12)
        eta = deadline_dt - timedelta(hours=buffer_hours)

    return {
        "shipment_id": shipment_id,
        "eta": eta.isoformat(),
        "source": "synthetic",
        "delayed": delayed,
        "delay_hours": delay_hours if delayed else 0,
    }


def get_vessel_eta(shipment_id: str, destination_port: str, deadline_dt: datetime, mode: str = "sea") -> dict:
    """
    Return expected arrival info for a shipment.

    For non-sea modes (air / road) there is no vessel tracking — returns on-time by default.
    For sea mode:
      1. Tries the MarineTraffic API if a key is configured.
      2. Falls back to synthetic delay simulation on any API error or missing key.

    Returns a dict with keys:
        shipment_id, eta (ISO str), source, delayed (bool), delay_hours (int)
    """
    if mode != "sea":
        on_time_eta = (deadline_dt - timedelta(hours=4)).isoformat()
        return {
            "shipment_id": shipment_id,
            "eta": on_time_eta,
            "source": "non_vessel",
            "delayed": False,
            "delay_hours": 0,
        }

    api_key = settings.MARINETRAFFIC_KEY
    if not api_key or api_key == "your_marinetraffic_key_here":
        logger.debug(
            "[vessel_api] No MarineTraffic key configured — using synthetic ETA for %s.",
            shipment_id,
        )
        return _synthetic_eta(deadline_dt, shipment_id)

    try:
        resp = requests.get(
            _MARINETRAFFIC_BASE,
            params={
                "v": 1,
                "apikey": api_key,
                "portid": destination_port,
                "timespan": 24,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        # Parse first result that matches our shipment — simplified for free-tier schema
        arrivals = data.get("DATA", [])
        if arrivals:
            arrival = arrivals[0]
            eta_str = arrival.get("EXPECTED_ARRIVAL", deadline_dt.isoformat())
            eta_dt = datetime.fromisoformat(eta_str.replace("Z", "+00:00"))
            delayed = eta_dt > deadline_dt
            delay_hours = max(int((eta_dt - deadline_dt).total_seconds() / 3600), 0) if delayed else 0
            return {
                "shipment_id": shipment_id,
                "eta": eta_dt.isoformat(),
                "source": "marinetraffic",
                "delayed": delayed,
                "delay_hours": delay_hours,
            }
    except Exception as exc:
        logger.warning("[vessel_api] MarineTraffic API error (%s) — falling back to synthetic ETA.", exc)

    return _synthetic_eta(deadline_dt, shipment_id)

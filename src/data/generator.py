import random
import uuid
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone

PORTS = ["Jebel Ali", "Abu Dhabi", "NSICT Mumbai", "Chennai", "Delhi ICD"]

CARGO_TYPES = ["Electronics", "Textiles", "Machinery", "Pharmaceuticals", "FMCG", "Auto Parts"]

MODES = ["sea", "air", "road"]
MODE_WEIGHTS = [0.60, 0.25, 0.15]


def generate_shipments(num_records: int = 500) -> List[Dict[str, Any]]:
    """
    Generates synthetic shipment records with realistic distributions.
    - Weights: log-normal distribution
    - Deadlines: 3-21 days
    - Modes: 60% sea, 25% air, 15% road
    """
    shipments = []
    now = datetime.now(timezone.utc)

    for _ in range(num_records):
        origin = random.choice(PORTS)
        dest = random.choice(PORTS)
        while origin == dest:
            dest = random.choice(PORTS)

        # Log-normal weight distribution (e.g., mean ~400kg, but skewed with heavy tails)
        # lognormvariate(mu, sigma)
        weight_kg = round(random.lognormvariate(6.0, 1.5), 2)

        # Ready date is somewhat around current time
        ready_dt = now + timedelta(days=random.randint(-2, 5))
        # Deadline is 3 to 21 days after ready_dt
        deadline_dt = ready_dt + timedelta(days=random.randint(3, 21))

        mode = random.choices(MODES, weights=MODE_WEIGHTS, k=1)[0]

        # Estimated value is roughly proportional to weight and cargo type multiplier, but kept simple here
        value_multiplier = random.uniform(5.0, 50.0)
        estimated_value_usd = round(weight_kg * value_multiplier, 2)

        shipments.append(
            {
                "shipment_id": f"SHP-{uuid.uuid4().hex[:8].upper()}",
                "origin_port": origin,
                "destination_port": dest,
                "cargo_weight_kg": weight_kg,
                "cargo_type": random.choice(CARGO_TYPES),
                "ready_datetime": ready_dt.isoformat(),
                "deadline_datetime": deadline_dt.isoformat(),
                "preferred_mode": mode,
                "estimated_value_usd": estimated_value_usd,
            }
        )

    return shipments


if __name__ == "__main__":
    import json
    from pathlib import Path

    # Generate and save 5000 records
    records = generate_shipments(5000)
    out_file = Path("data/raw/manifests.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w") as f:
        json.dump(records, f, indent=2)

    print(f"Saved {len(records)} shipments to {out_file}")

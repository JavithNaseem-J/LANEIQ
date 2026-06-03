import json
import math
from datetime import datetime
from pathlib import Path

import yaml

PORT_COORDS = {
    "NSICT Mumbai": (18.944, 72.953),
    "Chennai": (13.0827, 80.2707),
    "Abu Dhabi": (24.4539, 54.3773),
    "Jebel Ali": (24.9857, 55.0622),
    "Delhi ICD": (28.6139, 77.2090),
}


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def main():
    repo_root = Path(__file__).resolve().parents[2]

    params_path = repo_root / "pipelines" / "params.yaml"
    with open(params_path, "r") as f:
        params = yaml.safe_load(f)

    cost_coeffs = params.get("solver", {}).get("cost_coefficients", {"sea": 1.2, "air": 4.5, "road": 2.0})

    input_path = repo_root / "data" / "raw" / "manifests.json"
    output_path = repo_root / "data" / "features" / "routing_inputs.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(input_path, "r") as f:
        manifests = json.load(f)

    ready_dts = [datetime.fromisoformat(m["ready_datetime"].replace("Z", "+00:00")) for m in manifests]
    epoch_now = min(ready_dts)

    routing_inputs = []

    for m in manifests:
        origin = m["origin_port"]
        dest = m["destination_port"]

        olat, olon = PORT_COORDS[origin]
        dlat, dlon = PORT_COORDS[dest]

        dist_km = haversine(olat, olon, dlat, dlon)

        ready_dt = datetime.fromisoformat(m["ready_datetime"].replace("Z", "+00:00"))
        deadline_dt = datetime.fromisoformat(m["deadline_datetime"].replace("Z", "+00:00"))

        ready_hours = int((ready_dt - epoch_now).total_seconds() / 3600)
        deadline_hours = int((deadline_dt - epoch_now).total_seconds() / 3600)

        weight = m["cargo_weight_kg"]

        routing_inputs.append(
            {
                "shipment_id": m["shipment_id"],
                "origin": origin,
                "destination": dest,
                "distance_km": round(dist_km, 2),
                "time_window": {"ready_hours": ready_hours, "deadline_hours": deadline_hours},
                "weight_kg": weight,
                "costs": {
                    "sea": round(weight * cost_coeffs.get("sea", 1.2), 2),
                    "air": round(weight * cost_coeffs.get("air", 4.5), 2),
                    "road": round(weight * cost_coeffs.get("road", 2.0), 2),
                },
            }
        )

    with open(output_path, "w") as f:
        json.dump(routing_inputs, f, indent=2)


if __name__ == "__main__":
    main()

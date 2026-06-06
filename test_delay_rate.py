import sys
sys.path.insert(0, "f:/DSML/LANEIQ")

from datetime import datetime, timezone
from src.data.vessel_api import _synthetic_eta

deadline = datetime(2026, 7, 15, tzinfo=timezone.utc)

delayed_count = 0
for i in range(20):
    sid = f"SHP-TEST-{i:04d}"
    r = _synthetic_eta(deadline, sid)
    status = "DELAYED" if r["delayed"] else "on time"
    dh = r["delay_hours"]
    eta = r["eta"][:16]
    print(f"{sid}: {status}  (+{dh}h)  ETA: {eta}")
    if r["delayed"]:
        delayed_count += 1

print(f"\nDelayed: {delayed_count}/20 ({delayed_count/20*100:.0f}%)")

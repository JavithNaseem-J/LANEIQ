"""
Day 27 — Performance benchmark.
Measures API latency (p50/p95/p99) for the /optimize → /status cycle.
Usage: python benchmarks/performance.py [--url http://localhost:8000] [--n 20]
"""
import argparse
import json
import statistics
import time

import httpx

BRIEF = "Ship 500 kg of electronics from Chennai to Jebel Ali by June 20, 2026. Prefer air freight."
POLL_INTERVAL = 2
POLL_TIMEOUT = 120


def run_single(client: httpx.Client, base_url: str) -> float:
    """Run one full optimize+poll cycle, return total elapsed seconds."""
    t0 = time.time()

    r = client.post(f"{base_url}/optimize", json={"shipment_brief": BRIEF}, timeout=15)
    r.raise_for_status()
    task_id = r.json()["task_id"]

    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        r = client.get(f"{base_url}/status/{task_id}", timeout=10)
        r.raise_for_status()
        state = r.json()["state"]
        if state in ("success", "failure"):
            break
        time.sleep(POLL_INTERVAL)

    return round(time.time() - t0, 2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--n", type=int, default=20)
    args = parser.parse_args()

    print(f"Benchmarking {args.n} requests against {args.url}...")
    latencies = []

    with httpx.Client() as client:
        for i in range(1, args.n + 1):
            try:
                elapsed = run_single(client, args.url)
                latencies.append(elapsed)
                print(f"  [{i:02d}/{args.n}] {elapsed:.1f}s")
            except Exception as exc:
                print(f"  [{i:02d}/{args.n}] ERROR: {exc}")

    if not latencies:
        print("No successful requests.")
        return

    latencies.sort()
    n = len(latencies)
    results = {
        "n_requests": n,
        "p50_s": round(statistics.median(latencies), 2),
        "p95_s": round(latencies[int(n * 0.95)], 2),
        "p99_s": round(latencies[min(int(n * 0.99), n - 1)], 2),
        "min_s": round(min(latencies), 2),
        "max_s": round(max(latencies), 2),
        "mean_s": round(statistics.mean(latencies), 2),
        "throughput_rpm": round(60 / statistics.mean(latencies), 1),
    }

    print(f"\n{'='*40}")
    print(f"  Requests  : {results['n_requests']}")
    print(f"  p50       : {results['p50_s']}s")
    print(f"  p95       : {results['p95_s']}s")
    print(f"  p99       : {results['p99_s']}s")
    print(f"  Throughput: {results['throughput_rpm']} req/min")

    out = "benchmarks/results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved → {out}")


if __name__ == "__main__":
    main()

"""Simple sequential + concurrent load test against the Seeds API."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common import write_json


def post_predict(base_url: str, payload: dict, timeout: float = 30.0) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/predict",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status_code": None,
            "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
            "error": str(exc),
        }
    latency_ms = (time.perf_counter() - started) * 1000.0
    return {
        "ok": status == 200,
        "status_code": status,
        "latency_ms": round(latency_ms, 3),
        "body_preview": body[:200],
    }


def summarize(latencies: list[float], ok_count: int, total: int, wall_s: float) -> dict:
    if not latencies:
        return {
            "n": 0,
            "ok": ok_count,
            "errors": total - ok_count,
            "throughput_rps": 0.0,
        }
    ordered = sorted(latencies)
    p95_index = min(len(ordered) - 1, max(0, int(round(0.95 * (len(ordered) - 1)))))
    return {
        "n": total,
        "ok": ok_count,
        "errors": total - ok_count,
        "latency_ms": {
            "min": round(min(ordered), 3),
            "mean": round(statistics.fmean(ordered), 3),
            "median": round(statistics.median(ordered), 3),
            "p95": round(ordered[p95_index], 3),
            "max": round(max(ordered), 3),
        },
        "wall_seconds": round(wall_s, 3),
        "throughput_rps": round(ok_count / wall_s, 3) if wall_s > 0 else 0.0,
    }


def run_sequential(base_url: str, payload: dict, n: int) -> dict:
    latencies: list[float] = []
    ok_count = 0
    started = time.perf_counter()
    for _ in range(n):
        result = post_predict(base_url, payload)
        latencies.append(float(result["latency_ms"]))
        if result["ok"]:
            ok_count += 1
    return summarize(latencies, ok_count, n, time.perf_counter() - started)


def run_parallel(base_url: str, payload: dict, n: int, workers: int) -> dict:
    latencies: list[float] = []
    ok_count = 0
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(post_predict, base_url, payload) for _ in range(n)]
        for future in as_completed(futures):
            result = future.result()
            latencies.append(float(result["latency_ms"]))
            if result["ok"]:
                ok_count += 1
    return summarize(latencies, ok_count, n, time.perf_counter() - started)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Нагрузочный тест /predict.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--samples", default=str(ROOT / "sample_request.json"))
    parser.add_argument("--sequential", type=int, default=30)
    parser.add_argument("--parallel", type=int, default=40)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", default=str(ROOT / "results" / "load_test_report.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(Path(args.samples).read_text(encoding="utf-8"))
    if "instances" not in payload:
        raise SystemExit("sample_request.json должен содержать instances")

    # Warm-up
    warm = post_predict(args.base_url, payload)
    if not warm["ok"]:
        print(f"LOAD_TEST_FAIL warm-up: {warm}")
        return 1

    sequential = run_sequential(args.base_url, payload, args.sequential)
    parallel = run_parallel(args.base_url, payload, args.parallel, args.workers)
    report = {
        "base_url": args.base_url.rstrip("/"),
        "payload_instances": len(payload["instances"]),
        "warm_up_latency_ms": warm["latency_ms"],
        "sequential": sequential,
        "parallel": {**parallel, "workers": args.workers},
        "stable": sequential["errors"] == 0 and parallel["errors"] == 0,
    }
    write_json(Path(args.output), report)
    print("LOAD_TEST_JSON " + json.dumps(report, ensure_ascii=False))
    if not report["stable"]:
        print("LOAD_TEST_UNSTABLE")
        return 1
    print("LOAD_TEST_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

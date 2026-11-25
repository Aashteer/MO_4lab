"""Smoke-test /health, /metadata, /predict and a set of 422 requests."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common import CLASS_MAP, CLASS_NAMES, FEATURE_COLUMNS, write_json

VALID = {
    "area": 15.26,
    "perimeter": 14.84,
    "compactness": 0.871,
    "length_of_kernel": 5.763,
    "width_of_kernel": 3.312,
    "asymmetry_coefficient": 2.221,
    "length_of_kernel_groove": 5.22,
}


def request(method: str, url: str, payload=None, raw: bytes | None = None) -> tuple[int, str]:
    data = raw
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif raw is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def expected_ids(document) -> list[int]:
    if isinstance(document, list):
        if document and isinstance(document[0], dict):
            return [int(item["class_id"]) for item in document]
        return [int(item) for item in document]
    if isinstance(document, dict) and "predictions" in document:
        values = document["predictions"]
        if values and isinstance(values[0], dict):
            return [int(item["class_id"]) for item in values]
        return [int(item) for item in values]
    raise ValueError("expected_predictions.json must be a list of ints or an object with predictions")


def bad_cases() -> list[dict]:
    missing = dict(VALID)
    missing.pop("length_of_kernel_groove")
    extra = dict(VALID)
    extra["extra"] = 1
    as_text = dict(VALID)
    as_text["area"] = "15.26"
    as_null = dict(VALID)
    as_null["area"] = None
    as_bool = dict(VALID)
    as_bool["area"] = True
    non_finite = dict(VALID)
    non_finite["area"] = 1e309
    too_many = {"instances": [dict(VALID) for _ in range(101)]}
    return [
        {"name": "empty_object", "body": {}, "expect": 422},
        {"name": "empty_instances", "body": {"instances": []}, "expect": 422},
        {"name": "missing_field", "body": {"instances": [missing]}, "expect": 422},
        {"name": "extra_field", "body": {"instances": [extra]}, "expect": 422},
        {"name": "string_value", "body": {"instances": [as_text]}, "expect": 422},
        {"name": "null_value", "body": {"instances": [as_null]}, "expect": 422},
        {"name": "bool_value", "body": {"instances": [as_bool]}, "expect": 422},
        {"name": "non_finite", "body": {"instances": [non_finite]}, "expect": 422},
        {"name": "bare_array", "body": [1, 2, 3, 4, 5, 6, 7], "expect": 422},
        {"name": "too_many_instances", "body": too_many, "expect": 422},
        {"name": "invalid_json", "raw": b"{", "expect": 422},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Сравнить ответы API с expected_predictions.json.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--samples", default=str(ROOT / "sample_request.json"))
    parser.add_argument("--expected", default=str(ROOT / "expected_predictions.json"))
    parser.add_argument("--output", default=str(ROOT / "results" / "api_smoke_report.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base = args.base_url.rstrip("/")
    failures: list[str] = []
    report: dict = {"base_url": base}

    code, body = request("GET", f"{base}/health")
    health = _json_or_none(body)
    report["health"] = {"status_code": code, "body": health or body}
    if code != 200 or not isinstance(health, dict) or health.get("status") != "ok":
        failures.append(f"/health returned {code}: {body[:300]}")
    elif not str(health.get("model_version", "")).strip():
        failures.append("/health has no model_version")

    code, body = request("GET", f"{base}/metadata")
    meta = _json_or_none(body)
    report["metadata"] = {"status_code": code, "body": meta or body}
    classes = None if not isinstance(meta, dict) else (meta.get("class_names") or meta.get("classes"))
    if code != 200 or not isinstance(meta, dict):
        failures.append(f"/metadata returned {code}: {body[:300]}")
    elif meta.get("features") != FEATURE_COLUMNS or classes != CLASS_NAMES:
        failures.append(f"/metadata features or classes mismatch: {body[:500]}")
    elif not meta.get("model_name") or not meta.get("run_id") or not str(meta.get("version", "")).strip():
        failures.append("/metadata is missing model_name, version, or run_id")
    elif health and isinstance(health, dict) and str(meta.get("version")) != str(health.get("model_version")):
        failures.append("health.model_version and metadata.version differ")

    samples_doc = json.loads(Path(args.samples).read_text(encoding="utf-8"))
    if "instances" not in samples_doc:
        failures.append("sample_request.json has no instances")
        samples_doc = {"instances": []}
    expected = expected_ids(json.loads(Path(args.expected).read_text(encoding="utf-8")))
    code, body = request("POST", f"{base}/predict", payload=samples_doc)
    parsed = _json_or_none(body)
    report["predict"] = {"status_code": code, "body": parsed or body, "expected": expected}
    if code != 200 or not isinstance(parsed, dict):
        failures.append(f"/predict status {code}: {body[:400]}")
    else:
        got = [int(value) for value in parsed.get("predictions", [])]
        names = parsed.get("class_names", [])
        if got != expected:
            failures.append(f"predictions {got} != expected {expected}")
        if len(names) != len(got) or any(names[i] != CLASS_MAP[got[i]] for i in range(len(got))):
            failures.append(f"class_names {names} do not match predictions {got}")
        if "latency_ms" not in parsed or float(parsed["latency_ms"]) < 0:
            failures.append("latency_ms missing or negative")
        if not str(parsed.get("model_version", "")).strip():
            failures.append("predict response has no model_version")
        elif isinstance(meta, dict) and str(parsed.get("model_version")) != str(meta.get("version")):
            failures.append("predict.model_version and metadata.version differ")

    bad_results = []
    for case in bad_cases():
        if "raw" in case:
            code, body = request("POST", f"{base}/predict", raw=case["raw"])
        else:
            code, body = request("POST", f"{base}/predict", payload=case["body"])
        bad_results.append(
            {"name": case["name"], "status_code": code, "expect": case["expect"], "body": body[:500]}
        )
        if code != case["expect"]:
            failures.append(f"bad case {case['name']}: expected {case['expect']}, got {code}")
    code, body = request("GET", f"{base}/predict")
    bad_results.append({"name": "get_predict", "status_code": code, "expect": 405, "body": body[:300]})
    if code != 405:
        failures.append(f"GET /predict expected 405, got {code}")
    report["bad_requests"] = bad_results
    report["ok"] = not failures
    report["failures"] = failures
    write_json(Path(args.output), report)
    if failures:
        print("SMOKE_FAIL")
        for line in failures:
            print(line)
        return 1
    print("SMOKE_OK")
    print(f"predictions={expected} bad_cases={len(bad_results)}")
    return 0


def _json_or_none(body: str):
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())

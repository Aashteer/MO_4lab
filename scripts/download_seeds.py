"""Download the official UCI Seeds file and record its SHA-256.

The raw file is written exactly as received and is never rewritten afterwards.
"""

from __future__ import annotations

import hashlib
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "raw" / "seeds_dataset.txt"
SIDECAR = ROOT / "data" / "raw" / "SHA256SUMS.txt"
USER_AGENT = "MLOpsLab-Variant21/1.0"

TEXT_URLS = [
    "https://archive.ics.uci.edu/ml/machine-learning-databases/00236/seeds_dataset.txt",
    "https://archive.ics.uci.edu/static/public/236/data/seeds_dataset.txt",
]
ZIP_URLS = [
    "https://archive.ics.uci.edu/static/public/236/seeds.zip",
]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def looks_like_seeds(payload: bytes) -> bool:
    if not payload or payload.lstrip().startswith(b"<"):
        return False
    rows = [line.strip() for line in payload.decode("utf-8", errors="replace").splitlines() if line.strip()]
    if len(rows) != 210:
        return False
    labels = []
    for line in rows:
        parts = line.split()
        if len(parts) != 8:
            return False
        try:
            [float(value) for value in parts[:7]]
            label = int(float(parts[7]))
        except ValueError:
            return False
        if label not in (1, 2, 3):
            return False
        labels.append(label)
    return all(labels.count(label) == 70 for label in (1, 2, 3))


def from_zip(payload: bytes) -> bytes | None:
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile:
        return None
    names = [name for name in archive.namelist() if name.endswith("seeds_dataset.txt")]
    if not names:
        return None
    return archive.read(names[0])


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    data: bytes | None = None
    source = ""
    for url in TEXT_URLS:
        try:
            payload = fetch(url)
        except Exception as exc:  # noqa: BLE001 - report every mirror
            errors.append(f"{url}: {exc}")
            continue
        if looks_like_seeds(payload):
            data = payload
            source = url
            break
        errors.append(f"{url}: payload is not the 210x8 seeds table")
    if data is None:
        for url in ZIP_URLS:
            try:
                payload = from_zip(fetch(url))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{url}: {exc}")
                continue
            if payload is not None and looks_like_seeds(payload):
                data = payload
                source = url
                break
            errors.append(f"{url}: zip has no valid seeds_dataset.txt")
    if data is None:
        print("Failed to download UCI Seeds.", file=sys.stderr)
        for line in errors:
            print(line, file=sys.stderr)
        return 1
    DEST.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    SIDECAR.write_text(f"{digest}  seeds_dataset.txt\n", encoding="ascii")
    print(f"source={source}")
    print(f"path={DEST}")
    print(f"bytes={len(data)}")
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

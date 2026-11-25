"""Compute and verify SHA-256 of the exported model artifact for integrity control."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common import sha256_file, write_json


def resolve_model_file(model_dir: Path) -> Path:
    pickle_path = model_dir / "model.pkl"
    if pickle_path.is_file():
        return pickle_path
    raise FileNotFoundError(f"Не найден model.pkl в {model_dir}")


def build_hash_record(model_dir: Path) -> dict:
    model_dir = Path(model_dir)
    model_file = resolve_model_file(model_dir)
    digest = sha256_file(model_file)
    record = {
        "algorithm": "sha256",
        "file": str(model_file.name),
        "path": str(model_file.as_posix()),
        "sha256": digest,
        "size_bytes": model_file.stat().st_size,
        "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    meta_path = model_dir / "lab_metadata.json"
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for key in ("model_name", "version", "alias", "run_id", "algorithm"):
            if key in meta:
                record[key] = meta[key]
    return record


def write_hash_files(model_dir: Path, results_dir: Path | None = None) -> dict:
    model_dir = Path(model_dir)
    record = build_hash_record(model_dir)
    text_path = model_dir / "model_sha256.txt"
    text_path.write_text(f"{record['sha256']}  {record['file']}\n", encoding="ascii")
    write_json(model_dir / "model_hash.json", record)
    if results_dir is not None:
        write_json(Path(results_dir) / "model_hash.json", record)
    return record


def verify_hash(model_dir: Path, expected: str | None = None) -> dict:
    model_dir = Path(model_dir)
    record = build_hash_record(model_dir)
    actual = record["sha256"]
    if expected is None:
        stored = model_dir / "model_sha256.txt"
        if not stored.is_file():
            raise FileNotFoundError(f"Нет сохранённого хеша: {stored}")
        expected = stored.read_text(encoding="ascii").split()[0].strip()
    if actual != expected:
        raise RuntimeError(
            f"Целостность модели нарушена: ожидался {expected}, получено {actual}"
        )
    record["verified"] = True
    record["expected_sha256"] = expected
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Хеш сериализованной модели (SHA-256).")
    parser.add_argument("--model-dir", default=str(ROOT / "exported_model"))
    parser.add_argument("--results-dir", default=str(ROOT / "results"))
    parser.add_argument("--verify", action="store_true", help="Сверить с model_sha256.txt")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model_dir = Path(args.model_dir)
    if args.verify:
        record = verify_hash(model_dir)
        print("MODEL_HASH_OK " + json.dumps(record, ensure_ascii=False))
        return 0
    record = write_hash_files(model_dir, Path(args.results_dir))
    print("MODEL_HASH_JSON " + json.dumps(record, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

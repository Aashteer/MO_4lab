"""FastAPI service: a batch of kernel measurements, seven named floats each."""

from __future__ import annotations

import json
import math
import os
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")

import cloudpickle
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware

from src.common import CLASS_MAP, CLASS_NAMES, FEATURE_COLUMNS, ROOT

MODEL = None
METADATA: dict[str, Any] = {}
MODEL_HASH: str | None = None
_LOG_LOCK = threading.Lock()

_ROW_EXAMPLE = {
    "area": 15.26,
    "perimeter": 14.84,
    "compactness": 0.871,
    "length_of_kernel": 5.763,
    "width_of_kernel": 3.312,
    "asymmetry_coefficient": 2.221,
    "length_of_kernel_groove": 5.22,
}


class SeedFeatures(BaseModel):
    """One grain. Extra keys and missing keys are rejected."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": _ROW_EXAMPLE})
    area: float
    perimeter: float
    compactness: float
    length_of_kernel: float
    width_of_kernel: float
    asymmetry_coefficient: float
    length_of_kernel_groove: float

    @field_validator("*", mode="before")
    @classmethod
    def reject_non_numbers(cls, value: Any):
        if isinstance(value, bool) or isinstance(value, str):
            raise ValueError("expected a JSON number")
        return value

    @field_validator("*")
    @classmethod
    def must_be_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("value must be finite")
        return float(value)


class PredictRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"instances": [_ROW_EXAMPLE]}},
    )
    instances: list[SeedFeatures] = Field(min_length=1, max_length=100)


class PredictResponse(BaseModel):
    predictions: list[int]
    class_names: list[str]
    model_version: str
    latency_ms: float


class HealthResponse(BaseModel):
    status: str
    model_version: str
    model_sha256: str | None = None


class MetadataResponse(BaseModel):
    model_name: str
    version: str | None = None
    model_version: str | None = None
    alias: str | None = None
    run_id: str | None = None
    algorithm: str | None = None
    params: dict[str, Any] | None = None
    features: list[str]
    classes: list[str]
    class_names: list[str]
    class_map: dict[str, str]
    n_features: int = Field(7)
    model_sha256: str | None = None


def model_path() -> Path:
    return Path(os.environ.get("MODEL_PATH", ROOT / "exported_model"))


def request_log_path() -> Path:
    configured = os.environ.get("REQUEST_LOG_PATH")
    if configured:
        return Path(configured)
    return ROOT / "logs" / "api_requests.jsonl"


def model_hash_path() -> Path:
    configured = os.environ.get("MODEL_HASH_PATH")
    if configured:
        return Path(configured)
    return model_path() / "model_sha256.txt"


def model_version() -> str:
    value = METADATA.get("version")
    if value is None or str(value).strip() == "":
        return "unknown"
    return str(value)


def append_request_log(event: dict[str, Any]) -> None:
    """Append one audit event. Features are measurements, not personal data."""
    path = request_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False)
    with _LOG_LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def load_model_from_export(path: Path):
    """Load the exported Pipeline.

    Prefer mlflow.sklearn when MLflow is installed (host/dev). In the Docker image
    we load the same cloudpickle artifact ``model.pkl`` that MLflow wrote, so the
    container stays small and does not pull the full tracking stack.
    """
    try:
        import mlflow.sklearn  # type: ignore

        return mlflow.sklearn.load_model(str(path))
    except Exception:
        pickle_path = path / "model.pkl"
        if not pickle_path.is_file():
            raise RuntimeError(f"Не найден model.pkl в {path}")
        with pickle_path.open("rb") as handle:
            return cloudpickle.load(handle)


def load_artifacts() -> None:
    global MODEL, METADATA, MODEL_HASH
    path = model_path()
    MODEL = load_model_from_export(path)
    n_features = getattr(MODEL, "n_features_in_", None)
    if n_features is not None and int(n_features) != 7:
        raise RuntimeError(f"Модель ожидает {n_features} признаков, нужно 7.")
    meta_path = path / "lab_metadata.json"
    if meta_path.is_file():
        METADATA = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        METADATA = {}
    hash_file = model_hash_path()
    if hash_file.is_file():
        MODEL_HASH = hash_file.read_text(encoding="ascii").split()[0].strip()
    else:
        hash_json = path / "model_hash.json"
        if hash_json.is_file():
            MODEL_HASH = str(json.loads(hash_json.read_text(encoding="utf-8")).get("sha256") or "")
        else:
            MODEL_HASH = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_artifacts()
    request_log_path().parent.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Seeds classifier API",
    description="Классификация сортов пшеницы (Kama, Rosa, Canadian). Вариант 21.",
    version="1.0.0",
    lifespan=lifespan,
)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        started = time.perf_counter()
        body_bytes = await request.body()

        async def receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        request = Request(request.scope, receive)
        response = await call_next(request)
        latency_ms = round((time.perf_counter() - started) * 1000.0, 3)

        path = request.url.path
        if path in {"/predict", "/health", "/metadata"}:
            event: dict[str, Any] = {
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "model_version": model_version(),
                "model_sha256": MODEL_HASH,
            }
            # Successful /predict is logged with outputs in the endpoint itself.
            # Middleware still records health/metadata and failed/invalid predicts.
            if path == "/predict" and request.method == "POST":
                if response.status_code == 200:
                    response.headers["X-Request-Id"] = request_id
                    return response
                try:
                    payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
                except json.JSONDecodeError:
                    payload = None
                if isinstance(payload, dict) and isinstance(payload.get("instances"), list):
                    event["n_instances"] = len(payload["instances"])
                    event["instances"] = payload["instances"]
                else:
                    event["n_instances"] = None
                    event["body_invalid"] = True
            append_request_log(event)
            response.headers["X-Request-Id"] = request_id
        return response


app.add_middleware(AuditMiddleware)


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Keep non-finite inputs as HTTP 422. The default encoder cannot dump Infinity."""
    details = []
    for error in exc.errors():
        item = {key: _json_safe(val) for key, val in error.items() if key != "ctx"}
        if "ctx" in error:
            item["ctx"] = {"error": str(error["ctx"].get("error", ""))}
        details.append(item)
    return JSONResponse(status_code=422, content={"detail": details})


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", model_version=model_version(), model_sha256=MODEL_HASH)


@app.get("/metadata", response_model=MetadataResponse)
def metadata() -> MetadataResponse:
    version = model_version()
    class_map = {str(label): name for label, name in CLASS_MAP.items()}
    return MetadataResponse(
        model_name=str(METADATA.get("model_name", "seeds-classifier")),
        version=version,
        model_version=version,
        alias=METADATA.get("alias"),
        run_id=METADATA.get("run_id"),
        algorithm=METADATA.get("algorithm"),
        params=METADATA.get("params"),
        features=list(FEATURE_COLUMNS),
        classes=list(CLASS_NAMES),
        class_names=list(CLASS_NAMES),
        class_map=class_map,
        n_features=7,
        model_sha256=MODEL_HASH,
    )


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    if MODEL is None:
        raise RuntimeError("Модель не загружена.")
    rows = []
    instances = []
    for instance in payload.instances:
        data = instance.model_dump()
        instances.append(data)
        rows.append([data[column] for column in FEATURE_COLUMNS])
    frame = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    started = time.perf_counter()
    raw = MODEL.predict(frame)
    latency_ms = (time.perf_counter() - started) * 1000.0
    predictions = [int(value) for value in raw]
    names = [CLASS_MAP[value] for value in predictions]
    response = PredictResponse(
        predictions=predictions,
        class_names=names,
        model_version=model_version(),
        latency_ms=round(latency_ms, 3),
    )
    # Dedicated audit record with inputs + outputs (geometry only, no PII).
    append_request_log(
        {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "request_id": str(uuid.uuid4()),
            "method": "POST",
            "path": "/predict",
            "status_code": 200,
            "event": "predict_result",
            "n_instances": len(instances),
            "instances": instances,
            "predictions": predictions,
            "class_names": names,
            "model_version": model_version(),
            "model_sha256": MODEL_HASH,
            "model_latency_ms": response.latency_ms,
        }
    )
    return response

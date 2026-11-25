# Inference image for the UCI Seeds classifier (lab variant 21).
# Host training uses Python 3.10 + full requirements.txt.
# The image targets python:3.12-slim and installs requirements-serve.txt.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    MODEL_PATH=/app/exported_model \
    REQUEST_LOG_PATH=/app/logs/api_requests.jsonl \
    MODEL_HASH_PATH=/app/exported_model/model_sha256.txt \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
COPY requirements-serve.txt /app/requirements.txt
RUN pip install --no-cache-dir \
    -i ${PIP_INDEX_URL} \
    --trusted-host ${PIP_TRUSTED_HOST} \
    -r /app/requirements.txt

COPY src /app/src
COPY exported_model /app/exported_model
COPY sample_request.json /app/sample_request.json
COPY expected_predictions.json /app/expected_predictions.json

# Fail the image build if the serialized model is missing or hash verification fails.
ARG RUN_MODEL_INTEGRITY_CHECK=1
RUN if [ "$RUN_MODEL_INTEGRITY_CHECK" = "1" ]; then \
      python -m src.model_hash --model-dir /app/exported_model --results-dir /tmp && \
      python -m src.model_hash --model-dir /app/exported_model --verify && \
      python -c "from pathlib import Path; from src.app import load_model_from_export; \
m=load_model_from_export(Path('/app/exported_model')); \
assert int(getattr(m,'n_features_in_',7))==7"; \
    fi

RUN mkdir -p /app/logs /app/results && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]

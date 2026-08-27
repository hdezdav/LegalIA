FROM python:3.12-slim

# Build context is the REPOSITORY ROOT, not backend/. The API image also carries
# `ingestion` and `evaluation` because both are executed inside this container
# (scripts/ingest.sh, evaluation/run_evaluation.py) and both import app.*.

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# gcc is build-time only; libpq5 and curl stay for psycopg and HEALTHCHECK.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
COPY backend/requirements-dev.txt ./requirements-dev.txt
# Dev/test deps are installed because the documented workflow runs the suite
# inside this container (`docker compose exec legalia-api pytest`).
RUN pip install -r requirements-dev.txt \
    && apt-get purge -y --auto-remove gcc

COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini
COPY backend/tests ./tests
COPY backend/pyproject.toml ./pyproject.toml
COPY ingestion ./ingestion
COPY evaluation ./evaluation

RUN useradd -m -u 1000 legalia && chown -R legalia:legalia /app
USER legalia

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

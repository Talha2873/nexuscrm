# ==========================================================
# NexusCRM Backend - Django 5 / DRF / Celery / Channels
# ==========================================================
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System dependencies (psycopg build deps, postgres client for backups, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        postgresql-client \
        gettext \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app/

RUN mkdir -p /app/media /app/staticfiles /app/backups /app/logs \
    && chmod +x /app/scripts/*.sh

EXPOSE 8000

CMD ["/app/scripts/start-backend.sh"]

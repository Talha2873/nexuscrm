#!/usr/bin/env bash
# ==========================================================
# NexusCRM backend entrypoint
# Waits for dependencies, migrates, collects static, then serves.
# ==========================================================
set -euo pipefail

DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.development}"
export DJANGO_SETTINGS_MODULE

echo "==> Waiting for PostgreSQL at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432} ..."
until pg_isready -h "${POSTGRES_HOST:-db}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-nexuscrm}" >/dev/null 2>&1; do
  sleep 1
done
echo "==> PostgreSQL is ready."

echo "==> Applying database migrations ..."
python manage.py migrate --noinput

echo "==> Collecting static files ..."
python manage.py collectstatic --noinput --clear

if [ "${SEED_ON_START:-False}" = "True" ]; then
  echo "==> Seeding demo data ..."
  python manage.py seed_data --force
fi

if [ "${DEBUG:-True}" = "True" ]; then
  echo "==> Starting Daphne (ASGI, development) on :8000"
  exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
else
  echo "==> Starting Gunicorn (uvicorn workers, production) on :8000"
  exec gunicorn config.asgi:application \
      --bind 0.0.0.0:8000 \
      --workers "${GUNICORN_WORKERS:-4}" \
      --worker-class uvicorn.workers.UvicornWorker \
      --timeout 120 \
      --graceful-timeout 30 \
      --max-requests 1000 \
      --max-requests-jitter 100 \
      --access-logfile - \
      --error-logfile -
fi

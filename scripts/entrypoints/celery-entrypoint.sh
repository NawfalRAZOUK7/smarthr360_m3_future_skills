#!/bin/sh
# Entrypoint for Celery worker
# - Runs migrations if AUTO_MIGRATE=true
# - Starts Celery worker

set -e

if [ "$AUTO_MIGRATE" = "true" ]; then
  echo "Running database migrations (Celery)..."
  python manage.py migrate --noinput
fi

echo "Starting Celery worker..."
exec celery -A config worker --loglevel=info

#!/bin/sh
# Entrypoint for Django web service (Gunicorn)
# - Runs migrations if AUTO_MIGRATE=true
# - Starts Gunicorn server

set -e


# Collect static files at runtime
echo "Collecting static files..."
python manage.py collectstatic --noinput

if [ "$AUTO_MIGRATE" = "true" ]; then
  echo "Running database migrations..."
  python manage.py migrate --noinput
fi

echo "Starting Gunicorn..."
# Bind to both IPv4 and IPv6 by default; allow override via BIND address env.
GUNICORN_BINDS="${BIND:-0.0.0.0:8000}"
if [ -z "$BIND" ]; then
  GUNICORN_BINDS="0.0.0.0:8000 [::]:8000"
fi
exec gunicorn config.wsgi:application --bind $GUNICORN_BINDS

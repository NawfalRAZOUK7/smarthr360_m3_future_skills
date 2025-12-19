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
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000

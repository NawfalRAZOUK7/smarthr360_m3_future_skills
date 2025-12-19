#!/bin/sh
set -e

# Wait for database to be ready (optional, uncomment if needed)
# until nc -z $DB_HOST $DB_PORT; do
#   echo "Waiting for database..."
#   sleep 1
# done

exec "$@"

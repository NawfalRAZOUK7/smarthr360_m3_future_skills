#!/bin/sh
# Entrypoint for Nginx service
# - Starts Nginx in foreground

set -e

echo "Starting Nginx..."
exec nginx -g 'daemon off;'

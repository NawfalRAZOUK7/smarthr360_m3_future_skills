# Entrypoint Scripts for Docker Services

This directory contains service-specific entrypoint scripts used by Docker containers. Each script ensures proper startup, migrations, and service launch for its respective component.

## Scripts

- **web-entrypoint.sh**: Entrypoint for the Django web service. Runs database migrations (if `AUTO_MIGRATE=true`) and starts Gunicorn.
- **celery-entrypoint.sh**: Entrypoint for the Celery worker. Runs migrations (if `AUTO_MIGRATE=true`) and starts the Celery worker process.
- **ml-entrypoint.sh**: Entrypoint for the ML service. Starts the ML model server (adjust as needed for your serving method).
- **nginx-entrypoint.sh**: Entrypoint for the Nginx service. Starts Nginx in the foreground.

## Usage

Each Dockerfile should copy only the relevant entrypoint script from this directory and set it as the container's ENTRYPOINT. This ensures each service has a minimal, clear startup process and supports migrations or other pre-launch tasks as needed.

Scripts are POSIX-compliant shell scripts and should be executable (`chmod +x`).

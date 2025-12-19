# syntax=docker/dockerfile:1.4
# ==============================================================================
# Multi-stage Dockerfile for SmartHR360 Future Skills Platform
# ==============================================================================
# Stage 1: Builder - Install dependencies and compile Python packages
# Stage 2: Runtime - Minimal production image
# ==============================================================================

# ==============================================================================
# Stage 1: Builder
# ==============================================================================
FROM python:3.11-slim AS builder

# Set build arguments
ARG BUILD_ENV=production
ARG PYTHON_VERSION=3.11

# Environment variables for build stage
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /build


# Install build dependencies with BuildKit cache for apt, with retry loop for lock errors
RUN --mount=type=cache,target=/var/cache/apt \
        set -eux; \
        n=0; \
        until [ "$n" -ge 5 ]; do \
            rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock; \
            apt-get update && apt-get install -y --no-install-recommends \
                build-essential \
                curl \
                g++ \
                gcc \
                git \
                libpq-dev \
                && rm -rf /var/lib/apt/lists/* && break; \
            n=$((n+1)); \
            echo "apt-get failed, retrying in 5s... ($n/5)"; \
            sleep 5; \
        done

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements files
COPY requirements.txt requirements_ml.txt requirements_logging.txt requirements_security.txt requirements_celery.txt ./
COPY ml/requirements.txt ./ml/requirements.txt

# Install Python dependencies in virtual environment with BuildKit pip cache, with retry loop for network errors
RUN --mount=type=cache,target=/root/.cache/pip \
        set -eux; \
        n=0; \
        until [ "$n" -ge 5 ]; do \
            pip install --upgrade pip setuptools wheel && \
            pip install --no-cache-dir -r requirements.txt && \
            pip install --no-cache-dir -r requirements_ml.txt && \
            pip install --no-cache-dir -r requirements_logging.txt && \
            pip install --no-cache-dir -r requirements_security.txt && break; \
            n=$((n+1)); \
            echo "pip install failed, retrying in 10s... ($n/5)"; \
            sleep 10; \
        done


COPY manage.py pyproject.toml pytest.ini requirements*.txt ./
COPY config/ ./config/
COPY future_skills/ ./future_skills/
COPY celery_monitoring/ ./celery_monitoring/
COPY tests/ ./tests/
# Copy ML scripts and onboarding scripts
COPY ml/ ./ml/
COPY scripts/ ./scripts/
WORKDIR /build/app

# Create necessary directories
RUN mkdir -p \
    logs \
    staticfiles \
    media \
    artifacts/models \
    artifacts/datasets \
    artifacts/results \
    artifacts/cache/joblib

# Collect static files
RUN python manage.py collectstatic --noinput --clear || true

# ==============================================================================
# Stage 2: Runtime
# ==============================================================================
FROM python:3.11-slim AS runtime

# Set runtime arguments
ARG APP_USER=smarthr360
ARG APP_UID=1000
ARG APP_GID=1000

# Labels for image metadata
LABEL maintainer="SmartHR360 Team" \
      version="1.0.0" \
      description="SmartHR360 Future Skills Platform" \
      org.opencontainers.image.source="https://github.com/yourusername/smarthr360_m3_future_skills"

# Environment variables for runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PORT=8000

# Install runtime dependencies only and create app user (with BuildKit apt cache, with retry loop)
RUN --mount=type=cache,target=/var/cache/apt \
        set -eux; \
        n=0; \
        until [ "$n" -ge 5 ]; do \
            rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock; \
            apt-get update && apt-get install -y --no-install-recommends \
                curl \
                libpq5 \
                netcat-traditional \
                postgresql-client \
                && rm -rf /var/lib/apt/lists/* && apt-get clean && break; \
            n=$((n+1)); \
            echo "apt-get failed, retrying in 5s... ($n/5)"; \
            sleep 5; \
        done; \
        groupadd -g "${APP_GID}" "${APP_USER}"; \
        useradd -u "${APP_UID}" -g "${APP_GID}" -m -s /bin/bash "${APP_USER}"

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv


# Copy only necessary application files and folders to runtime image
COPY --from=builder --chown=${APP_USER}:${APP_USER} /build/app /app

# Copy collected static files from builder
COPY --from=builder --chown=${APP_USER}:${APP_USER} /build/app/staticfiles /app/staticfiles

# Create necessary directories and entrypoint script
RUN set -eux; \
    mkdir -p \
        logs \
        staticfiles \
        media \
        artifacts/models \
        artifacts/datasets \
        artifacts/results \
        artifacts/cache/joblib; \
    chown -R "${APP_USER}:${APP_USER}" /app; \
    printf '%s\n' \
        '#!/bin/bash' \
        'set -e' \
        '' \
        'echo "Starting SmartHR360 Future Skills Platform..."' \
        '' \
        '# Wait for database' \
        'if [ -n "$DB_HOST" ]; then' \
        '    echo "Waiting for database at $DB_HOST:${DB_PORT:-5432}..."' \
        '    for i in {1..30}; do' \
        '        nc -z "$DB_HOST" "${DB_PORT:-5432}" && break' \
        '        echo "Waiting for database... ($i/30)"' \
        '        sleep 2' \
        '    done' \
        'fi' \
        '' \
        '# Run migrations if AUTO_MIGRATE is set' \
        'if [ "$AUTO_MIGRATE" = "true" ]; then' \
        '    echo "Running database migrations..."' \
        '    python manage.py migrate --noinput' \
        'fi' \
        '' \
        '# Create superuser if credentials provided' \
        'if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then' \
        '    echo "Creating superuser if not exists..."' \
        "    python manage.py shell -c \"" \
        "from django.contrib.auth import get_user_model;" \
        "User = get_user_model();" \
        "if not User.objects.filter(username=\\\"${DJANGO_SUPERUSER_USERNAME:-}\\\").exists():" \
        "    User.objects.create_superuser(\\\"${DJANGO_SUPERUSER_USERNAME:-}\\\", \\\"${DJANGO_SUPERUSER_EMAIL:-}\\\", \\\"${DJANGO_SUPERUSER_PASSWORD:-}\\\")" \
        "    print(\\\"Superuser created\\\")" \
        "else:" \
        "    print(\\\"Superuser already exists\\\")" \
        "\" || true" \
        'fi' \
        '' \
        'echo "SmartHR360 is ready!"' \
        'exec "$@"' \
        > /app/entrypoint.sh; \
    chmod +x /app/entrypoint.sh

# Switch to non-root user
USER ${APP_USER}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health/ || exit 1

# Expose port
EXPOSE ${PORT}

# Set entrypoint (default: Django app, but allow override for ML pipeline)
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command (can be overridden in docker-compose for ML pipeline)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--worker-class", "gthread", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]

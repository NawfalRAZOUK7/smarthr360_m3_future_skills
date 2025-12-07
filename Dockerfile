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

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    g++ \
    gcc \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements files
COPY requirements.txt requirements_ml.txt requirements_logging.txt requirements_security.txt ./

# Install Python dependencies in virtual environment
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements_ml.txt && \
    pip install --no-cache-dir -r requirements_logging.txt && \
    pip install --no-cache-dir -r requirements_security.txt

# Copy application code for collectstatic
COPY . /build/app
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

# Install runtime dependencies only and create app user
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        curl \
        libpq5 \
        netcat-traditional \
        postgresql-client; \
    rm -rf /var/lib/apt/lists/*; \
    apt-get clean; \
    groupadd -g "${APP_GID}" "${APP_USER}"; \
    useradd -u "${APP_UID}" -g "${APP_GID}" -m -s /bin/bash "${APP_USER}"

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=${APP_USER}:${APP_USER} . /app

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
        'if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then' \
        '    echo "Creating superuser if not exists..."' \
        "    python manage.py shell -c \"" \
        "from django.contrib.auth import get_user_model;" \
        "User = get_user_model();" \
        "if not User.objects.filter(username=\\\"$DJANGO_SUPERUSER_USERNAME\\\").exists():" \
        "    User.objects.create_superuser(\\\"$DJANGO_SUPERUSER_USERNAME\\\", \\\"$DJANGO_SUPERUSER_EMAIL\\\", \\\"$DJANGO_SUPERUSER_PASSWORD\\\")" \
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

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--worker-class", "gthread", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]

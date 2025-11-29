# ==============================================================================
# Multi-stage Dockerfile for SmartHR360 Future Skills Platform
# ==============================================================================
# Stage 1: Builder - Install dependencies and compile Python packages
# Stage 2: Runtime - Minimal production image
# ==============================================================================

# ==============================================================================
# Stage 1: Builder
# ==============================================================================
FROM python:3.11-slim as builder

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
    libpq-dev \
    gcc \
    g++ \
    git \
    curl \
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
RUN mkdir -p logs staticfiles media ml/models ml/data ml/results

# Collect static files
RUN python manage.py collectstatic --noinput --clear || true

# ==============================================================================
# Stage 2: Runtime
# ==============================================================================
FROM python:3.11-slim as runtime

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

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -g ${APP_GID} ${APP_USER} && \
    useradd -u ${APP_UID} -g ${APP_GID} -m -s /bin/bash ${APP_USER}

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=${APP_USER}:${APP_USER} . /app

# Copy collected static files from builder
COPY --from=builder --chown=${APP_USER}:${APP_USER} /build/app/staticfiles /app/staticfiles

# Create necessary directories with proper permissions
RUN mkdir -p logs staticfiles media ml/models ml/data ml/results && \
    chown -R ${APP_USER}:${APP_USER} /app

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Starting SmartHR360 Future Skills Platform..."\n\
\n\
# Wait for database\n\
if [ -n "$DB_HOST" ]; then\n\
    echo "Waiting for database at $DB_HOST:${DB_PORT:-5432}..."\n\
    for i in {1..30}; do\n\
        nc -z "$DB_HOST" "${DB_PORT:-5432}" && break\n\
        echo "Waiting for database... ($i/30)"\n\
        sleep 2\n\
    done\n\
fi\n\
\n\
# Run migrations if AUTO_MIGRATE is set\n\
if [ "$AUTO_MIGRATE" = "true" ]; then\n\
    echo "Running database migrations..."\n\
    python manage.py migrate --noinput\n\
fi\n\
\n\
# Create superuser if credentials provided\n\
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then\n\
    echo "Creating superuser if not exists..."\n\
    python manage.py shell -c "\n\
from django.contrib.auth import get_user_model;\n\
User = get_user_model();\n\
if not User.objects.filter(username=\"$DJANGO_SUPERUSER_USERNAME\").exists():\n\
    User.objects.create_superuser(\"$DJANGO_SUPERUSER_USERNAME\", \"$DJANGO_SUPERUSER_EMAIL\", \"$DJANGO_SUPERUSER_PASSWORD\")\n\
    print(\"Superuser created\")\n\
else:\n\
    print(\"Superuser already exists\")\n\
" || true\n\
fi\n\
\n\
echo "SmartHR360 is ready!"\n\
exec "$@"\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

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

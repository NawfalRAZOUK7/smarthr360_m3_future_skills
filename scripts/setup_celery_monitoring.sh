#!/bin/bash

# SmartHR360 Celery Monitoring Local Setup Script
# This script is for LOCAL Python onboarding only (not for Docker onboarding).
# For Docker onboarding, use scripts/docker-setup.sh instead.

set -e  # Exit on error

# ==========================================
echo "🚀 SmartHR360 Celery Monitoring Local Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}ℹ $1${NC}"; }


# --- Robust Python/venv selection (prefer .venv312, fallback .venv314, else python3) ---
print_info "Checking Python version and venv..."
if [ -d ".venv312" ]; then
    PYTHON_BIN=".venv312/bin/python"
    VENV_NAME=".venv312"
elif [ -d ".venv314" ]; then
    PYTHON_BIN=".venv314/bin/python"
    VENV_NAME=".venv314"
else
    PYTHON_BIN="python3"
    VENV_NAME="(system/global)"
fi
PYTHON_VERSION=$($PYTHON_BIN --version 2>&1 | awk '{print $2}')
print_success "Python $PYTHON_VERSION detected ($VENV_NAME)"

# --- Warn if not in project venv ---
if [ -z "$VIRTUAL_ENV" ] || [[ "$VIRTUAL_ENV" != *smarthr360_m3_future_skills* ]]; then
    print_info "You are not in the project virtual environment."
    echo "It's recommended to activate one: source $VENV_NAME/bin/activate"
    read -p "Continue anyway? (y/n): " continue_anyway
    if [[ ! $continue_anyway =~ ^[Yy]$ ]]; then
        print_error "Aborting setup. Activate the project venv and rerun."
        exit 1
    fi
else
    print_success "Virtual environment: $VIRTUAL_ENV"
fi

# --- Install Celery monitoring dependencies ---
print_info "Installing Celery monitoring dependencies from requirements_celery.txt..."
if [ -f "requirements_celery.txt" ]; then
    $PYTHON_BIN -m pip install -r requirements_celery.txt
    print_success "Celery monitoring dependencies installed"
else
    print_error "requirements_celery.txt not found. Please provide it."
    exit 1
fi

# --- Setup secrets.env for Celery Monitoring (if needed) ---
print_info "Checking for secrets.env (needed for Flower auth or external monitoring)..."
if [ ! -f "secrets.env" ]; then
    if [ -f "secrets.example" ]; then
        cp secrets.example secrets.env
        print_success "secrets.env created from secrets.example"
        print_info "Update secrets.env with your Flower or external monitoring credentials if needed."
    else
        print_info "No secrets.example found. Skipping secrets.env setup."
    fi
else
    print_info "secrets.env already exists."
fi

# --- Setup .env for Celery Monitoring (if needed) ---
print_info "Checking for .env file..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env created from .env.example"
        print_info "Update .env with any required environment variables for Celery/monitoring."
    else
        print_info "No .env.example found. Skipping .env setup."
    fi
else
    print_info ".env already exists."
fi

# --- Robust Redis Connection Check (support Docker/local) ---
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}
print_info "Checking Redis connection at $REDIS_HOST:$REDIS_PORT..."

REDIS_OK=0
if command -v redis-cli > /dev/null 2>&1; then
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping | grep -q PONG; then
        REDIS_OK=1
    else
        print_info "redis-cli found, but ping failed. Output: $(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>&1)"
    fi
else
    print_info "redis-cli not found. Trying nc..."
fi

if [ $REDIS_OK -eq 0 ]; then
    if command -v nc > /dev/null 2>&1; then
        if nc -z "$REDIS_HOST" "$REDIS_PORT"; then
            REDIS_OK=1
        else
            print_info "nc could not connect to $REDIS_HOST:$REDIS_PORT."
        fi
    else
        print_info "nc not found. Trying Python socket..."
    fi
fi

if [ $REDIS_OK -eq 0 ]; then
    python3 - <<EOF
import socket
try:
    s = socket.create_connection(("$REDIS_HOST", int("$REDIS_PORT")), timeout=2)
    s.close()
    exit(0)
except Exception as e:
    print(f"Python socket check failed: {e}")
    exit(1)
EOF
    if [ $? -eq 0 ]; then
        REDIS_OK=1
    fi
fi

if [ $REDIS_OK -eq 1 ]; then
    print_success "Redis is running at $REDIS_HOST:$REDIS_PORT"
else
    print_error "Redis is NOT running or not reachable at $REDIS_HOST:$REDIS_PORT.\nDiagnostics:"
    print_info "- redis-cli: $(command -v redis-cli || echo not found)"
    print_info "- nc: $(command -v nc || echo not found)"
    print_info "- Host: $REDIS_HOST, Port: $REDIS_PORT"
    print_info "- Try: redis-cli -h $REDIS_HOST -p $REDIS_PORT ping"
    print_info "- Try: nc -z $REDIS_HOST $REDIS_PORT"
    exit 1
fi

# --- Run Django Migrations ---
print_info "Running database migrations..."
$PYTHON_BIN manage.py migrate --noinput
print_success "Migrations complete"

# --- Create Required Directories ---
print_info "Creating log directories..."
mkdir -p logs/celery
print_success "Log directories created"

# --- Check for Port/Process Conflicts ---
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port in use
    else
        return 1  # Port free
    fi
}

if check_port 5555; then
    print_info "Port 5555 is already in use. Flower may already be running."
fi

if pgrep -f "celery.*worker" > /dev/null; then
    print_info "Celery worker process already running. Kill with: pkill -f 'celery.*worker'"
fi

# --- Final Summary and Next Steps ---
echo ""
echo "=========================================="
print_success "Celery monitoring local setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source .venv/bin/activate"
echo "  2. Update .env and secrets.env with your configuration if needed"
echo "  3. Start Celery Worker:"
echo "     celery -A config worker --loglevel=info --concurrency=4"
echo "  4. Start Celery Beat (scheduled tasks):"
echo "     celery -A config beat --loglevel=info"
echo "  5. Start Flower Monitoring UI:"
echo "     celery -A config flower --port=5555"
echo "     Access at: http://localhost:5555"
echo "  6. Start Prometheus Exporter (optional):"
echo "     celery-exporter --broker redis://localhost:6379/0"
echo "     Metrics at: http://localhost:9808/metrics"
echo "  7. View documentation:"
echo "     - Monitoring Guide: docs/CELERY_MONITORING_GUIDE.md"
echo "=========================================="
echo ""
echo "If you want to use Docker for onboarding, use: scripts/docker-setup.sh"
echo "=========================================="

# --- Offer to Start Services ---
echo ""
read -p "Start Celery worker now? (y/n): " start_worker
if [[ $start_worker =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting Celery worker in background..."
    echo "You can stop it later with: pkill -f 'celery.*worker'"
    echo ""
    nohup $PYTHON_BIN -m celery -A config worker --loglevel=info --concurrency=4 > celery_worker.log 2>&1 &
    echo "Celery worker started in background. Logs: celery_worker.log"
fi

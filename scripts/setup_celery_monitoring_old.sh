#!/bin/bash

# Celery Monitoring Setup Script
# Sets up and starts Celery worker, beat, and Flower monitoring

set -e

echo "=========================================="
echo "SmartHR360 Celery Monitoring Setup"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Not running in a virtual environment${NC}"
    echo "Activate your virtual environment first:"
    echo "  source .venv/bin/activate"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION"

# Check if Redis is running
echo ""
echo "Checking Redis connection..."
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Redis is running"
else
    echo -e "${RED}✗${NC} Redis is not running"
    echo "Start Redis with: redis-server"
    exit 1
fi

# Install/upgrade Celery monitoring dependencies
echo ""
echo "Installing Celery monitoring dependencies..."
pip install -q --upgrade \
    flower \
    django-celery-results \
    django-celery-beat \
    tenacity \
    pybreaker \
    prometheus-client

echo -e "${GREEN}✓${NC} Dependencies installed"

# Run migrations
echo ""
echo "Running database migrations..."
python manage.py migrate --noinput
echo -e "${GREEN}✓${NC} Migrations complete"

# Check if directories exist
echo ""
echo "Creating log directories..."
mkdir -p logs/celery
echo -e "${GREEN}✓${NC} Log directories created"

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port in use
    else
        return 1  # Port free
    fi
}

# Check if Flower is already running
if check_port 5555; then
    echo -e "${YELLOW}Warning: Port 5555 is already in use${NC}"
    echo "Flower may already be running"
fi

# Check if celery workers are running
if pgrep -f "celery.*worker" > /dev/null; then
    echo -e "${YELLOW}Warning: Celery worker process already running${NC}"
    echo "Kill existing workers with: pkill -f 'celery.*worker'"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. Start Celery Worker:"
echo "   ${GREEN}celery -A config worker --loglevel=info --concurrency=4${NC}"
echo ""
echo "2. Start Celery Beat (scheduled tasks):"
echo "   ${GREEN}celery -A config beat --loglevel=info${NC}"
echo ""
echo "3. Start Flower Monitoring UI:"
echo "   ${GREEN}celery -A config flower --port=5555${NC}"
echo "   Access at: ${GREEN}http://localhost:5555${NC}"
echo ""
echo "4. Start Prometheus Exporter (optional):"
echo "   ${GREEN}celery-exporter --broker redis://localhost:6379/0${NC}"
echo "   Metrics at: ${GREEN}http://localhost:9808/metrics${NC}"
echo ""
echo "=========================================="
echo "Useful Commands:"
echo "=========================================="
echo ""
echo "Check worker status:"
echo "  ${GREEN}celery -A config inspect stats${NC}"
echo ""
echo "View active tasks:"
echo "  ${GREEN}celery -A config inspect active${NC}"
echo ""
echo "Purge all queues:"
echo "  ${GREEN}celery -A config purge${NC}"
echo ""
echo "Monitor events:"
echo "  ${GREEN}celery -A config events${NC}"
echo ""
echo "=========================================="
echo "Documentation:"
echo "=========================================="
echo ""
echo "Complete guide: ${GREEN}docs/CELERY_MONITORING_GUIDE.md${NC}"
echo ""

# Offer to start services
echo ""
read -p "Start Celery worker now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting Celery worker..."
    echo "Press Ctrl+C to stop"
    echo ""
    celery -A config worker --loglevel=info --concurrency=4
fi

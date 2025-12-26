#!/bin/bash

# SmartHR360 Health Check Script
# Tests all critical services and endpoints

set -e

# Configuration
HEALTH_CHECK_URL="${HEALTH_CHECK_URL:-http://localhost:8000/api/health/}"
TIMEOUT=30
RETRIES=3

echo "Running health checks for SmartHR360..."

# Function to check HTTP endpoint
check_endpoint() {
    local url=$1
    local name=$2
    local timeout=$3

    echo -n "Checking $name ($url)... "

    if curl -f --max-time $timeout --silent "$url" > /dev/null 2>&1; then
        echo "✅ PASS"
        return 0
    else
        echo "❌ FAIL"
        return 1
    fi
}

# Function to check service
check_service() {
    local service=$1
    local command=$2

    echo -n "Checking $service... "

    if eval "$command"; then
        echo "✅ PASS"
        return 0
    else
        echo "❌ FAIL"
        return 1
    fi
}

# Health checks
FAILED_CHECKS=0

# Django application health
if ! check_endpoint "$HEALTH_CHECK_URL" "Django Health Check" 10; then
    ((FAILED_CHECKS++))
fi

# Database connectivity
if ! check_service "Database" "docker-compose -f compose/docker-compose.prod.yml exec -T db pg_isready -U postgres -d smarthr360"; then
    ((FAILED_CHECKS++))
fi

# Redis connectivity
if ! check_service "Redis" "docker-compose -f compose/docker-compose.prod.yml exec -T redis redis-cli ping | grep -q PONG"; then
    ((FAILED_CHECKS++))
fi

# Celery worker status
if ! check_service "Celery Worker" "docker-compose -f compose/docker-compose.prod.yml exec -T celery celery -A config inspect active | grep -q 'OK'"; then
    ((FAILED_CHECKS++))
fi

# MLflow server
if ! check_endpoint "http://localhost:5500" "MLflow Server" 5; then
    echo "⚠️  WARNING: MLflow server not accessible (may be expected)"
fi

# Disk usage check
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "❌ FAIL: Disk usage is ${DISK_USAGE}% (threshold: 90%)"
    ((FAILED_CHECKS++))
else
    echo "✅ PASS: Disk usage is ${DISK_USAGE}%"
fi

# Memory check (basic)
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ "$MEMORY_USAGE" -gt 90 ]; then
    echo "❌ FAIL: Memory usage is ${MEMORY_USAGE}% (threshold: 90%)"
    ((FAILED_CHECKS++))
else
    echo "✅ PASS: Memory usage is ${MEMORY_USAGE}%"
fi

# Summary
echo ""
echo "Health check summary:"
if [ "$FAILED_CHECKS" -eq 0 ]; then
    echo "🎉 All health checks passed!"
    exit 0
else
    echo "💥 $FAILED_CHECKS health check(s) failed!"
    exit 1
fi

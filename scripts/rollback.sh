#!/bin/bash

##############################################################################
# Automated Rollback Script for SmartHR360
#
# This script performs an automated rollback to the previous version
##############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="${NAMESPACE:-smarthr360}"
COMPONENT="${1:-all}"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     SmartHR360 Automated Rollback                   ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to rollback deployment
rollback_deployment() {
    local deployment=$1

    echo -e "${YELLOW}Rolling back ${deployment}...${NC}"

    # Check if deployment exists
    if ! kubectl get deployment $deployment -n $NAMESPACE &> /dev/null; then
        echo -e "${RED}❌ Deployment $deployment not found${NC}"
        return 1
    fi

    # Get current and previous revisions
    CURRENT_REVISION=$(kubectl rollout history deployment/$deployment -n $NAMESPACE | tail -n 1 | awk '{print $1}')
    PREVIOUS_REVISION=$(kubectl rollout history deployment/$deployment -n $NAMESPACE | tail -n 2 | head -n 1 | awk '{print $1}')

    echo -e "${BLUE}Current revision: ${CURRENT_REVISION}${NC}"
    echo -e "${BLUE}Rolling back to revision: ${PREVIOUS_REVISION}${NC}"

    # Perform rollback
    kubectl rollout undo deployment/$deployment -n $NAMESPACE

    # Wait for rollback to complete
    echo "Waiting for rollback to complete..."
    kubectl rollout status deployment/$deployment -n $NAMESPACE --timeout=5m

    echo -e "${GREEN}✅ ${deployment} rolled back successfully${NC}"

    # Show revision history
    echo ""
    echo "Deployment history:"
    kubectl rollout history deployment/$deployment -n $NAMESPACE | tail -n 5
}

# Main rollback logic
case $COMPONENT in
    "api"|"API")
        rollback_deployment "smarthr360-api"
        ;;

    "celery-worker"|"worker")
        rollback_deployment "smarthr360-celery-worker"
        ;;

    "celery-beat"|"beat")
        rollback_deployment "smarthr360-celery-beat"
        ;;

    "all"|"ALL")
        echo -e "${YELLOW}Rolling back all components...${NC}"
        echo ""

        rollback_deployment "smarthr360-api"
        echo ""

        rollback_deployment "smarthr360-celery-worker"
        echo ""

        rollback_deployment "smarthr360-celery-beat"
        ;;

    *)
        echo -e "${RED}Error: Unknown component: $COMPONENT${NC}"
        echo "Usage: $0 [api|celery-worker|celery-beat|all]"
        echo "Example: $0 api"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Rollback Complete!                                ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Verify deployment health
echo -e "${BLUE}Verifying deployment health...${NC}"
kubectl get pods -n $NAMESPACE
echo ""

# Check for any issues
NOT_READY=$(kubectl get pods -n $NAMESPACE --field-selector=status.phase!=Running --no-headers 2>/dev/null | wc -l)
if [ $NOT_READY -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Warning: $NOT_READY pods are not running${NC}"
    kubectl get pods -n $NAMESPACE --field-selector=status.phase!=Running
else
    echo -e "${GREEN}✅ All pods are running${NC}"
fi

# Test API health
echo ""
echo -e "${BLUE}Testing API health...${NC}"
API_POD=$(kubectl get pod -n $NAMESPACE -l component=api -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -n "$API_POD" ]; then
    kubectl port-forward -n $NAMESPACE $API_POD 8001:8000 &
    PF_PID=$!

    sleep 5

    if curl -f http://localhost:8001/api/health/ -s > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API health check passed${NC}"
    else
        echo -e "${YELLOW}⚠️  API health check failed${NC}"
    fi

    kill $PF_PID 2>/dev/null || true
else
    echo -e "${YELLOW}⚠️  Could not find API pod for health check${NC}"
fi

echo ""
echo -e "${GREEN}Rollback verification complete${NC}"

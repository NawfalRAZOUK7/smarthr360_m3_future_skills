#!/bin/bash

##############################################################################
# Canary Deployment Script for SmartHR360
#
# This script performs a canary deployment by gradually increasing traffic
# to the new version while monitoring metrics.
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
NEW_VERSION="${1}"
CANARY_STEPS="${CANARY_STEPS:-5,10,25,50,100}"
STEP_DURATION="${STEP_DURATION:-5m}"

if [ -z "$NEW_VERSION" ]; then
    echo -e "${RED}Error: Version tag required${NC}"
    echo "Usage: $0 <version-tag>"
    echo "Example: $0 v1.2.0"
    exit 1
fi

echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     SmartHR360 Canary Deployment                    ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Version: ${NEW_VERSION}${NC}"
echo -e "${GREEN}Namespace: ${NAMESPACE}${NC}"
echo -e "${GREEN}Canary steps: ${CANARY_STEPS}${NC}"
echo -e "${GREEN}Step duration: ${STEP_DURATION}${NC}"
echo ""

# Function to check health
check_health() {
    local deployment=$1
    local error_threshold=${2:-10}

    echo "Checking health of $deployment..."

    # Check pod status
    READY_PODS=$(kubectl get deployment $deployment -n $NAMESPACE -o jsonpath='{.status.readyReplicas}')
    DESIRED_PODS=$(kubectl get deployment $deployment -n $NAMESPACE -o jsonpath='{.spec.replicas}')

    if [ "$READY_PODS" != "$DESIRED_PODS" ]; then
        echo -e "${RED}❌ Not all pods are ready: $READY_PODS/$DESIRED_PODS${NC}"
        return 1
    fi

    # Check error rate
    ERROR_COUNT=$(kubectl logs -n $NAMESPACE -l deployment=$deployment --since=1m | grep ERROR | wc -l || echo "0")
    if [ $ERROR_COUNT -gt $error_threshold ]; then
        echo -e "${RED}❌ High error rate: $ERROR_COUNT errors${NC}"
        return 1
    fi

    echo -e "${GREEN}✅ Health check passed${NC}"
    return 0
}

# Function to calculate replicas for percentage
calculate_replicas() {
    local total=$1
    local percentage=$2
    echo $(( ($total * $percentage) / 100 ))
}

# Step 1: Get current deployment info
echo -e "${BLUE}Step 1: Getting current deployment info...${NC}"

CURRENT_REPLICAS=$(kubectl get deployment smarthr360-api -n $NAMESPACE -o jsonpath='{.spec.replicas}')
echo -e "${GREEN}Current replicas: ${CURRENT_REPLICAS}${NC}"

# Step 2: Create canary deployment
echo -e "${BLUE}Step 2: Creating canary deployment...${NC}"

# Export current deployment and modify for canary
kubectl get deployment smarthr360-api -n $NAMESPACE -o yaml | \
    sed 's/name: smarthr360-api/name: smarthr360-api-canary/' | \
    sed "s|image: .*/smarthr360-api:.*|image: ghcr.io/your-org/smarthr360-api:${NEW_VERSION}|" | \
    sed 's/replicas: .*/replicas: 1/' | \
    kubectl apply -f -

# Add canary label
kubectl patch deployment smarthr360-api-canary -n $NAMESPACE -p '{"spec":{"template":{"metadata":{"labels":{"version":"canary"}}}}}'

echo -e "${GREEN}✅ Canary deployment created with 1 replica${NC}"

# Wait for canary to be ready
kubectl rollout status deployment/smarthr360-api-canary -n $NAMESPACE --timeout=5m

# Step 3: Gradual rollout
echo -e "${BLUE}Step 3: Starting gradual rollout...${NC}"

IFS=',' read -ra STEPS <<< "$CANARY_STEPS"

for PERCENTAGE in "${STEPS[@]}"; do
    echo ""
    echo -e "${YELLOW}═══ Rolling out to ${PERCENTAGE}% ═══${NC}"

    # Calculate replicas
    CANARY_REPLICAS=$(calculate_replicas $CURRENT_REPLICAS $PERCENTAGE)
    STABLE_REPLICAS=$(( $CURRENT_REPLICAS - $CANARY_REPLICAS ))

    # Ensure at least 1 replica
    if [ $CANARY_REPLICAS -lt 1 ]; then
        CANARY_REPLICAS=1
    fi
    if [ $STABLE_REPLICAS -lt 1 ]; then
        STABLE_REPLICAS=1
    fi

    echo -e "${GREEN}Canary replicas: ${CANARY_REPLICAS}${NC}"
    echo -e "${GREEN}Stable replicas: ${STABLE_REPLICAS}${NC}"

    # Scale deployments
    kubectl scale deployment smarthr360-api-canary -n $NAMESPACE --replicas=$CANARY_REPLICAS
    kubectl scale deployment smarthr360-api -n $NAMESPACE --replicas=$STABLE_REPLICAS

    # Wait for scaling
    kubectl rollout status deployment/smarthr360-api-canary -n $NAMESPACE --timeout=5m

    echo -e "${BLUE}Monitoring for ${STEP_DURATION}...${NC}"

    # Convert duration to seconds
    DURATION_SECONDS=$(echo $STEP_DURATION | sed 's/m/*60/' | sed 's/s//' | bc)
    CHECKS=$(( $DURATION_SECONDS / 30 ))

    ROLLBACK_NEEDED=0
    for ((i=1; i<=$CHECKS; i++)); do
        echo -n "."
        sleep 30

        # Check canary health
        if ! check_health "smarthr360-api-canary" 5; then
            echo ""
            echo -e "${RED}❌ Canary health check failed!${NC}"
            ROLLBACK_NEEDED=1
            break
        fi
    done
    echo ""

    if [ $ROLLBACK_NEEDED -eq 1 ]; then
        echo -e "${RED}Initiating rollback...${NC}"

        # Scale canary to 0
        kubectl scale deployment smarthr360-api-canary -n $NAMESPACE --replicas=0

        # Restore stable replicas
        kubectl scale deployment smarthr360-api -n $NAMESPACE --replicas=$CURRENT_REPLICAS

        echo -e "${RED}❌ Canary deployment failed and was rolled back${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ ${PERCENTAGE}% rollout successful${NC}"

    if [ $PERCENTAGE -ne 100 ]; then
        read -p "Continue to next step? (yes/no/rollback): " CONFIRM
        if [ "$CONFIRM" == "rollback" ]; then
            echo -e "${YELLOW}Rolling back deployment...${NC}"
            kubectl scale deployment smarthr360-api-canary -n $NAMESPACE --replicas=0
            kubectl scale deployment smarthr360-api -n $NAMESPACE --replicas=$CURRENT_REPLICAS
            echo -e "${YELLOW}Rollback complete${NC}"
            exit 0
        elif [ "$CONFIRM" != "yes" ]; then
            echo -e "${YELLOW}Canary deployment paused${NC}"
            echo -e "${YELLOW}Current state: ${PERCENTAGE}% canary traffic${NC}"
            exit 0
        fi
    fi
done

# Step 4: Finalize deployment
echo ""
echo -e "${BLUE}Step 4: Finalizing deployment...${NC}"

# Update main deployment to new version
kubectl set image deployment/smarthr360-api -n $NAMESPACE \
    api=ghcr.io/your-org/smarthr360-api:${NEW_VERSION}

# Scale back to original replicas
kubectl scale deployment smarthr360-api -n $NAMESPACE --replicas=$CURRENT_REPLICAS

# Wait for rollout
kubectl rollout status deployment/smarthr360-api -n $NAMESPACE --timeout=10m

# Scale down canary
kubectl scale deployment smarthr360-api-canary -n $NAMESPACE --replicas=0

echo -e "${GREEN}✅ Main deployment updated${NC}"

# Step 5: Cleanup
echo -e "${BLUE}Step 5: Cleaning up...${NC}"
read -p "Delete canary deployment? (yes/no): " CLEANUP

if [ "$CLEANUP" == "yes" ]; then
    kubectl delete deployment smarthr360-api-canary -n $NAMESPACE
    echo -e "${GREEN}✅ Canary deployment removed${NC}"
else
    echo -e "${YELLOW}Canary deployment kept (scaled to 0)${NC}"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Canary Deployment Complete!                      ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}All traffic now on version: ${NEW_VERSION}${NC}"

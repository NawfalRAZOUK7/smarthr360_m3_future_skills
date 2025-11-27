#!/bin/bash

# SmartHR360 Test Runner Script
# Provides convenient commands to run different test suites

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Parse command line arguments
TEST_TYPE=${1:-all}
VERBOSE=${2:--v}

print_info "Running SmartHR360 Tests..."
echo ""

case $TEST_TYPE in
    "all")
        print_info "Running all tests with coverage..."
        pytest --cov=future_skills --cov-report=html --cov-report=term-missing $VERBOSE
        print_success "All tests completed. Coverage report: htmlcov/index.html"
        ;;
    
    "unit")
        print_info "Running unit tests only..."
        pytest future_skills/tests/ $VERBOSE -m "not slow"
        print_success "Unit tests completed"
        ;;
    
    "integration")
        print_info "Running integration tests..."
        pytest tests/integration/ $VERBOSE
        print_success "Integration tests completed"
        ;;
    
    "e2e")
        print_info "Running end-to-end tests..."
        pytest tests/e2e/ $VERBOSE
        print_success "E2E tests completed"
        ;;
    
    "fast")
        print_info "Running fast tests only (excluding slow tests)..."
        pytest $VERBOSE -m "not slow"
        print_success "Fast tests completed"
        ;;
    
    "ml")
        print_info "Running ML-related tests..."
        pytest $VERBOSE -m "ml"
        print_success "ML tests completed"
        ;;
    
    "api")
        print_info "Running API tests..."
        pytest $VERBOSE -m "api"
        print_success "API tests completed"
        ;;
    
    "coverage")
        print_info "Generating detailed coverage report..."
        pytest --cov=future_skills --cov-report=html --cov-report=term-missing --cov-report=json
        print_success "Coverage report generated: htmlcov/index.html"
        echo ""
        python -m coverage report --show-missing
        ;;
    
    "failed")
        print_info "Re-running last failed tests..."
        pytest --lf $VERBOSE
        print_success "Failed tests re-run completed"
        ;;
    
    "specific")
        if [ -z "$2" ]; then
            echo "Usage: $0 specific <test_path>"
            echo "Example: $0 specific tests/integration/test_prediction_flow.py::TestPredictionFlow::test_complete_prediction_flow"
            exit 1
        fi
        print_info "Running specific test: $2"
        pytest "$2" -v
        print_success "Specific test completed"
        ;;
    
    "help"|"-h"|"--help")
        echo "SmartHR360 Test Runner"
        echo ""
        echo "Usage: $0 [TEST_TYPE] [OPTIONS]"
        echo ""
        echo "Test Types:"
        echo "  all          - Run all tests with coverage (default)"
        echo "  unit         - Run unit tests only"
        echo "  integration  - Run integration tests"
        echo "  e2e          - Run end-to-end tests"
        echo "  fast         - Run fast tests (exclude slow tests)"
        echo "  ml           - Run ML-related tests"
        echo "  api          - Run API tests"
        echo "  coverage     - Generate detailed coverage report"
        echo "  failed       - Re-run last failed tests"
        echo "  specific     - Run specific test (requires test path)"
        echo "  help         - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0                    # Run all tests"
        echo "  $0 unit               # Run unit tests"
        echo "  $0 integration -vv    # Run integration tests with verbose output"
        echo "  $0 specific tests/integration/test_prediction_flow.py"
        exit 0
        ;;
    
    *)
        echo "Unknown test type: $TEST_TYPE"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac

echo ""
print_info "Test execution completed"

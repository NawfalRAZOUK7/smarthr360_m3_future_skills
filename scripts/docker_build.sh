#!/bin/bash


# SmartHR360 Docker Build and Deploy Script
# Hardened: Logging, error handling, script checks, Compose compatibility

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ $1${NC}"; }
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_warn() { echo -e "${YELLOW}⚠ $1${NC}"; }

# --- Logging setup ---
LOG_FILE="docker-build.log"
echo "=========================================="
print_info "SmartHR360 Docker Build (logging to $LOG_FILE)"
echo "=========================================="
print_info "All build and onboarding output will be logged to $LOG_FILE"

# --- Compose command detection ---
if command -v docker compose &>/dev/null; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

# --- Ensure all onboarding scripts are executable ---
ONBOARDING_SCRIPTS=(
    "scripts/ml_train.sh"
    "scripts/setup_mlflow.sh"
    "scripts/setup_celery_monitoring.sh"
)
for SCRIPT_PATH in "${ONBOARDING_SCRIPTS[@]}"; do
    if [ ! -x "$SCRIPT_PATH" ]; then
        chmod +x "$SCRIPT_PATH" || print_warn "Could not set executable permission for $SCRIPT_PATH"
    fi
done
print_success "Script permissions checked: ${ONBOARDING_SCRIPTS[*]}"

# Parse command
COMMAND=${1:-help}

case $COMMAND in

        "dev")
                print_info "Building and starting development environment... (logging to $LOG_FILE)"
                $COMPOSE up -d --build >> "$LOG_FILE" 2>&1
                if [ $? -ne 0 ]; then
                    print_error "Development environment failed to start. See $LOG_FILE for details."
                    tail -20 "$LOG_FILE"
                    exit 1
                fi
                print_success "Development environment is running"
                echo ""
                echo "Services:"
                $COMPOSE ps
                echo ""
                echo "Access the application at: http://localhost:8000"
                echo "View logs: $COMPOSE logs -f"
                ;;


    "prod")
        print_info "Preparing ML model before production build... (logging to $LOG_FILE)"
        MODEL_PATH="artifacts/models/future_skills_model.pkl"
        ML_VERSION=${ML_VERSION:-v1}
        if [ -f "$MODEL_PATH" ]; then
            ML_STEP="retrain"
            print_info "Existing model found. Running retrain (version: $ML_VERSION) before Docker build..."
        else
            ML_STEP="train"
            print_info "No model found. Running train (version: $ML_VERSION) before Docker build..."
        fi
        bash scripts/ml_train.sh "$ML_STEP" "$ML_VERSION" >> "$LOG_FILE" 2>&1
        if [ $? -ne 0 ]; then
            print_error "ML model $ML_STEP failed. See $LOG_FILE for details."
            tail -20 "$LOG_FILE"
            exit 1
        fi
        print_success "ML model $ML_STEP complete."
        echo ""
        print_info "Running ML experiment... (logging to $LOG_FILE)"
        bash scripts/ml_train.sh experiment >> "$LOG_FILE" 2>&1
        if [ $? -ne 0 ]; then
            print_error "ML experiment failed. See $LOG_FILE for details."
            tail -20 "$LOG_FILE"
            exit 1
        fi
        print_success "ML experiment completed."
        print_info "Evaluating trained models... (logging to $LOG_FILE)"
        bash scripts/ml_train.sh evaluate >> "$LOG_FILE" 2>&1
        if [ $? -ne 0 ]; then
            print_error "ML evaluation failed. See $LOG_FILE for details."
            tail -20 "$LOG_FILE"
            exit 1
        fi
        print_success "ML evaluation completed."
        print_info "Generating predictions for test employee (ID: 1)... (logging to $LOG_FILE)"
        bash scripts/ml_train.sh predict 1 >> "$LOG_FILE" 2>&1 || print_warn "(Prediction step skipped or failed)"
        print_info "Building and starting production environment... (logging to $LOG_FILE)"
        $COMPOSE -f docker-compose.prod.yml up -d --build >> "$LOG_FILE" 2>&1
        if [ $? -ne 0 ]; then
            print_error "Production environment failed to start. See $LOG_FILE for details."
            tail -20 "$LOG_FILE"
            exit 1
        fi
        print_success "Production environment is running"
        echo ""
        echo "Services:"
        $COMPOSE -f docker-compose.prod.yml ps
        echo ""
        echo "Access the application at: http://localhost"
        ;;


    "build")
        ENV=${2:-dev}
        print_info "Checking if Docker is running..."
        if ! docker info >/dev/null 2>&1; then
            print_error "Docker is not running."
            read -p "Do you want to run docker-setup.sh now? (y/n): " setup_choice
            if [ "$setup_choice" = "y" ] || [ "$setup_choice" = "Y" ]; then
                if [ -f "$(dirname "$0")/docker-setup.sh" ]; then
                    print_info "Running docker-setup.sh... (logging to $LOG_FILE)"
                    bash "$(dirname "$0")/docker-setup.sh" >> "$LOG_FILE" 2>&1
                else
                    print_error "docker-setup.sh not found in scripts directory."
                    exit 1
                fi
            else
                print_info "Build cancelled. Please start Docker and try again."
                exit 1
            fi
        fi
        print_info "Building Docker image for $ENV environment... (logging to $LOG_FILE)"
        if [ "$ENV" = "prod" ]; then
            $COMPOSE -f docker-compose.prod.yml build >> "$LOG_FILE" 2>&1
        else
            $COMPOSE build >> "$LOG_FILE" 2>&1
        fi
        if [ $? -ne 0 ]; then
            print_error "Docker image build failed. See $LOG_FILE for details."
            tail -20 "$LOG_FILE"
            exit 1
        fi
        print_success "Docker image built successfully"
        ;;


    "stop")
        ENV=${2:-dev}
        print_info "Stopping Docker containers... (logging to $LOG_FILE)"
        if [ "$ENV" = "prod" ]; then
            $COMPOSE -f docker-compose.prod.yml down >> "$LOG_FILE" 2>&1
        else
            $COMPOSE down >> "$LOG_FILE" 2>&1
        fi
        if [ $? -ne 0 ]; then
            print_error "Failed to stop Docker containers. See $LOG_FILE for details."
            tail -20 "$LOG_FILE"
            exit 1
        fi
        print_success "Docker containers stopped"
        ;;


    "restart")
        ENV=${2:-dev}
        print_info "Restarting Docker containers... (logging to $LOG_FILE)"
        if [ "$ENV" = "prod" ]; then
            $COMPOSE -f docker-compose.prod.yml restart >> "$LOG_FILE" 2>&1
        else
            $COMPOSE restart >> "$LOG_FILE" 2>&1
        fi
        if [ $? -ne 0 ]; then
            print_error "Failed to restart Docker containers. See $LOG_FILE for details."
            tail -20 "$LOG_FILE"
            exit 1
        fi
        print_success "Docker containers restarted"
        ;;


    "logs")
        SERVICE=${2:-web}
        print_info "Showing logs for $SERVICE..."
        $COMPOSE logs -f "$SERVICE"
        ;;


    "shell")
        print_info "Opening shell in web container..."
        $COMPOSE exec web /bin/bash
        ;;


    "migrate")
        print_info "Running database migrations... (logging to $LOG_FILE)"
        $COMPOSE exec web python manage.py migrate >> "$LOG_FILE" 2>&1
        if [ $? -ne 0 ]; then
            print_error "Migrations failed. See $LOG_FILE for details."
            tail -20 "$LOG_FILE"
            exit 1
        fi
        print_success "Migrations completed"
        ;;


    "test")
        print_info "Running tests in Docker container... (logging to $LOG_FILE)"
        $COMPOSE exec web pytest --cov=future_skills >> "$LOG_FILE" 2>&1
        if [ $? -ne 0 ]; then
            print_error "Tests failed. See $LOG_FILE for details."
            tail -20 "$LOG_FILE"
            exit 1
        fi
        print_success "Tests completed"
        ;;


    "clean")
        print_info "Cleaning up Docker resources... (logging to $LOG_FILE)"
        read -p "This will remove all containers, volumes, and images. Continue? (y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            $COMPOSE down -v >> "$LOG_FILE" 2>&1
            $COMPOSE -f docker-compose.prod.yml down -v >> "$LOG_FILE" 2>&1
            docker system prune -af >> "$LOG_FILE" 2>&1
            print_success "Docker resources cleaned"
        else
            print_info "Cleanup cancelled"
        fi
        ;;


    "status")
        print_info "Docker containers status:"
        echo ""
        echo "Development:"
        $COMPOSE ps
        echo ""
        echo "Production:"
        $COMPOSE -f docker-compose.prod.yml ps
        ;;


    "help"|"-h"|"--help")
        echo "SmartHR360 Docker Management Script"
        echo ""
        echo "Usage: $0 [COMMAND] [OPTIONS]"
        echo ""
        echo "Commands:"
        echo "  dev          - Start development environment"
        echo "  prod         - Start production environment"
        echo "  build        - Build Docker image (dev|prod)"
        echo "  stop         - Stop containers (dev|prod)"
        echo "  restart      - Restart containers (dev|prod)"
        echo "  logs         - Show logs for service (default: web)"
        echo "  shell        - Open shell in web container"
        echo "  migrate      - Run database migrations"
        echo "  test         - Run tests in container"
        echo "  clean        - Clean up all Docker resources"
        echo "  status       - Show status of all containers"
        echo "  help         - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 dev                # Start development environment"
        echo "  $0 build prod         # Build production image"
        echo "  $0 logs web           # Show web service logs"
        echo "  $0 stop prod          # Stop production environment"
        echo ""
        echo "All build and onboarding output is logged to $LOG_FILE"
        exit 0
        ;;

    *)
        print_error "Unknown command: $COMMAND"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac

print_info "All build and onboarding output is available in $LOG_FILE"

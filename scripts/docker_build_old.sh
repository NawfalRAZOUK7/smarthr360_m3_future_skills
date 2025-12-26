#!/bin/bash

# SmartHR360 Docker Build and Deploy Script
# Simplifies Docker operations for development and production

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Parse command
COMMAND=${1:-help}

case $COMMAND in
    "dev")
        print_info "Building and starting development environment..."
        docker-compose up -d --build
        print_success "Development environment is running"
        echo ""
        echo "Services:"
        docker-compose ps
        echo ""
        echo "Access the application at: http://localhost:8000"
        echo "View logs: docker-compose logs -f"
        ;;

    "prod")
        print_info "Preparing ML model before production build..."
        MODEL_PATH="artifacts/models/future_skills_model.pkl"
        ML_VERSION=${ML_VERSION:-v1}
        if [ -f "$MODEL_PATH" ]; then
            ML_STEP="retrain"
            print_info "Existing model found. Running retrain (version: $ML_VERSION) before Docker build..."
        else
            ML_STEP="train"
            print_info "No model found. Running train (version: $ML_VERSION) before Docker build..."
        fi
        if bash scripts/ml_train.sh "$ML_STEP" "$ML_VERSION"; then
            print_success "ML model $ML_STEP complete."
            echo ""
            print_info "Running ML experiment..."
            bash scripts/ml_train.sh experiment
            print_info "Evaluating trained models..."
            bash scripts/ml_train.sh evaluate
            print_info "Generating predictions for test employee (ID: 1)..."
            bash scripts/ml_train.sh predict 1 || print_info "(Prediction step skipped or failed)"
        else
            print_error "ML model $ML_STEP failed. Aborting build."
            exit 1
        fi
        print_info "Building and starting production environment..."
        docker-compose -f compose/docker-compose.prod.yml up -d --build
        print_success "Production environment is running"
        echo ""
        echo "Services:"
        docker-compose -f compose/docker-compose.prod.yml ps
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
                    print_info "Running docker-setup.sh..."
                    bash "$(dirname "$0")/docker-setup.sh"
                else
                    print_error "docker-setup.sh not found in scripts directory."
                    exit 1
                fi
            else
                print_info "Build cancelled. Please start Docker and try again."
                exit 1
            fi
        fi
        print_info "Building Docker image for $ENV environment..."
        if [ "$ENV" = "prod" ]; then
            docker-compose -f compose/docker-compose.prod.yml build
        else
            docker-compose build
        fi
        print_success "Docker image built successfully"
        ;;

    "stop")
        ENV=${2:-dev}
        print_info "Stopping Docker containers..."
        if [ "$ENV" = "prod" ]; then
            docker-compose -f compose/docker-compose.prod.yml down
        else
            docker-compose down
        fi
        print_success "Docker containers stopped"
        ;;

    "restart")
        ENV=${2:-dev}
        print_info "Restarting Docker containers..."
        if [ "$ENV" = "prod" ]; then
            docker-compose -f compose/docker-compose.prod.yml restart
        else
            docker-compose restart
        fi
        print_success "Docker containers restarted"
        ;;

    "logs")
        SERVICE=${2:-web}
        print_info "Showing logs for $SERVICE..."
        docker-compose logs -f "$SERVICE"
        ;;

    "shell")
        print_info "Opening shell in web container..."
        docker-compose exec web /bin/bash
        ;;

    "migrate")
        print_info "Running database migrations..."
        docker-compose exec web python manage.py migrate
        print_success "Migrations completed"
        ;;

    "test")
        print_info "Running tests in Docker container..."
        docker-compose exec web pytest --cov=future_skills
        print_success "Tests completed"
        ;;

    "clean")
        print_info "Cleaning up Docker resources..."
        read -p "This will remove all containers, volumes, and images. Continue? (y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            docker-compose down -v
            docker-compose -f compose/docker-compose.prod.yml down -v
            docker system prune -af
            print_success "Docker resources cleaned"
        else
            print_info "Cleanup cancelled"
        fi
        ;;

    "status")
        print_info "Docker containers status:"
        echo ""
        echo "Development:"
        docker-compose ps
        echo ""
        echo "Production:"
        docker-compose -f compose/docker-compose.prod.yml ps
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
        exit 0
        ;;

    *)
        print_error "Unknown command: $COMMAND"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac

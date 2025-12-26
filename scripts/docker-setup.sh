#!/bin/bash
set -e

# ==========================================
# SmartHR360 Docker Setup Script
# ==========================================
LOG_FILE="var/docker-setup.log"
echo "=========================================="
echo -e "\033[0;34mSmartHR360 Docker Setup (logging to $LOG_FILE)\033[0m"
echo "=========================================="
echo -e "\033[0;34m[INFO] All onboarding output will be logged to $LOG_FILE\033[0m"

# --- Check for required environment files ---
echo "[docker-setup] === Check for required environment files ==="
echo "[docker-setup] Checking for .env.docker and secrets.env..."
echo "🔎 Checking environment files..."
if [ ! -f .env.docker ]; then
    echo "⚠️  No .env.docker file found. Creating from .env.docker.example..."
    if [ -f .env.docker.example ]; then
        cp .env.docker.example .env.docker
        echo "✅ Created .env.docker file. Please update it with your values."
    else
        echo "❌ .env.docker.example not found. Cannot create .env.docker file."
        exit 1
    fi
fi
if [ ! -f secrets.env ]; then
    echo "⚠️  No secrets.env file found. Creating from secrets.example..."
    if [ -f secrets.example ]; then
        cp secrets.example secrets.env
        echo "✅ Created secrets.env file. Please update it with your secrets."
    else
        echo "❌ secrets.example not found. Cannot create secrets.env file."
        exit 1
    fi
fi

# --- Check for Docker and Docker Compose ---
echo "[docker-setup] === Check for Docker and Docker Compose ==="
echo "[docker-setup] Checking if 'docker' and 'docker-compose' are installed..."
echo "🔎 Checking Docker and Docker Compose installation..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi
if ! command -v docker-compose &> /dev/null && ! docker compose version >/dev/null 2>&1; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi
echo "✅ Docker and Docker Compose are installed"

# --- Ensure Redis is running (try Docker Compose, fallback to redis-server) ---
echo "[docker-setup] === Ensure Redis is running (Docker Compose or local) ==="
echo "[docker-setup] Checking if Redis is running on localhost:6379..."
echo "🔎 Checking if Redis is running..."
if ! (pgrep -f redis-server > /dev/null || nc -z localhost 6379); then
    echo "⚠️  Redis is not running. Attempting to start Redis via Docker Compose..."
    if docker compose config | grep -q redis; then
        docker compose up -d redis
        sleep 3
        if nc -z localhost 6379; then
            echo "✅ Redis started via Docker Compose."
        else
            echo "❌ Failed to start Redis via Docker Compose. Trying local redis-server..."
            if command -v redis-server &> /dev/null; then
                redis-server &
                sleep 3
                if nc -z localhost 6379; then
                    echo "✅ Redis started locally."
                else
                    echo "❌ Could not start Redis. Please start Redis manually."
                    exit 1
                fi
            else
                echo "❌ redis-server not found. Please install Redis or ensure it is running."
                exit 1
            fi
        fi
    else
        echo "❌ No Redis service found in Docker Compose. Trying local redis-server..."
        if command -v redis-server &> /dev/null; then
            redis-server &
            sleep 3
            if nc -z localhost 6379; then
                echo "✅ Redis started locally."
            else
                echo "❌ Could not start Redis. Please start Redis manually."
                exit 1
            fi
        else
            echo "❌ redis-server not found. Please install Redis or ensure it is running."
            exit 1
        fi
    fi
else
    echo "✅ Redis is already running."
fi

# --- Wait for Redis to be ready (max 30s) ---
echo "[docker-setup] === Wait for Redis to be ready (max 30s) ==="
echo "[docker-setup] Waiting for Redis to accept connections (timeout: $REDIS_WAIT_TIMEOUT seconds)..."
echo -e "\033[0;34m[INFO] Waiting for Redis to be ready...\033[0m"
REDIS_WAIT_TIMEOUT=30
REDIS_WAIT_INTERVAL=1
REDIS_WAIT_ELAPSED=0
while ! nc -z localhost 6379; do
    sleep $REDIS_WAIT_INTERVAL
    REDIS_WAIT_ELAPSED=$((REDIS_WAIT_ELAPSED + REDIS_WAIT_INTERVAL))
    if [ $REDIS_WAIT_ELAPSED -ge $REDIS_WAIT_TIMEOUT ]; then
        echo -e "\033[0;31m✗ Timed out waiting for Redis to be ready after $REDIS_WAIT_TIMEOUT seconds.\033[0m"
        exit 1
    fi
done
echo -e "\033[0;32m✓ Redis is ready.\033[0m"

# --- Ensure ml/models directory exists for Docker build ---
echo "[docker-setup] === Ensure ml/models directory exists for Docker build ==="
echo "[docker-setup] Checking for ml/models directory..."
echo "📁 Creating missing ml/models directory for Docker build..."
if [ ! -d "ml/models" ]; then
    mkdir -p ml/models
    touch ml/models/.gitkeep
    echo "✅ ml/models directory created."
else
    echo "✅ ml/models directory already exists."
fi

# --- Parse environment argument (dev/prod) ---
echo "[docker-setup] === Parse environment argument (dev/prod) ==="
echo "[docker-setup] Environment argument: $ENV (default: dev)"
echo "🔎 Parsing environment argument (default: dev)..."
ENV=${1:-dev}
if [ "$ENV" = "prod" ]; then
    COMPOSE="docker-compose -f compose/docker-compose.prod.yml"
else
    COMPOSE="docker-compose"
fi


# --- Logging setup ---
echo "[docker-setup] === Logging setup ==="
echo "[docker-setup] All output will be logged to $LOG_FILE."
echo "[docker-setup] Log file: $LOG_FILE"
LOG_FILE="docker-setup.log"
touch "$LOG_FILE"


# --- Ensure all onboarding scripts are executable ---
echo "[docker-setup] === Ensure all onboarding scripts are executable ==="
echo "[docker-setup] Checking permissions for onboarding scripts..."
ONBOARDING_SCRIPTS=(
    "scripts/setup_celery_monitoring.sh"
    "scripts/setup_mlflow.sh"
    "scripts/ml_train.sh"
)
echo -e "\033[0;34m[INFO] Checking onboarding script permissions...\033[0m"
for SCRIPT_PATH in "${ONBOARDING_SCRIPTS[@]}"; do
    if [ ! -x "$SCRIPT_PATH" ]; then
        chmod +x "$SCRIPT_PATH" || echo -e "\033[1;33m⚠ Could not set executable permission for $SCRIPT_PATH\033[0m"
    fi
done
echo -e "\033[0;32m✓ Script permissions checked: ${ONBOARDING_SCRIPTS[*]}\033[0m"


# --- Run pre-setup scripts for dependencies with error handling and logging ---

echo "[docker-setup] === Run pre-setup scripts for dependencies ==="
echo "[docker-setup] Running setup_celery_monitoring.sh and setup_mlflow.sh interactively..."

# Run setup_celery_monitoring.sh interactively so prompts appear in main terminal
SCRIPT_PATH="scripts/setup_celery_monitoring.sh"
echo -e "\033[0;34m[INFO] Running $SCRIPT_PATH interactively\033[0m"
bash "$SCRIPT_PATH"
if [ $? -ne 0 ]; then
    echo -e "\033[0;31m✗ $SCRIPT_PATH failed. See $LOG_FILE for details.\033[0m"
    tail -20 "$LOG_FILE"
    exit 1
else
    echo -e "\033[0;32m✓ $SCRIPT_PATH completed successfully.\033[0m"
fi

# Run setup_mlflow.sh interactively so prompts appear in main terminal
SCRIPT_PATH="scripts/setup_mlflow.sh"
echo -e "\033[0;34m[INFO] Running $SCRIPT_PATH interactively\033[0m"
bash "$SCRIPT_PATH"
if [ $? -ne 0 ]; then
    echo -e "\033[0;31m✗ $SCRIPT_PATH failed. See $LOG_FILE for details.\033[0m"
    tail -20 "$LOG_FILE"
    exit 1
else
    echo -e "\033[0;32m✓ $SCRIPT_PATH completed successfully.\033[0m"
fi


# --- Train or retrain ML model before Docker build ---
echo "[docker-setup] === Train or retrain ML model before Docker build ==="
echo "[docker-setup] Checking if ML model exists at $MODEL_PATH (version: $ML_VERSION)..."
echo -e "\033[0;34m[INFO] Checking ML model status and training if needed...\033[0m"
MODEL_PATH="artifacts/models/future_skills_model.pkl"
ML_VERSION=${ML_VERSION:-v1}
if [ -f "$MODEL_PATH" ]; then
        ML_STEP="retrain"
        echo -e "\033[0;34m[INFO] Existing model found. Running retrain (version: $ML_VERSION) before Docker build...\033[0m"
else
        ML_STEP="train"
        echo -e "\033[0;34m[INFO] No model found. Running train (version: $ML_VERSION) before Docker build...\033[0m"
fi
SCRIPT_PATH="scripts/ml_train.sh"
echo -e "\033[0;34m[INFO] Running $SCRIPT_PATH $ML_STEP interactively\033[0m"
bash "$SCRIPT_PATH" "$ML_STEP" "$ML_VERSION"
if [ $? -ne 0 ]; then
    echo -e "\033[0;31m✗ $SCRIPT_PATH $ML_STEP failed. See $LOG_FILE for details.\033[0m"
    tail -20 "$LOG_FILE"
    exit 1
else
    echo -e "\033[0;32m✓ $SCRIPT_PATH $ML_STEP completed successfully.\033[0m"
fi

echo -e "\033[0;34m[INFO] Running $SCRIPT_PATH experiment interactively\033[0m"
python3 ml/scripts/experiment_future_skills_models.py
if [ $? -ne 0 ]; then
    echo -e "\033[0;31m✗ $SCRIPT_PATH experiment failed. See $LOG_FILE for details.\033[0m"
    tail -20 "$LOG_FILE"
    exit 1
else
    echo -e "\033[0;32m✓ $SCRIPT_PATH experiment completed successfully.\033[0m"
fi

echo -e "\033[0;34m[INFO] Running $SCRIPT_PATH evaluate interactively\033[0m"
python3 ml/scripts/evaluate_future_skills_models.py
if [ $? -ne 0 ]; then
    echo -e "\033[0;31m✗ $SCRIPT_PATH evaluate failed. See $LOG_FILE for details.\033[0m"
    tail -20 "$LOG_FILE"
    exit 1
else
    echo -e "\033[0;32m✓ $SCRIPT_PATH evaluate completed successfully.\033[0m"
fi

echo -e "\033[0;34m[INFO] Running $SCRIPT_PATH predict 1 interactively\033[0m"
bash "$SCRIPT_PATH" predict 1 || echo -e "\033[0;33m(Prediction step skipped or failed)\033[0m"


# --- Build Docker images ---
echo "[docker-setup] === Build Docker images ==="
echo "[docker-setup] Building docker-base and docker-build targets using Makefile..."
echo -e "\033[0;34m[INFO] Building Docker base image... (logging to $LOG_FILE)\033[0m"

echo -e "\033[0;34m[INFO] Building Docker images via Makefile... (logging to $LOG_FILE)\033[0m"
make docker-base >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo -e "\033[0;31m✗ make docker-base failed. See $LOG_FILE for details.\033[0m"
    tail -20 "$LOG_FILE"
    exit 1
else
    echo -e "\033[0;32m✓ make docker-base completed successfully.\033[0m"
fi

make docker-build >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo -e "\033[0;31m✗ make docker-build failed. See $LOG_FILE for details.\033[0m"
    tail -20 "$LOG_FILE"
    exit 1
else
    echo -e "\033[0;32m✓ make docker-build completed successfully.\033[0m"
fi

echo -e "\033[0;34m[INFO] Building Docker containers for $ENV... (logging to $LOG_FILE)\033[0m"
$COMPOSE build >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo -e "\033[0;31m✗ Docker containers build failed. See $LOG_FILE for details.\033[0m"
    tail -20 "$LOG_FILE"
    exit 1
else
    echo -e "\033[0;32m✓ Docker containers built successfully.\033[0m"
fi

# --- Start Docker Compose services ---
echo "[docker-setup] === Start Docker Compose services ==="
echo "[docker-setup] Starting Docker Compose services for $ENV..."
echo -e "\033[0;34m[INFO] Starting services for $ENV... (logging to $LOG_FILE)\033[0m"
$COMPOSE up -d >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo -e "\033[0;31m✗ Failed to start services. See $LOG_FILE for details.\033[0m"
    tail -20 "$LOG_FILE"
    exit 1
else
    echo -e "\033[0;32m✓ Services started successfully.\033[0m"
fi


# --- Wait for database to be ready ---
echo "[docker-setup] === Wait for database to be ready ==="
echo "[docker-setup] Sleeping 5 seconds to allow database to initialize..."
echo -e "\033[0;34m[INFO] Waiting for database to be ready...\033[0m"
sleep 5

# --- Use correct python for manage.py ---
echo "[docker-setup] === Use correct python for manage.py ==="
# Prefer .venv312, fallback to .venv314 if not found
if [ -d ".venv312" ]; then
    echo "[docker-setup] Activating .venv312 virtual environment."
    source .venv312/bin/activate
    PYTHON_BIN=".venv312/bin/python"
elif [ -d ".venv314" ]; then
    echo "[docker-setup] .venv312 not found, activating .venv314 virtual environment."
    source .venv314/bin/activate
    PYTHON_BIN=".venv314/bin/python"
else
    echo "[docker-setup] ERROR: Neither .venv312 nor .venv314 found. Exiting."
    exit 1
fi
echo "[docker-setup] Using Python: $PYTHON_BIN"

# --- Run Django migrations ---
echo "[docker-setup] === Run Django migrations ==="
echo "[docker-setup] Running: $PYTHON_BIN manage.py migrate"
echo -e "\033[0;34m[INFO] Running database migrations... (logging to $LOG_FILE)\033[0m"
$PYTHON_BIN manage.py migrate >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo -e "\033[0;31m✗ Database migrations failed. See $LOG_FILE for details.\033[0m"
    tail -20 "$LOG_FILE"
    exit 1
else
    echo -e "\033[0;32m✓ Database migrations completed successfully.\033[0m"
fi

# --- Collect static files ---
echo "[docker-setup] === Collect static files ==="
echo "[docker-setup] Running: $PYTHON_BIN manage.py collectstatic --noinput"
echo -e "\033[0;34m[INFO] Collecting static files... (logging to $LOG_FILE)\033[0m"
$PYTHON_BIN manage.py collectstatic --noinput >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo -e "\033[0;31m✗ Collectstatic failed. See $LOG_FILE for details.\033[0m"
    tail -20 "$LOG_FILE"
    exit 1
else
    echo -e "\033[0;32m✓ Static files collected successfully.\033[0m"
fi

# --- Prompt to create Django superuser ---
echo "[docker-setup] === Prompt to create Django superuser ==="
echo "[docker-setup] Prompting user to optionally create a Django superuser..."
echo "👤 Optionally create a Django superuser..."
read -p "Would you like to create a superuser? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    $COMPOSE exec web python manage.py createsuperuser
fi

# --- Prompt to load initial data fixtures ---
echo "[docker-setup] === Prompt to load initial data fixtures ==="
echo "[docker-setup] Prompting user to optionally load initial data fixtures..."
echo "💾 Optionally load initial data fixtures..."
read -p "Would you like to load initial data fixtures? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if $COMPOSE exec web test -f future_skills/fixtures/initial_data.json; then
        $COMPOSE exec web python manage.py loaddata future_skills/fixtures/initial_data.json
        echo "✅ Fixtures loaded successfully"
    else
        echo "ℹ️  No fixtures file found at future_skills/fixtures/initial_data.json"
    fi
fi

# --- Print summary and useful commands ---
echo "[docker-setup] === Print summary and useful commands ==="
echo "[docker-setup] Setup complete. Printing summary and useful commands."
echo "=========================================="
echo -e "\033[0;32m✅ Setup complete!\033[0m"
echo "=========================================="
echo -e "\033[0;34m[INFO] All onboarding output is available in $LOG_FILE\033[0m"
echo ""
echo "🌐 Application is running at:"
echo "   - API: http://localhost:8000/api/"
echo "   - Admin: http://localhost:8000/admin/"
echo ""
echo "📊 Database connection:"
echo "   - Host: localhost"
echo "   - Port: 5432"
echo "   - Database: smarthr360"
echo "   - User: postgres"
echo "   - Password: postgres"
echo ""
echo "📝 Useful commands:"
if [ "$ENV" = "prod" ]; then
    echo "   - View logs: docker-compose -f compose/docker-compose.prod.yml logs -f"
    echo "   - Stop services: docker-compose -f compose/docker-compose.prod.yml down"
    echo "   - Restart services: docker-compose -f compose/docker-compose.prod.yml restart"
    echo "   - Run tests: docker-compose -f compose/docker-compose.prod.yml exec web pytest"
else
    echo "   - View logs: docker-compose logs -f"
    echo "   - Stop services: docker-compose down"
    echo "   - Restart services: docker-compose restart"
    echo "   - Run tests: docker-compose exec web pytest"
fi
echo ""

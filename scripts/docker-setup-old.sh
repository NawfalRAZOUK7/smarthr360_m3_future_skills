#!/bin/bash
# Docker Setup Script for SmartHR360 Future Skills

set -e

echo "=========================================="
echo "SmartHR360 Docker Setup"
echo "=========================================="

# Check for .env.docker file
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

# Check for secrets.env file
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

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Ensure Celery monitoring and dependencies are set up before ML workflow
echo ""
echo "🛠️  Setting up Celery monitoring and dependencies..."
if bash scripts/setup_celery_monitoring.sh; then
    echo "✅ Celery monitoring setup complete."
else
    echo "❌ Celery monitoring setup failed. Aborting setup."
    exit 1
fi
# Ensure MLflow and dependencies are set up before ML workflow
echo ""
echo "🛠️  Setting up MLflow and dependencies..."
if bash scripts/setup_mlflow.sh; then
    echo "✅ MLflow setup complete."
else
    echo "❌ MLflow setup failed. Aborting setup."
    exit 1
fi

# Accept environment argument: dev (default) or prod
ENV=${1:-dev}
if [ "$ENV" = "prod" ]; then
    COMPOSE="docker-compose -f docker-compose.prod.yml"
else
    COMPOSE="docker-compose"
fi

# Train or retrain ML model before building Docker images
# Determine if we need to train or retrain the ML model
MODEL_PATH="artifacts/models/future_skills_model.pkl"
ML_VERSION=${ML_VERSION:-v1}
if [ -f "$MODEL_PATH" ]; then
    ML_STEP="retrain"
    echo "🤖 Existing model found. Running retrain (version: $ML_VERSION) before Docker build..."
else
    ML_STEP="train"
    echo "🤖 No model found. Running train (version: $ML_VERSION) before Docker build..."
fi
# Run experiment, evaluate, and predict after train/retrain
if bash scripts/ml_train.sh "$ML_STEP" "$ML_VERSION"; then
    echo "✅ ML model $ML_STEP complete."
    echo ""
    echo "🔬 Running ML experiment..."
    bash scripts/ml_train.sh experiment
    echo "📊 Evaluating trained models..."
    bash scripts/ml_train.sh evaluate
    echo "🤖 Generating predictions for test employee (ID: 1)..."
    bash scripts/ml_train.sh predict 1 || echo "(Prediction step skipped or failed)"
else
    echo "❌ ML model $ML_STEP failed. Aborting setup."
    exit 1
fi

# Build base image first (required for modular Dockerfiles)
echo ""
echo "🔨 Building base image (Dockerfile.base)..."
docker build -f Dockerfile.base -t smarthr360-base:latest .

# Build containers
echo ""
echo "🔨 Building Docker containers for $ENV..."
$COMPOSE build

# Start services
echo ""
echo "🚀 Starting services for $ENV..."
$COMPOSE up -d

# Wait for database to be ready
echo ""
echo "⏳ Waiting for database to be ready..."
sleep 5

# Run migrations
echo ""
echo "🔄 Running database migrations..."
$COMPOSE exec web python manage.py migrate

# Collect static files
echo ""
echo "📦 Collecting static files..."
$COMPOSE exec web python manage.py collectstatic --noinput

# Create superuser prompt
echo ""

read -p "Would you like to create a superuser? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    $COMPOSE exec web python manage.py createsuperuser
fi

# Load fixtures if available
echo ""

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

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
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
    echo "   - View logs: docker-compose -f docker-compose.prod.yml logs -f"
    echo "   - Stop services: docker-compose -f docker-compose.prod.yml down"
    echo "   - Restart services: docker-compose -f docker-compose.prod.yml restart"
    echo "   - Run tests: docker-compose -f docker-compose.prod.yml exec web pytest"
else
    echo "   - View logs: docker-compose logs -f"
    echo "   - Stop services: docker-compose down"
    echo "   - Restart services: docker-compose restart"
    echo "   - Run tests: docker-compose exec web pytest"
fi
echo ""
# Check for secrets.env file
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
# Ensure Celery monitoring and dependencies are set up before ML workflow
echo ""
echo "🛠️  Setting up Celery monitoring and dependencies..."
if bash scripts/setup_celery_monitoring.sh; then
    echo "✅ Celery monitoring setup complete."
else
    echo "❌ Celery monitoring setup failed. Aborting setup."
    exit 1
fi
# Ensure MLflow and dependencies are set up before ML workflow
echo ""
echo "🛠️  Setting up MLflow and dependencies..."
if bash scripts/setup_mlflow.sh; then
    echo "✅ MLflow setup complete."
else
    echo "❌ MLflow setup failed. Aborting setup."
    exit 1
fi
#!/bin/bash
# Docker Setup Script for SmartHR360 Future Skills

set -e

echo "=========================================="
echo "SmartHR360 Docker Setup"
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"


# Check for .env.docker file
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


# Accept environment argument: dev (default) or prod
ENV=${1:-dev}
if [ "$ENV" = "prod" ]; then
    COMPOSE="docker-compose -f docker-compose.prod.yml"
else
    COMPOSE="docker-compose"
fi



# Train or retrain ML model before building Docker images
# Determine if we need to train or retrain the ML model
MODEL_PATH="artifacts/models/future_skills_model.pkl"
ML_VERSION=${ML_VERSION:-v1}
if [ -f "$MODEL_PATH" ]; then
    ML_STEP="retrain"
    echo "🤖 Existing model found. Running retrain (version: $ML_VERSION) before Docker build..."
else
    ML_STEP="train"
    echo "🤖 No model found. Running train (version: $ML_VERSION) before Docker build..."
fi
# Run experiment, evaluate, and predict after train/retrain
if bash scripts/ml_train.sh "$ML_STEP" "$ML_VERSION"; then
    echo "✅ ML model $ML_STEP complete."
    echo ""
    echo "🔬 Running ML experiment..."
    bash scripts/ml_train.sh experiment
    echo "📊 Evaluating trained models..."
    bash scripts/ml_train.sh evaluate
    echo "🤖 Generating predictions for test employee (ID: 1)..."
    bash scripts/ml_train.sh predict 1 || echo "(Prediction step skipped or failed)"
else
    echo "❌ ML model $ML_STEP failed. Aborting setup."
    exit 1
fi

# Build base image first (required for modular Dockerfiles)
echo ""
echo "🔨 Building base image (Dockerfile.base)..."
docker build -f Dockerfile.base -t smarthr360-base:latest .

# Build containers
echo ""
echo "🔨 Building Docker containers for $ENV..."
$COMPOSE build

# Start services
echo ""
echo "🚀 Starting services for $ENV..."
$COMPOSE up -d


# Wait for database to be ready
echo ""
echo "⏳ Waiting for database to be ready..."
sleep 5

# Run migrations
echo ""
echo "🔄 Running database migrations..."
$COMPOSE exec web python manage.py migrate

# Collect static files
echo ""
echo "📦 Collecting static files..."
$COMPOSE exec web python manage.py collectstatic --noinput

# Create superuser prompt
echo ""

read -p "Would you like to create a superuser? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    $COMPOSE exec web python manage.py createsuperuser
fi

# Load fixtures if available
echo ""

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

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
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
    echo "   - View logs: docker-compose -f docker-compose.prod.yml logs -f"
    echo "   - Stop services: docker-compose -f docker-compose.prod.yml down"
    echo "   - Restart services: docker-compose -f docker-compose.prod.yml restart"
    echo "   - Run tests: docker-compose -f docker-compose.prod.yml exec web pytest"
else
    echo "   - View logs: docker-compose logs -f"
    echo "   - Stop services: docker-compose down"
    echo "   - Restart services: docker-compose restart"
    echo "   - Run tests: docker-compose exec web pytest"
fi
echo ""

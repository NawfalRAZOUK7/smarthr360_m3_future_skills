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

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env file. Please update it with your values."
    else
        echo "❌ .env.example not found. Cannot create .env file."
        exit 1
    fi
fi

# Build containers
echo ""
echo "🔨 Building Docker containers..."
docker-compose build

# Start services
echo ""
echo "🚀 Starting services..."
docker-compose up -d

# Wait for database to be ready
echo ""
echo "⏳ Waiting for database to be ready..."
sleep 5

# Run migrations
echo ""
echo "🔄 Running database migrations..."
docker-compose exec web python manage.py migrate

# Collect static files
echo ""
echo "📦 Collecting static files..."
docker-compose exec web python manage.py collectstatic --noinput

# Create superuser prompt
echo ""
read -p "Would you like to create a superuser? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose exec web python manage.py createsuperuser
fi

# Load fixtures if available
echo ""
read -p "Would you like to load initial data fixtures? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if docker-compose exec web test -f future_skills/fixtures/initial_data.json; then
        docker-compose exec web python manage.py loaddata future_skills/fixtures/initial_data.json
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
echo "   - View logs: docker-compose logs -f"
echo "   - Stop services: docker-compose down"
echo "   - Restart services: docker-compose restart"
echo "   - Run tests: docker-compose exec web pytest"
echo ""

# Docker Deployment Guide

This guide covers Docker deployment for the SmartHR360 Future Skills project.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
- [Production Setup](#production-setup)
- [Common Commands](#common-commands)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- At least 4GB available RAM
- At least 10GB available disk space

## Development Setup

### 1. Build and Start Services

```bash
# Build images
docker-compose build

# Start services in detached mode
docker-compose up -d

# View logs
docker-compose logs -f
```

### 2. Initialize Database

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Load initial data (if available)
docker-compose exec web python manage.py loaddata future_skills/fixtures/initial_data.json
```

### 3. Access the Application

- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/
- Database: localhost:5432 (postgres/postgres)

### 4. Development Workflow

```bash
# View service status
docker-compose ps

# Access web container shell
docker-compose exec web bash

# Run management commands
docker-compose exec web python manage.py <command>

# Run tests
docker-compose exec web pytest

# Stop services
docker-compose down

# Stop and remove volumes (warning: deletes data)
docker-compose down -v
```

## Production Setup

### 1. Environment Configuration

Create a `.env.prod` file:

```env
# Django
DEBUG=False
SECRET_KEY=your-super-secret-production-key-change-this
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Database
POSTGRES_DB=smarthr360_prod
POSTGRES_USER=smarthr360_user
POSTGRES_PASSWORD=your-secure-database-password

# Email (optional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### 2. Build and Deploy

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# Collect static files
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Create superuser
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### 3. Access Production Application

- Application: http://your-server-ip (via Nginx)
- The application will be served through Nginx reverse proxy

## Common Commands

### Container Management

```bash
# View running containers
docker-compose ps

# View all containers (including stopped)
docker-compose ps -a

# Restart a specific service
docker-compose restart web

# Rebuild a specific service
docker-compose build web

# View resource usage
docker stats
```

### Database Operations

```bash
# Create database backup
docker-compose exec db pg_dump -U postgres smarthr360 > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore database backup
docker-compose exec -T db psql -U postgres smarthr360 < backup.sql

# Access PostgreSQL shell
docker-compose exec db psql -U postgres smarthr360
```

### Logs and Debugging

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs web
docker-compose logs db

# Follow logs in real-time
docker-compose logs -f web

# View last 100 lines
docker-compose logs --tail=100 web

# View logs with timestamps
docker-compose logs -t web
```

### Maintenance

```bash
# Update dependencies
docker-compose exec web pip install -r requirements.txt

# Clear Docker cache
docker system prune -a

# Remove unused volumes
docker volume prune

# Check disk usage
docker system df
```

## Troubleshooting

### Container Won't Start

```bash
# Check container logs
docker-compose logs web

# Check if ports are available
lsof -i :8000
lsof -i :5432

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Database Connection Issues

```bash
# Verify database is running
docker-compose ps db

# Check database health
docker-compose exec db pg_isready -U postgres

# Verify connection string
docker-compose exec web env | grep DATABASE_URL
```

### Permission Issues

```bash
# Fix ownership (if needed)
docker-compose exec web chown -R 1000:1000 /app/logs
docker-compose exec web chown -R 1000:1000 /app/media
```

### Out of Memory

```bash
# Check resource usage
docker stats

# Limit container memory in docker-compose.yml:
# services:
#   web:
#     mem_limit: 1g
```

### Static Files Not Loading

```bash
# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Verify static volume
docker volume inspect smarthr360_m3_future_skills_static_volume

# Check nginx configuration
docker-compose exec nginx nginx -t
```

## Best Practices

1. **Security**

   - Never commit `.env` files with production credentials
   - Use strong, unique passwords for production
   - Regularly update base images
   - Run containers as non-root users in production

2. **Performance**

   - Use multi-stage builds for smaller images
   - Enable Docker BuildKit for faster builds
   - Use volume mounts for development, copy for production
   - Configure appropriate worker counts for Gunicorn

3. **Monitoring**

   - Set up health checks for all services
   - Monitor container resource usage
   - Implement log aggregation
   - Set up automated backups

4. **Updates**
   - Regularly update dependencies
   - Test updates in staging environment first
   - Use version tags for production images
   - Maintain rollback capability

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Nginx Documentation](https://nginx.org/en/docs/)

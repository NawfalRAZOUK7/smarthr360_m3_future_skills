# SmartHR360 CI/CD Quick Start Guide

## 🚀 Quick Implementation

This guide provides step-by-step instructions to implement the complete CI/CD pipeline for SmartHR360 Future Skills.

### Phase 1: Repository Setup (15 minutes)

1. **Create Required Branches**

   ```bash
   git checkout -b staging
   git checkout -b production
   git push origin staging production
   ```

2. **Set Up GitHub Secrets**

   - Go to Repository Settings → Secrets and variables → Actions
   - Add the following secrets:
     ```
     STAGING_SSH_PRIVATE_KEY: (Generate SSH key pair)
     PRODUCTION_SSH_PRIVATE_KEY: (Generate SSH key pair)
     STAGING_HOST: your-staging-server.com
     PRODUCTION_HOST: your-production-server.com
     STAGING_USER: deploy
     PRODUCTION_USER: deploy
     ```

3. **Configure Environment Files**
   ```bash
   cp .env.production.example .env.production
   cp .env.staging.example .env.staging
   # Edit with your actual values
   ```

### Phase 2: Server Setup (30 minutes)

1. **Staging Server Setup**

   ```bash
   # On staging server
   sudo apt update
   sudo apt install -y docker.io docker-compose git nginx

   # Create deploy user
   sudo useradd -m -s /bin/bash deploy
   sudo usermod -aG docker deploy

   # Setup SSH access for GitHub Actions
   sudo -u deploy mkdir /home/deploy/.ssh
   sudo -u deploy chmod 700 /home/deploy/.ssh
   # Add GitHub Actions public key to authorized_keys

   # Clone repository
   sudo -u deploy git clone https://github.com/YOUR-USERNAME/smarthr360_m3_future_skills.git /opt/smarthr360
   cd /opt/smarthr360

   # Setup environment
   sudo -u deploy cp .env.staging .env
   ```

2. **Production Server Setup**

   ```bash
   # On production server (similar to staging)
   sudo apt update
   sudo apt install -y docker.io docker-compose git nginx certbot

   # Setup SSL certificates
   sudo certbot certonly --standalone -d api.smarthr360.com

   # Setup similar to staging server
   ```

### Phase 3: Test the Pipeline (10 minutes)

1. **Test CI Pipeline**

   ```bash
   # Create a feature branch
   git checkout -b test-ci-pipeline
   git commit --allow-empty -m "Test CI pipeline"
   git push origin test-ci-pipeline

   # Create a pull request to trigger CI
   # Check GitHub Actions tab for results
   ```

2. **Test Build Pipeline**

   ```bash
   # Merge to staging branch
   git checkout staging
   git merge test-ci-pipeline
   git push origin staging

   # Check if build pipeline triggers
   ```

### Phase 4: Go Live (15 minutes)

1. **Deploy to Staging**

   - The staging deployment will trigger automatically when code is pushed to staging branch
   - Monitor the deployment in GitHub Actions

2. **Deploy to Production**

   - Create a GitHub release to trigger production deployment
   - Go to Repository → Releases → Create new release
   - Tag version (e.g., v1.0.0) and publish

3. **Verify Deployment**

   ```bash
   # Test health endpoint
   curl https://api.smarthr360.com/api/health/

   # Check application logs
   curl https://api.smarthr360.com/api/status/
   ```

## 📋 Checklist

### Repository Configuration

- [ ] GitHub repository created
- [ ] Required branches (main, staging) created
- [ ] GitHub Actions workflows committed
- [ ] Repository secrets configured
- [ ] Environment files created

### Server Infrastructure

- [ ] Staging server provisioned
- [ ] Production server provisioned
- [ ] Docker and docker-compose installed
- [ ] Deploy user created with SSH access
- [ ] SSL certificates configured (production)

### Testing & Validation

- [ ] CI pipeline tested (feature branch → PR)
- [ ] Build pipeline tested (push to staging)
- [ ] Staging deployment tested
- [ ] Production deployment tested
- [ ] Health checks verified

### Monitoring & Alerting

- [ ] Application monitoring configured
- [ ] Error alerting set up
- [ ] Log aggregation configured
- [ ] Backup strategy implemented

## 🔧 Troubleshooting

### Common Issues

1. **CI Pipeline Fails**

   ```bash
   # Check GitHub Actions logs
   # Verify Python version compatibility
   # Check dependency installation
   # Validate test database setup
   ```

2. **Build Pipeline Fails**

   ```bash
   # Check Docker build logs
   # Verify Dockerfile syntax
   # Check .dockerignore configuration
   # Validate build context size
   ```

3. **Deployment Fails**

   ```bash
   # Check SSH connection
   # Verify server permissions
   # Check environment variables
   # Validate Docker Compose configuration
   ```

4. **Application Won't Start**
   ```bash
   # Check container logs: docker-compose logs
   # Verify database connectivity
   # Check environment variables
   # Validate health check endpoints
   ```

### Debug Commands

```bash
# Test local Docker setup
make docker-build
make docker-test

# Check deployment status
docker-compose -f docker-compose.staging.yml ps
docker-compose -f docker-compose.prod.yml logs web

# Health check
./scripts/health-check.sh

# Backup verification
./scripts/backup.sh
```

## 📚 Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Celery Documentation](https://docs.celeryproject.org/)

## 🎯 Success Metrics

- **CI Pipeline**: All tests pass in < 15 minutes
- **Build Pipeline**: Docker images build in < 10 minutes
- **Deployment**: Zero-downtime deployments in < 5 minutes
- **Uptime**: 99.9% application availability
- **Recovery**: < 15 minutes from failure to recovery

## 📞 Support

For issues with this CI/CD implementation:

1. Check the troubleshooting section above
2. Review GitHub Actions logs for detailed error messages
3. Validate server configuration and permissions
4. Test locally before deploying to production

---

_This quick start guide gets your SmartHR360 Future Skills platform from development to production with a robust, scalable CI/CD pipeline in under 2 hours._

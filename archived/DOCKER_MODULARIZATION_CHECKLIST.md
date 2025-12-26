# Docker & DevOps Modularization Roadmap

This document provides a detailed, actionable checklist and guidance for optimizing and modularizing the Docker and DevOps setup for the SmartHR360 project. Follow each step to ensure maintainability, efficiency, and best practices.

---

## 1. Shared Base Image for All Services & Dockerfile Verification

- [x] Review and update **all Dockerfiles** (`Dockerfile.base`, `Dockerfile.web`, `Dockerfile.celery`, `Dockerfile.nginx`, legacy Dockerfiles, etc.) to ensure:
  - [x] Only `Dockerfile.base` installs system dependencies and requirements. _(Verified)_
  - [x] All service Dockerfiles use `FROM smarthr360-base:latest` (except Nginx) and do NOT re-install requirements. _(Verified: web/celery use base, nginx uses nginx base)_
  - [x] No redundant `pip install` or system package installs in service Dockerfiles. _(Verified: no redundant installs in main Dockerfiles)_
  - [x] Legacy or unused Dockerfiles are identified, documented, and removed or renamed as needed. _(Legacy: `Dockerfile.simple`, `Dockerfile`—archived in `archived/`)_
  - [x] All Dockerfiles are modular, minimal, and follow best practices. _(Verified)_

**Note:**

- Legacy Dockerfiles have been renamed for clarity:
  - `Dockerfile.simple` → `Dockerfile.legacy.simple`
  - `Dockerfile` → `Dockerfile.legacy`
    All other Dockerfiles are modular and up to date.

## 2. Centralize Static Assets and Artifacts

- [x] Define Docker volumes in `docker-compose.yml` for shared assets (e.g., ML models, static files, logs).
  - `static_volume`: static files
  - `media_volume`: media uploads
  - `ml_models_volume`: ML models (e.g., future_skills_model.pkl)
  - `logs_volume`: logs (now in both docker-compose.yml and docker-compose.prod.yml)
  - `postgres_data`, `redis_data`: database and cache persistence
- [x] Mount these volumes in all relevant services (e.g., web, celery) at the same path (e.g., `/app/artifacts/models`).
  - `ml_models_volume` is now mounted in both `web` and `celery_worker` at `/app/artifacts/models` for consistent ML model access.
  - `logs_volume` is mounted in both for log persistence.
  - `static_volume` and `media_volume` are mounted in `web`.
- [x] Remove COPY of shared assets from Dockerfiles if using volumes.
  - ML model is now provided via Docker volume only; Dockerfiles only copy runtime code and trained models from builder stages.

## 3. Multi-Stage Builds

- Static file collection (Django collectstatic)
- ML model training (scripts/ml_train.sh)
- Requirements installation (in Dockerfile.base)
- Asset preparation (dataset preparation, migrations if needed)
- Stage 1: Build assets, train models, collect static files.
- Stage 2: Copy only the needed results to the final image.

## Multi-Stage Build Strategy Plan

This section outlines the multi-stage build approach for all main Dockerfiles. Each service will use a multi-stage Dockerfile to separate build-time tasks from the final runtime image, resulting in smaller, more secure, and maintainable images.

### 1. web (Django/Gunicorn)

**Build-time tasks:**

- Install build dependencies (node, npm/yarn, Python build tools)
- Build frontend assets (if any, e.g., npm run build)
- Collect static files (python manage.py collectstatic)

**Stages:**

- **builder:** Installs all build dependencies, runs asset build and collectstatic, produces static assets in /app/staticfiles
- **final:** Starts from a minimal Python image, copies only app code and /app/staticfiles from builder

### 2. celery (Celery Worker)

**Build-time tasks:**

- Install build dependencies (Python build tools, ML libraries)
- (Optional) Run ML model training or pre-compilation if needed

**Stages:**

- **builder:** Installs all build dependencies, runs any model training or pre-compilation, produces trained models/artifacts in /app/ml/models
- **final:** Starts from a minimal Python image, copies only app code and /app/ml/models from builder

### 3. ML Service (if separate)

**Build-time tasks:**

- Install build dependencies (ML libraries, data tools)
- Train ML models, export artifacts

**Stages:**

- **builder:** Installs all build dependencies, runs model training, produces model artifacts in /app/ml/models
- **final:** Starts from a minimal Python image, copies only serving code and /app/ml/models from builder

### 4. nginx

**Build-time tasks:**

- (Optional) Build static assets or generate configs

**Stages:**

- **builder:** (If needed) Builds static assets or generates configs
- **final:** Starts from nginx:alpine, copies only nginx.conf and static assets from builder

---

For each Dockerfile, the final image will only contain what is needed for runtime. All build dependencies and intermediate files will be left behind in the builder stage.

Next steps: Refactor each Dockerfile as per this plan, document produced files per stage, and validate the builds.

For detailed documentation of files/artifacts produced in each build stage, see:
**[DOCKER_PRODUCED_FILES_PER_STAGE.md](DOCKER_PRODUCED_FILES_PER_STAGE.md)**

## 4. Centralize Environment Configuration

- [x] Use a single `.env.docker` file at the project root for all non-sensitive environment variables shared by all services (web, celery, ML, etc.). Referenced in `docker-compose.yml` using `env_file` for each service. _(Complete)_
- [x] For sensitive data (secrets, passwords, API keys), use Docker secrets or a separate `secrets.env` file (not committed). Template provided as `secrets.example`. _(Complete)_
- [x] Document all required environment variables and secrets in template files (`.env.docker.example` and `secrets.example`) for onboarding. _(Complete)_

## 5. Service-Specific Entrypoints

- [x] Store all entrypoint scripts in a shared directory: [`scripts/entrypoints/`](scripts/entrypoints/). _(Complete)_
- [x] Each Dockerfile copies only the relevant entrypoint script for its service. _(Complete)_
- [x] Document the purpose and usage of each entrypoint script in [`scripts/entrypoints/README.md`](scripts/entrypoints/README.md). _(Complete)_

Note: The base image (`Dockerfile.base`) does not require an entrypoint, as it is not intended to be run directly.

## 6. Network and Service Discovery

- [x] Ensure all services are on the same Docker Compose network (`smarthr360-network`). _(Complete)_
- [x] Use service names for inter-service communication (e.g., `db`, `redis`, `web`, `celery_worker`, `celery_beat`, `nginx`). _(Complete)_
- [x] Document network topology and service discovery in the [README](README.md#docker-compose-network-topology--service-discovery). _(Complete)_

## 7. Centralized Testing and Linting

- [x] Remove test/lint steps from service Dockerfiles unless needed for runtime. _(All runtime images now exclude test/lint artifacts; see Dockerfile.web, Dockerfile.celery, etc.)_
- [x] Document how to run tests and linting locally and in CI. _(See [README.md](README.md#local-testing--linting) and [tests/README.md](tests/README.md) for full instructions.)_
- [ ] Create a dedicated CI/CD pipeline stage or container for running tests, linting, and security checks. _(Planned: see [README.md](README.md#cicd-test--lint-container-planned); current pipeline in `.github/workflows/ci.yml`)_

## 8. Layer Caching

- [x] Order Dockerfile steps so that code is copied last, after dependencies are installed. _(All main Dockerfiles follow this pattern for optimal caching.)_
- [x] Document Docker build best practices for contributors. _(See [README.md](README.md#docker-build-best-practices) for guidelines.)_

## 9. Documentation, Automation & Script Verification

- [x] Review, verify, and update **all shell scripts** in the `scripts/` directory (`*.sh`) to ensure:
  - [x] Scripts are modular, reusable, and do not duplicate logic handled in Dockerfiles or Makefiles.
  - [x] No redundant installation or configuration steps.
  - [x] Scripts are clearly named, documented, and have a single responsibility.
  - [x] All scripts follow best practices for error handling, logging, and portability.
  - [x] All major scripts are documented in `scripts/README.md` with usage examples and workflow integration.
  - [ ] Periodically review for legacy or unused scripts and refactor/remove as needed. _(No legacy/unused scripts found as of last review; continue periodic checks.)_

**Scripts reviewed:**

- setup_dev.sh
- run_tests.sh
- docker_build.sh
- docker-setup.sh
- ml_train.sh
- quick_setup.sh
- setup_mlflow.sh
- setup_celery_monitoring.sh
- blue-green-deploy.sh
- canary-deploy.sh
- deploy-argocd-apps.sh
- install-argocd.sh
- prepare_deployment.sh
- security_scan.sh
- verify-pipeline.sh
- generate-secrets.sh
- rollback.sh

- [x] Maintain up-to-date markdown documentation for all DevOps processes, including script usage and responsibilities (see `scripts/README.md`).
- [x] Add a section in the README for Docker/DevOps workflow and script usage.

## 10. Use a Package Index or Artifact Registry (Optional, for large projects)

- _(Planned for future implementation; revisit when internal package distribution is required.)_

- [ ] If needed, build Python wheels or packages and upload to a private PyPI or artifact registry.
- [ ] Update Dockerfiles to install from the registry.
- [ ] Document the process for building and publishing packages.

---

## Safety and Update Checklist

- [ ] Before making changes, back up current Dockerfiles, requirements, and compose files.
- [ ] Make changes incrementally and test each step (build, run, connect services).
- [ ] Use version control branches for all updates.
- [ ] Review and test all changes in a staging environment before production.

---

## Current State Analysis (to be filled in)

- [ ] List current Dockerfiles and their base images.
- [ ] List all requirements files and which services use them.
- [ ] List all shared assets and how they are distributed.
- [ ] List all environment variables and how they are managed.
- [ ] List all entrypoint scripts and their usage.
- [ ] List current CI/CD steps for testing and deployment.

---

## References

- [Docker Official Documentation](https://docs.docker.com/)
- [Docker Compose Best Practices](https://docs.docker.com/compose/best-practices/)
- [12 Factor App Methodology](https://12factor.net/)

---

**Follow this checklist and update this file as you progress. This will ensure a safe, maintainable, and efficient Docker/DevOps setup for your project.**

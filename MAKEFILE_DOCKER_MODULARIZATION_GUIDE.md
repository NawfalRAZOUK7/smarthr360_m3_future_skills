# Makefile & Docker Modularization Integration Guide

This guide explains how to update and organize your Makefiles to align with the new modular Docker build strategy for SmartHR360. Follow these steps to ensure a robust, maintainable, and reproducible workflow for all developers and CI/CD.

---

## 1. Why Update the Makefiles?

- The new Docker setup uses a shared base image (`smarthr360-base:latest`) for all services, built from `Dockerfile.base`.
- All service Dockerfiles (web, celery, nginx, etc.) depend on this base image.
- The base image **must** be built before any other Docker image builds.
- Makefiles should enforce this order and make it easy to rebuild only what is needed.

---

## 2. Required Makefile Targets

### 2.1. Base Image Build

Add this target to your main `Makefile`:

```makefile
docker-base:
	docker build -t smarthr360-base:latest -f Dockerfile.base .
```

### 2.2. Main Docker Build (All Services)

Update your `docker-build` target to depend on `docker-base`:

```makefile
docker-build: docker-base
	docker compose build
```

This ensures the base image is always up-to-date before building service images.

### 2.3. Service-Specific Builds (Optional)

If you want to build only a specific service (e.g., web):

```makefile
docker-web: docker-base
	docker compose build web
```

Repeat for other services as needed.

---

## 3. Recommended Build & Run Order

1. **Build the base image:**
   ```sh
   make docker-base
   ```
2. **Build all service images:**
   ```sh
   make docker-build
   ```
3. **Start the environment:**
   ```sh
   make docker-up
   ```
4. **Stop the environment:**
   ```sh
   make docker-down
   ```

---

## 4. CI/CD Integration

- In your CI pipeline, always run `make docker-base` before `make docker-build`.
- This guarantees that the latest base image is used for all builds.
- Example CI steps:
  ```yaml
  - run: make docker-base
  - run: make docker-build
  - run: make docker-up
  - run: make test
  ```

---

## 5. Troubleshooting & Best Practices

- If you change `Dockerfile.base`, always rebuild the base image (`make docker-base`) before rebuilding services.
- If you change only a service Dockerfile, you can run `make docker-build` (it will skip rebuilding the base if unchanged).
- Document this workflow in your project README and onboarding docs.
- Use `make docker-clean` to remove all containers, images, and volumes if you need a fresh start.

---

## 6. Example Makefile Snippet

```makefile
# Build base image
.PHONY: docker-base
docker-base:
	docker build -t smarthr360-base:latest -f Dockerfile.base .

# Build all images (depends on base)
.PHONY: docker-build
docker-build: docker-base
	docker compose build

# Start/stop
.PHONY: docker-up docker-down
docker-up:
	docker compose up -d
docker-down:
	docker compose down
```

---

## 7. Summary Checklist

- [ ] Add `docker-base` target to all Makefiles that build Docker images.
- [ ] Make all service build targets depend on `docker-base`.
- [ ] Update documentation and onboarding to reflect the new build order.
- [ ] Use this order in CI/CD and local development.

---

---

## 8. Makefile Structure and Roles

### Main Makefile

- **Purpose:** Centralizes all Docker build logic and orchestrates the build order for the entire project.
- **Responsibilities:**
  - Defines `docker-base` to build the shared base image.
  - Ensures all service builds depend on `docker-base`.
  - Provides targets for building, starting, stopping, and cleaning all Docker services.
  - Should be the only Makefile updated for Docker build order and base image logic.

### Service-Specific Makefiles (e.g., Makefile.celery, Makefile.security, Makefile.logging)

- **Purpose:** Contain commands and automation specific to their service domain (e.g., Celery, security, logging).
- **Responsibilities:**
  - Should NOT contain Docker build logic or base image dependencies.
  - May include service-specific test, lint, or utility commands.
  - Remain focused and minimal to avoid duplication and confusion.

### Workflow Summary

1. **Developers and CI/CD should use the main Makefile for all Docker build and orchestration tasks.**
2. **Service-specific Makefiles are only for advanced, service-specific automation—not for Docker builds.**
3. **Document this structure in onboarding and team docs to ensure clarity and maintainability.**

---

For further details, see your modularization checklist and Dockerfile documentation.

# SmartHR360: Clean Onboarding & Build Order

This guide provides the safest, most logical order to run all scripts and commands for a clean, reproducible onboarding and build process.

---

## 🟢 1. Prerequisites

- Ensure Docker and Docker Compose are installed and running.
- (Optional) Clean your Docker environment:
  ```bash
  docker system prune -af --volumes
  docker volume ls  # Remove project volumes if needed
  ```

---

## 🟦 2. Docker & Onboarding Preparation

Run the main onboarding/setup script:

```bash
bash scripts/docker-setup.sh
```

- Ensures Docker is ready
- Runs onboarding scripts (ML, MLflow, Celery monitoring)
- Trains or retrains ML models
- Builds base Docker images

---

## 🟨 3. Build & Start Environment

Start the development or production environment:

```bash
./scripts/docker_build.sh dev    # For development
./scripts/docker_build.sh prod   # For production
```

---

## 🟧 4. Database Migrations

Run database migrations inside the container:

```bash
./scripts/docker_build.sh migrate
```

---

## 🟪 5. Testing

Run tests inside the container:

```bash
./scripts/docker_build.sh test
```

---

## 🟫 6. Logs, Shell, and Status

- View logs:
  ```bash
  ./scripts/docker_build.sh logs web
  ```
- Check status:
  ```bash
  ./scripts/docker_build.sh status
  ```
- Open a shell in the web container:
  ```bash
  ./scripts/docker_build.sh shell
  ```

---

## 🔄 7. Clean Up (Optional)

To stop and remove all containers, images, and volumes:

```bash
./scripts/docker_build.sh clean
```

---

## Notes

- You do NOT need to run ml_train.sh, setup_mlflow.sh, or setup_celery_monitoring.sh manually—these are handled by docker-setup.sh.
- Always run docker-setup.sh after a full clean or on a new machine.
- For advanced ML workflows, see ml_train.sh usage in the main README.

---

This order ensures a robust, repeatable onboarding and build process for all developers and CI/CD environments.

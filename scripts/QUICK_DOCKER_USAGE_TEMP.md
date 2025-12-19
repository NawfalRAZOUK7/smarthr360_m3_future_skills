# Quick Docker Script Usage Guide

This guide explains how to use `scripts/quick_docker.sh` for onboarding, building, and managing your local Docker environment for both development and production.

## ⚠️ Recommended Order: Dev First, Then Prod

**Always run all onboarding, build, and test steps in the dev environment first.**

- The dev environment is safe for catching errors and validating changes.
- Once everything works in dev, repeat the same steps in prod.
- This minimizes risk and ensures a smooth production rollout.

**Summary:**

1. Complete all steps in dev mode.
2. If successful, repeat in prod mode.

---

## 1. Make the Script Executable (one-time)

```sh
chmod +x scripts/quick_docker.sh
```

---

## 2. Run the Script (Interactive Mode)

```sh
./scripts/quick_docker.sh
```

**How to use the interactive menu:**

1. Select `dev` mode (type `1` and press Enter)
2. Select steps one by one by typing their number (e.g., `1` for onboard, `2` for build, etc.)
3. When finished, select `done` (type the number shown for 'done', usually `11`) to start execution.

- Do **not** type `done` as text; always use the number.

4. Repeat the same process for `prod` mode (type `2` at the mode prompt).

**Recommended order for testing (dev first, then prod):**

1. onboard (1)
2. build (2)
3. migrate (3)
4. test (4)
5. up (8)

You can also run steps one by one, or select `all` (type `10`) to run all main steps in order.

---

---

## 2a. Step-by-Step Checklist (Mark as You Go)

Use this checklist to track your progress for both dev and prod environments. Mark each step as you complete it.

### Dev Environment

- [ ] onboard (dev) _(setup only; services like Redis are **not running** yet)_
- [ ] build (dev)
- [ ] migrate (dev)
- [ ] test (dev)
- [ ] up (dev) _(starts all containers, including Redis)_

### Prod Environment (after dev is successful)

- [ ] onboard (prod) _(setup only; services like Redis are **not running** yet)_
- [ ] build (prod)
- [ ] migrate (prod)
- [ ] test (prod)
- [ ] up (prod) _(starts all containers, including Redis)_

---

---

## 3. Run the Script (Command-Line Arguments)

You can skip the menu and run specific steps directly. Here are recommended commands for each major operation in both dev and prod:

### Onboarding (setup)

- **Dev:**
  ```sh
  ./scripts/quick_docker.sh --dev --onboard
  ```
- **Prod:**
  ```sh
  ./scripts/quick_docker.sh --prod --onboard
  ```

### Build Images

- **Dev:**
  ```sh
  ./scripts/quick_docker.sh --dev --build
  ```
- **Prod:**
  ```sh
  ./scripts/quick_docker.sh --prod --build
  ```

### Database Migrations

- **Dev:**
  ```sh
  ./scripts/quick_docker.sh --dev --migrate
  ```
- **Prod:**
  ```sh
  ./scripts/quick_docker.sh --prod --migrate
  ```

### Run Tests

- **Dev:**
  ```sh
  ./scripts/quick_docker.sh --dev --test
  ```
- **Prod:**
  ```sh
  ./scripts/quick_docker.sh --prod --test
  ```

### Start Containers

- **Dev:**
  ```sh
  ./scripts/quick_docker.sh --dev --up
  ```
- **Prod:**
  ```sh
  ./scripts/quick_docker.sh --prod --up
  ```

### Show Logs

- **Dev:**
  ```sh
  ./scripts/quick_docker.sh --dev --logs
  ```
- **Prod:**
  ```sh
  ./scripts/quick_docker.sh --prod --logs
  ```

### Open Shell in Web Container

- **Dev:**
  ```sh
  ./scripts/quick_docker.sh --dev --shell
  ```
- **Prod:**
  ```sh
  ./scripts/quick_docker.sh --prod --shell
  ```

### Clean Everything

- **Dev:**
  ```sh
  ./scripts/quick_docker.sh --dev --clean
  ```
- **Prod:**
  ```sh
  ./scripts/quick_docker.sh --prod --clean
  ```

### Run All Main Steps

- **Dev:**
  ```sh
  ./scripts/quick_docker.sh --dev --all
  ```
- **Prod:**
  ```sh
  ./scripts/quick_docker.sh --prod --all
  ```

---

## 4. Recommended Testing Workflows

### Test Dev Environment

1. Onboard/setup:
   ```sh
   ./scripts/quick_docker.sh --dev --onboard
   ```
2. Build images:
   ```sh
   ./scripts/quick_docker.sh --dev --build
   ```
3. Run migrations:
   ```sh
   ./scripts/quick_docker.sh --dev --migrate
   ```
4. Run tests:
   ```sh
   ./scripts/quick_docker.sh --dev --test
   ```
5. Start containers:
   ```sh
   ./scripts/quick_docker.sh --dev --up
   ```

### Test Prod Environment

1. Onboard/setup:
   ```sh
   ./scripts/quick_docker.sh --prod --onboard
   ```
2. Build images:
   ```sh
   ./scripts/quick_docker.sh --prod --build
   ```
3. Run migrations:
   ```sh
   ./scripts/quick_docker.sh --prod --migrate
   ```
4. Run tests:
   ```sh
   ./scripts/quick_docker.sh --prod --test
   ```
5. Start containers:
   ```sh
   ./scripts/quick_docker.sh --prod --up
   ```

---

### 1. Test Dev Environment (Always First)

Run these steps in order:

```sh
./scripts/quick_docker.sh --dev --onboard
./scripts/quick_docker.sh --dev --build
./scripts/quick_docker.sh --dev --migrate
./scripts/quick_docker.sh --dev --test
./scripts/quick_docker.sh --dev --up
```

### 2. Test Prod Environment (After Dev Succeeds)

Repeat the same steps for prod:

```sh
./scripts/quick_docker.sh --prod --onboard
./scripts/quick_docker.sh --prod --build
./scripts/quick_docker.sh --prod --migrate
./scripts/quick_docker.sh --prod --test
./scripts/quick_docker.sh --prod --up
```

---

---

---

## 4. Step Descriptions

- **onboard:** Runs onboarding/setup (docker-setup.sh). _This only prepares dependencies and environment files. **No containers or services (like Redis) are started yet!**_
- **build:** Builds Docker images (docker_build.sh --build)
- **migrate:** Runs DB migrations (docker_build.sh --migrate)
- **test:** Runs tests (docker_build.sh --test)
- **logs:** Shows logs for all containers
- **shell:** Opens a shell in the web container
- **clean:** Stops/removes containers, images, and volumes
- **up:** Starts containers in the background (including Redis, Postgres, web, etc.)
- **down:** Stops containers
- **all:** Runs onboard, build, migrate, test, up (in order)

---

## 5. Troubleshooting

- If you see `Invalid option` in the menu, type the number (not the label).
- If a step fails, check the output for errors.
- You can always quit the menu with `Ctrl+C`.
- **Script permissions:** The script now automatically ensures all required .sh files are executable, so you should not see permission errors.
- **Redis or other services not running after onboarding?** This is expected! _You must run the `up` step to start all containers and services. Onboarding only prepares the environment._

---

For more details, see the script comments or ask for help!

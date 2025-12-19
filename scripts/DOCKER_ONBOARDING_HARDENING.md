# Docker Onboarding Script Hardening Checklist

This document provides a comprehensive, actionable checklist for making `docker-setup.sh` and all onboarding scripts robust, maintainable, and CI/CD-friendly. It covers error handling, script permissions, and logging, with exact steps, code patterns, and verification points.

---

## ✅ 1. Error Handling for Onboarding Scripts

**Goal:** If any onboarding script fails, the process stops and the error is clear.

### Step-by-Step Checklist

1. **After every onboarding script call, check the exit status (`$?`).**
   - This ensures you catch any failure immediately after the script runs.
2. **If non-zero, print a clear, color-coded error message specifying which script failed.**
   - Use red color for errors for visibility.
3. **Exit with a non-zero code immediately.**
   - Prevents the rest of the setup from running if a critical step fails.
4. **Optionally, tail the log file for the last 20 lines on error.**
   - This helps quickly diagnose what went wrong in CI/CD or local runs.
5. **Use consistent echo patterns for both success and failure.**
   - Green for success, red for failure, yellow for warnings.

### Example Implementation

```bash
LOG_FILE="docker-setup.log"
SCRIPT_PATH="scripts/setup_mlflow.sh"

# Run script and log output
bash "$SCRIPT_PATH" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
  echo -e "\033[0;31m✗ $SCRIPT_PATH failed. See $LOG_FILE for details.\033[0m"
  tail -20 "$LOG_FILE"
  exit 1
fi
# Success echo
echo -e "\033[0;32m✓ $SCRIPT_PATH completed successfully.\033[0m"
```

### Verification Steps

- [ ] Intentionally break an onboarding script (e.g., add `exit 1` to setup_mlflow.sh) and run docker-setup.sh. Confirm that:
  - The error is caught and printed in red.
  - The script exits immediately after the failure.
  - The last 20 lines of the log are shown for diagnosis.
- [ ] Restore the script and confirm that a successful run prints a green success message and continues.

### Notes

- Repeat this pattern for every onboarding script (setup_celery_monitoring.sh, setup_mlflow.sh, ml_train.sh, etc).
- Always check the exit status immediately after the script call.
- Use the same color and echo conventions throughout for consistency.

---

## ✅ 2. Ensure All .sh Scripts Are Executable

**Goal:** Prevent 'permission denied' errors by ensuring all called scripts are executable before running them.

### Step-by-Step Checklist

1. **Before calling any `.sh` script, check if it is executable with `[ -x ... ]`.**
   - This prevents runtime errors due to missing execute permissions.
2. **If not executable, attempt `chmod +x` to set the permission.**
   - This fixes the issue automatically in most environments.
3. **If `chmod +x` fails, print a yellow warning message.**
   - This alerts the user to a potential permission or filesystem problem.
4. **Always check and fix permissions before every onboarding script call.**
   - Do not assume scripts are executable by default.
5. **Document which scripts are checked and fixed.**
   - This helps with future maintenance and onboarding.

### Example Implementation

```bash
SCRIPT_PATH="scripts/setup_mlflow.sh"
if [ ! -x "$SCRIPT_PATH" ]; then
  chmod +x "$SCRIPT_PATH" || echo -e "\033[1;33m⚠ Could not set executable permission for $SCRIPT_PATH\033[0m"
fi
```

#### For multiple scripts:

```bash
for SCRIPT_PATH in scripts/setup_celery_monitoring.sh scripts/setup_mlflow.sh scripts/ml_train.sh; do
  if [ ! -x "$SCRIPT_PATH" ]; then
    chmod +x "$SCRIPT_PATH" || echo -e "\033[1;33m⚠ Could not set executable permission for $SCRIPT_PATH\033[0m"
  fi
done
```

### Verification Steps

- [ ] Remove execute permission from a script (e.g., `chmod -x scripts/setup_mlflow.sh`) and run docker-setup.sh. Confirm that:
  - The script is made executable automatically.
  - No 'permission denied' error occurs.
- [ ] Simulate a read-only filesystem or permission error and confirm that a yellow warning is printed if `chmod +x` fails.
- [ ] All onboarding scripts are checked and fixed before execution.

### Notes

- This pattern should be applied to every onboarding script and any other .sh script called from docker-setup.sh.
- Always check permissions before running, not after.
- Use yellow for warnings, green for success, red for errors.

---

## ✅ 3. Log Onboarding Output for CI/CD Troubleshooting

**Goal:** Make troubleshooting easier by logging all onboarding output.

### Step-by-Step Checklist

1. **Define a log file at the top of docker-setup.sh (e.g., `LOG_FILE="docker-setup.log"`).**
   - This centralizes all onboarding output for review.
2. **Redirect both stdout and stderr of each onboarding script to the log file.**
   - Use `>> "$LOG_FILE" 2>&1` for every script call.
3. **Print the log file location at the start and end of the script.**
   - This helps users and CI/CD systems find logs quickly.
4. **On error, tail the log for the last 20 lines for quick diagnosis.**
   - This provides immediate context for failures.
5. **Use clear, color-coded echo statements before and after each major step, referencing the log file.**
   - Blue/info for step start, green for success, red for error.
6. **Optionally, add timestamps to log entries for better traceability.**
   - Use `date` or `ts` if available.

### Example Implementation

```bash
LOG_FILE="docker-setup.log"
echo "=========================================="
echo "SmartHR360 Docker Setup (logging to $LOG_FILE)"
echo "=========================================="

SCRIPT_PATH="scripts/setup_mlflow.sh"
echo -e "\033[0;34m[INFO] Running $SCRIPT_PATH (logging to $LOG_FILE)\033[0m"
bash "$SCRIPT_PATH" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
  echo -e "\033[0;31m✗ $SCRIPT_PATH failed. See $LOG_FILE for details.\033[0m"
  tail -20 "$LOG_FILE"
  exit 1
fi
echo -e "\033[0;32m✓ $SCRIPT_PATH completed successfully.\033[0m"
```

#### For multiple scripts:

```bash
for SCRIPT_PATH in scripts/setup_celery_monitoring.sh scripts/setup_mlflow.sh scripts/ml_train.sh; do
  echo -e "\033[0;34m[INFO] Running $SCRIPT_PATH (logging to $LOG_FILE)\033[0m"
  bash "$SCRIPT_PATH" >> "$LOG_FILE" 2>&1
  if [ $? -ne 0 ]; then
    echo -e "\033[0;31m✗ $SCRIPT_PATH failed. See $LOG_FILE for details.\033[0m"
    tail -20 "$LOG_FILE"
    exit 1
  fi
  echo -e "\033[0;32m✓ $SCRIPT_PATH completed successfully.\033[0m"
done
```

### Verification Steps

- [ ] Run docker-setup.sh and confirm that all onboarding output is written to docker-setup.log.
- [ ] On error, confirm that the last 20 lines of the log are printed to the console.
- [ ] At the end of a successful run, confirm that the log file location is printed for reference.
- [ ] Review the log file for completeness, clarity, and timestamped entries if enabled.

### Notes

- Always use the same log file for all onboarding steps to centralize troubleshooting.
- Use color-coded echoes for all major steps and log references.
- Optionally, add timestamps to each log entry for better traceability in CI/CD environments (e.g., `bash "$SCRIPT_PATH" 2>&1 | ts >> "$LOG_FILE"`).

---

## ✅ 4. Recommended Order of Commands and Echoes

**Goal:** Ensure a clear, logical, and user-friendly flow for onboarding, with consistent and informative output at every step.

### Step-by-Step Checklist

1. **Print a start banner and log file location at the top.**
   - Use clear separators and info echoes to indicate the beginning of the setup and where logs will be written.
2. **For each onboarding script (e.g., setup_celery_monitoring.sh, setup_mlflow.sh, ml_train.sh):**
   - [ ] Check if executable, fix if needed (see section 2).
   - [ ] Print a blue/info echo before running the script, stating which script is about to run and where output will be logged.
   - [ ] Run the script, redirecting output to the log file (see section 3).
   - [ ] Check exit status, print a green success echo or red error echo as appropriate (see section 1).
   - [ ] On error, tail the log and exit immediately.
3. **Continue with Docker build, up, and other steps as normal, logging output as needed.**
   - Use info echoes before each major Docker step (build, up, migrations, collectstatic, etc.).
   - Print success or error echoes after each step.
4. **At the end, print a summary and the log file location.**
   - Use a green banner for success, red for failure, and always reference the log file for troubleshooting.

### Example Implementation

```bash
LOG_FILE="docker-setup.log"
echo "=========================================="
echo "SmartHR360 Docker Setup (logging to $LOG_FILE)"
echo "=========================================="

for SCRIPT_PATH in scripts/setup_celery_monitoring.sh scripts/setup_mlflow.sh scripts/ml_train.sh; do
  if [ ! -x "$SCRIPT_PATH" ]; then
    chmod +x "$SCRIPT_PATH" || echo -e "\033[1;33m⚠ Could not set executable permission for $SCRIPT_PATH\033[0m"
  fi
  echo -e "\033[0;34m[INFO] Running $SCRIPT_PATH (logging to $LOG_FILE)\033[0m"
  bash "$SCRIPT_PATH" >> "$LOG_FILE" 2>&1
  if [ $? -ne 0 ]; then
    echo -e "\033[0;31m✗ $SCRIPT_PATH failed. See $LOG_FILE for details.\033[0m"
    tail -20 "$LOG_FILE"
    exit 1
  fi
  echo -e "\033[0;32m✓ $SCRIPT_PATH completed successfully.\033[0m"
done

echo -e "\033[0;34m[INFO] Building Docker images...\033[0m"
docker build -f Dockerfile.base -t smarthr360-base:latest . >> "$LOG_FILE" 2>&1
# ...repeat pattern for other Docker steps...

echo "=========================================="
echo -e "\033[0;32m✅ Setup complete!\033[0m"
echo "=========================================="
echo "All logs are available at: $LOG_FILE"
```

### Verification Steps

- [ ] Run docker-setup.sh and confirm that:
  - The start banner and log file location are printed at the top.
  - Each onboarding script prints an info echo before running, and a green success or red error echo after.
  - On error, the log is tailed and the script exits immediately.
  - All major Docker steps are echoed and logged.
  - The summary and log file location are printed at the end.
- [ ] Review the log file and console output for clarity and completeness.

### Notes

- Always use color-coded echoes for info (blue), success (green), warning (yellow), and error (red).
- Maintain the same order and echo pattern for all onboarding and Docker steps for consistency and user experience.

---

## ✅ 5. Verification & Maintenance

**Goal:** Ensure the onboarding hardening patterns are effective, reliable, and kept up to date as scripts evolve.

### Step-by-Step Verification Checklist

1. **Test docker-setup.sh in a clean environment:**
   - Remove or rename .env, secrets.env, and artifacts directories.
   - Run docker-setup.sh and confirm all onboarding steps, permission checks, and logging work as expected.
2. **Intentionally break an onboarding script:**
   - Add `exit 1` or a known error to a script (e.g., setup_mlflow.sh).
   - Run docker-setup.sh and confirm:
     - The error is caught and printed in red.
     - The script exits immediately after the failure.
     - The last 20 lines of the log are shown for diagnosis.
3. **Test script permissions:**
   - Remove execute permission from a script (e.g., `chmod -x scripts/setup_mlflow.sh`).
   - Run docker-setup.sh and confirm:
     - The script is made executable automatically.
     - No 'permission denied' error occurs.
     - A warning is printed if chmod fails.
4. **Review log file after a run:**
   - Confirm all onboarding output is present, clear, and (optionally) timestamped.
   - On error, confirm the log is tailed in the console.
5. **Check summary and log location at the end:**
   - Ensure the script prints a clear summary and the log file location at the end of every run.
6. **Document and update onboarding scripts:**
   - When adding new onboarding scripts, update docker-setup.sh and this checklist.
   - Ensure new scripts follow all hardening patterns (permission, error handling, logging, echoes).

### Maintenance Best Practices
- [ ] Regularly review onboarding scripts for changes or new requirements.
- [ ] Update this checklist and docker-setup.sh whenever onboarding logic changes.
- [ ] Encourage contributors to follow these patterns for any new scripts.
- [ ] Periodically test onboarding in a clean environment and with simulated failures.
- [ ] Keep log file size manageable (rotate or truncate if needed in CI/CD).

### Example Maintenance Log
- [ ] [2025-12-17] Verified onboarding hardening after major script refactor.
- [ ] [2025-12-17] Added new onboarding script: scripts/setup_data_science.sh (pattern applied).

### Notes
- Verification and maintenance are ongoing processes—review and test regularly.
- Keep this checklist in version control and reference it in onboarding documentation.

---

## 📝 Summary Table

| Step               | What to Check/Do                                  | Example/Pattern |
| ------------------ | ------------------------------------------------- | --------------- |
| Error handling     | Exit on failure, print error, tail log            | See section 1   |
| Script permissions | Check +x, fix if needed, warn if can't set        | See section 2   |
| Logging            | Log all output, print log location, tail on error | See section 3   |
| Order & echoes     | Banner, info, run, check, success/error, summary  | See section 4   |
| Verification       | Test, break, review log, update docs              | See section 5   |

---

**Adopt these patterns and checklists in `docker-setup.sh` and all onboarding scripts for a robust, maintainable, and CI/CD-friendly workflow.**

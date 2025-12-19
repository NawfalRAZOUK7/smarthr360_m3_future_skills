# DOCKER_BUILD_HARDENING.md

## Docker Build & Deploy Script Hardening Checklist

This checklist ensures that `docker_build.sh` is robust, maintainable, and CI/CD-friendly, following the same best practices as `docker-setup.sh`.

---

## 1. Error Handling & Logging

- [x] Define a `LOG_FILE` at the top (e.g., `docker-build.log`).
- [x] Print the log file location at the start and end of the script.
- [x] Redirect stdout and stderr of all critical steps (ML training, Docker build, up, etc.) to the log file using `>> "$LOG_FILE" 2>&1`.
- [x] On error, print a red error message, tail the last 20 lines of the log, and exit immediately.
- [x] Use color-coded echoes for info (blue), success (green), warning (yellow), and error (red).

## 2. Executable Checks for Scripts

- [x] Before calling any `.sh` script (e.g., `ml_train.sh`), check if it is executable with `[ -x ... ]`.
- [x] If not, attempt `chmod +x` and print a yellow warning if it fails.
- [x] Document which scripts are checked and fixed.

## 3. Docker Compose Command Compatibility

- [x] Detect if `docker compose` (space) is available and prefer it over `docker-compose` (hyphen) for future compatibility.
- [x] Fallback to `docker-compose` if `docker compose` is not available.
- [x] Use the selected compose command consistently throughout the script.

## 4. Consistent Order & Echo Patterns

- [x] Print a start banner and log file location at the top.
- [x] For each onboarding or build step:
  - [x] Check script executability.
  - [x] Print a blue info echo before running.
  - [x] Run the step, logging output.
  - [x] Check exit status, print green success or red error echo.
  - [x] On error, tail the log and exit.
- [x] Continue with Docker build, up, and other steps, logging output and using info/success/error echoes.
- [x] Print a summary and log file location at the end.

## 5. Verification & Maintenance

- [x] Test the script by intentionally breaking a step and confirming error handling and log tailing.
- [x] Review the log file for completeness and clarity.
- [x] Periodically review and update the script to match onboarding and CI/CD best practices.

---

## Example Implementation Snippet

```bash
LOG_FILE="docker-build.log"
echo "=========================================="
echo -e "\033[0;34mSmartHR360 Docker Build (logging to $LOG_FILE)\033[0m"
echo "=========================================="

SCRIPT_PATH="scripts/ml_train.sh"
if [ ! -x "$SCRIPT_PATH" ]; then
  chmod +x "$SCRIPT_PATH" || echo -e "\033[1;33m⚠ Could not set executable permission for $SCRIPT_PATH\033[0m"
fi
echo -e "\033[0;34m[INFO] Running $SCRIPT_PATH (logging to $LOG_FILE)\033[0m"
bash "$SCRIPT_PATH" train v1 >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
  echo -e "\033[0;31m✗ $SCRIPT_PATH failed. See $LOG_FILE for details.\033[0m"
  tail -20 "$LOG_FILE"
  exit 1
fi
echo -e "\033[0;32m✓ $SCRIPT_PATH completed successfully.\033[0m"
```

---

## Notes

- Always use the same log file for all steps to centralize troubleshooting.
- Use color-coded echoes for all major steps and log references.
- Maintain the same order and echo pattern for all onboarding and Docker steps for consistency and user experience.

#!/usr/bin/env bash
set -euo pipefail

# Ensure a local Django user exists for Postman runs.
# Defaults: username=postman, password=postman123!, email=postman@example.com
# Override via env: POSTMAN_USERNAME, POSTMAN_PASSWORD, POSTMAN_EMAIL

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

USERNAME="${POSTMAN_USERNAME:-postman}"
PASSWORD="${POSTMAN_PASSWORD:-postman123!}"
EMAIL="${POSTMAN_EMAIL:-postman@example.com}"
SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.development}"
POSTMAN_ENV_FILE="${POSTMAN_ENV_FILE:-postman/.env}"

# Choose python: prefer venv, fallback to system
if [[ -x ".venv312/bin/python" ]]; then
  PY_CMD=".venv312/bin/python"
elif [[ -x ".venv/bin/python" ]]; then
  PY_CMD=".venv/bin/python"
else
  PY_CMD="${PYTHON:-python}"
fi

if [[ ! -f "manage.py" ]]; then
  echo "manage.py not found; are you in the project root?" >&2
  exit 1
fi

# Create a local Postman env file with defaults if missing (read-only template).
if [[ ! -f "${POSTMAN_ENV_FILE}" ]]; then
  mkdir -p "$(dirname "${POSTMAN_ENV_FILE}")"
  cat > "${POSTMAN_ENV_FILE}" <<EOF
# Auto-generated local Postman credentials for dev/testing only.
# Do NOT put production secrets here. Override via POSTMAN_USERNAME/POSTMAN_PASSWORD env vars or edit locally.
POSTMAN_USERNAME=${USERNAME}
POSTMAN_PASSWORD=${PASSWORD}
POSTMAN_EMAIL=${EMAIL}
EOF
  chmod 600 "${POSTMAN_ENV_FILE}" || true
  echo "ℹ️  Created ${POSTMAN_ENV_FILE} with local defaults."
fi

${PY_CMD} manage.py shell --settings="${SETTINGS_MODULE}" <<PYCODE
from django.contrib.auth import get_user_model
User = get_user_model()
username = "${USERNAME}"
password = "${PASSWORD}"
email = "${EMAIL}"

user, created = User.objects.get_or_create(username=username, defaults={"email": email})
if created:
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f"✅ Created user '{username}' with provided password.")
else:
    user.set_password(password)
    user.save()
    print(f"ℹ️  Updated password for existing user '{username}'.")
PYCODE

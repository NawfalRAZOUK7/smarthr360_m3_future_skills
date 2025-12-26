#!/usr/bin/env bash
set -euo pipefail

# Run Postman collections via Newman.
# Defaults to API v2 core collection + dev environment. Override with flags.

usage() {
  cat <<'USAGE'
Usage: scripts/run_postman.sh [-c collection] [-e environment] [-r reporters] [-o output_dir]

Options:
  -c  Postman collection file (default: postman/collection_api_v2_core.json)
  -e  Postman environment file (default: postman/environment.dev.json)
  -r  Reporter list for newman (default: cli,json,htmlextra)
  -o  Output directory for reports (default: var/newman/<timestamp>)

Examples:
  scripts/run_postman.sh                      # v2 collection against dev env
  scripts/run_postman.sh -c postman/collection_smoke.json -e postman/environment.staging.json
  scripts/run_postman.sh -r cli,json -o var/newman
USAGE
}

COLLECTION="postman/collection_api_v2_core.json"
ENV_FILE="postman/environment.dev.json"
REPORTERS="cli,json,htmlextra"
OUT_DIR=""  # if empty we create var/newman/<timestamp>
EXTRA_ENV_VARS=()
PY_CMD="python"
BASE_URL_FALLBACK="${BASE_URL_FALLBACK:-http://127.0.0.1:8001}"

# Prefer venv python if available
if [[ -x ".venv312/bin/python" ]]; then
  PY_CMD=".venv312/bin/python"
elif [[ -x ".venv/bin/python" ]]; then
  PY_CMD=".venv/bin/python"
fi

# Optionally load Postman creds from a local file (postman/.env.local or postman/.env)
load_postman_creds() {
  local envfile=""
  for f in postman/.env.local postman/.env; do
    if [[ -f "$f" ]]; then
      envfile="$f"
      break
    fi
  done
  if [[ -z "$envfile" ]]; then
    return
  fi
  while IFS='=' read -r key val; do
    [[ -z "$key" ]] && continue
    [[ "$key" = \#* ]] && continue
    case "$key" in
      POSTMAN_USERNAME) export POSTMAN_USERNAME="${val}";;
      POSTMAN_PASSWORD) export POSTMAN_PASSWORD="${val}";;
    esac
  done < "$envfile"
}

load_postman_creds

while getopts ":c:e:r:o:h" opt; do
  case "${opt}" in
    c) COLLECTION="${OPTARG}" ;;
    e) ENV_FILE="${OPTARG}" ;;
    r) REPORTERS="${OPTARG}" ;;
    o) OUT_DIR="${OPTARG}" ;;
    h) usage; exit 0 ;;
    *) usage; exit 1 ;;
  esac
done

if [[ ! -f "${COLLECTION}" ]]; then
  echo "Collection not found: ${COLLECTION}" >&2
  exit 1
fi
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Environment not found: ${ENV_FILE}" >&2
  exit 1
fi

# Optionally ensure a Postman user exists (local dev)
if [[ -f "scripts/ensure_postman_user.sh" ]]; then
  bash scripts/ensure_postman_user.sh
fi
# Optionally ensure a sample employee exists (for predict/recommend)
if [[ -f "scripts/ensure_sample_employee.sh" ]]; then
  bash scripts/ensure_sample_employee.sh
fi

# Capture a sample employee id and job_role id for ML calls
POSTMAN_EMPLOYEE_EMAIL="${POSTMAN_EMPLOYEE_EMAIL:-postman.employee@example.com}"
EMPLOYEE_ID="$(
  ${PY_CMD} manage.py shell --settings="${DJANGO_SETTINGS_MODULE:-config.settings.development}" -c "
import json
from future_skills.models import Employee, JobRole
email='${POSTMAN_EMPLOYEE_EMAIL}'
emp=Employee.objects.filter(email=email).first()
jr=JobRole.objects.order_by('id').first()
payload={'employee_id': emp.id if emp else '', 'job_role_id': (emp.job_role_id if emp else (jr.id if jr else ''))}
print(json.dumps(payload))
" | tail -n 1
)" || true
if [[ -n "$EMPLOYEE_ID" ]]; then
  EMP_ID_VAL=$(printf '%s' "$EMPLOYEE_ID" | "${PY_CMD}" -c "import sys,json; data=json.load(sys.stdin); print(data.get('employee_id',''))" 2>/dev/null || true)
  JOB_ROLE_VAL=$(printf '%s' "$EMPLOYEE_ID" | "${PY_CMD}" -c "import sys,json; data=json.load(sys.stdin); print(data.get('job_role_id',''))" 2>/dev/null || true)
  if [[ -z "$EMP_ID_VAL" && -n "$JOB_ROLE_VAL" ]]; then
    EMP_ID_VAL="1"
  fi
  if [[ -z "$JOB_ROLE_VAL" ]]; then
    JOB_ROLE_VAL="1"
  fi
  EXTRA_ENV_VARS+=(--env-var "employee_id=${EMP_ID_VAL}" --env-var "job_role_id=${JOB_ROLE_VAL}")
fi

UNIQUE_TAG="$(date +%s)"
EXTRA_ENV_VARS+=(--env-var "bulk_email=bulk.demo+${UNIQUE_TAG}@example.com")

get_env_var() {
  local key="$1"
  "${PY_CMD}" - <<'PY' 2>/dev/null || true
import json, sys
key = sys.argv[1]
env_file = sys.argv[2]
data = json.load(open(env_file))
for item in data.get("values", []):
    if item.get("key") == key:
        val = item.get("value")
        if val is None:
            break
        print(val)
        break
PY
}

if [[ -n "${POSTMAN_USERNAME:-}" && -n "${POSTMAN_PASSWORD:-}" ]]; then
  BASE_URL_OVERRIDE="${BASE_URL_FALLBACK}"
  # Try to read from env file; fallback stays if missing
  READ_BASE_URL=$(get_env_var base_url "${ENV_FILE}" || true)
  if [[ -n "${READ_BASE_URL}" ]]; then
    BASE_URL_OVERRIDE="${READ_BASE_URL}"
  else
    echo "ℹ️  base_url missing in ${ENV_FILE}; forcing fallback ${BASE_URL_OVERRIDE}" >&2
  fi
  if [[ -n "${BASE_URL_OVERRIDE}" ]]; then
    echo "🔑 Fetching access/refresh tokens for Postman using POSTMAN_USERNAME/POSTMAN_PASSWORD..."
    TOKEN_JSON=$(curl -sf -X POST "${BASE_URL_OVERRIDE}/api/auth/token/" \
      -d "username=${POSTMAN_USERNAME}" \
      -d "password=${POSTMAN_PASSWORD}") || TOKEN_JSON=""
    if [[ -n "${TOKEN_JSON}" ]]; then
      ACCESS=$(printf '%s' "${TOKEN_JSON}" | "${PY_CMD}" -c "import sys,json; data=json.load(sys.stdin); print(data.get('access',''))" 2>/dev/null || true)
      REFRESH=$(printf '%s' "${TOKEN_JSON}" | "${PY_CMD}" -c "import sys,json; data=json.load(sys.stdin); print(data.get('refresh',''))" 2>/dev/null || true)
      if [[ -n "${ACCESS}" && -n "${REFRESH}" ]]; then
        EXTRA_ENV_VARS+=(--env-var "access_token=${ACCESS}" --env-var "refresh_token=${REFRESH}")
        echo "✅ Token acquired and injected for this run."
      else
        echo "⚠️  Token fetch succeeded but response missing tokens; proceeding without injection." >&2
      fi
    else
      echo "⚠️  Token auto-fetch failed; proceeding without injection." >&2
    fi
  fi
fi

# Build per-run output directory if not provided
RUN_ID="$(date +%Y%m%d_%H%M%S)"
if [[ -z "${OUT_DIR}" ]]; then
  OUT_DIR="var/newman/${RUN_ID}"
fi
mkdir -p "${OUT_DIR}"

# Generate a unique CSV for bulk upload to avoid duplicate-email errors
UPLOAD_CSV="${OUT_DIR}/employees_upload.csv"
cat > "${UPLOAD_CSV}" <<EOF
name,email,department,position,job_role_id,current_skills
Upload Demo One,upload.demo.one+${RUN_ID}@example.com,Data,Data Analyst,1,"Python;Data Analysis"
Upload Demo Two,upload.demo.two+${RUN_ID}@example.com,Operations,Project Manager,1,"Project Management;Communication"
EOF
EXTRA_ENV_VARS+=(--env-var "bulk_upload_file=$(pwd)/${UPLOAD_CSV}")

# Prefer globally installed newman; fallback to npx if available.
if command -v newman >/dev/null 2>&1; then
  RUNNER="newman"
elif [[ -x "var/newman_deps/bin/newman" ]]; then
  RUNNER="var/newman_deps/bin/newman"
elif command -v npx >/dev/null 2>&1; then
  # Ephemeral install per run; avoids local node_modules conflicts
  RUNNER="npx -p newman@6 -p newman-reporter-html -p newman-reporter-htmlextra newman"
else
  echo "Newman not found and npx unavailable. Please install Node.js/npm." >&2
  exit 1
fi

set -x
${RUNNER} run "${COLLECTION}" \
  -e "${ENV_FILE}" \
  -r "${REPORTERS}" \
  --reporter-json-export "${OUT_DIR}/report.json" \
  --reporter-htmlextra-export "${OUT_DIR}/report.html" \
  "${EXTRA_ENV_VARS[@]-}" || exit $?

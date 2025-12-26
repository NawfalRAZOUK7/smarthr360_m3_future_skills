#!/usr/bin/env bash
set -euo pipefail

# Run Postman collection with ML endpoints (wrapper around run_postman.sh).
# Use after starting the server with make serve-ml (ML enabled).

BASE_URL_FALLBACK="${BASE_URL_FALLBACK:-http://127.0.0.1:8001}"
# Default to full collection so ML + core endpoints run; override via POSTMAN_COLLECTION if needed.
COLLECTION="${POSTMAN_COLLECTION:-postman/collection_api_v2.json}"
ENV_FILE="${POSTMAN_ENV:-postman/environment.dev.json}"
REPORTERS="${POSTMAN_REPORTERS:-cli,json,htmlextra}"
OUT_DIR="${POSTMAN_OUT_DIR:-}"

BASE_URL_FALLBACK="${BASE_URL_FALLBACK}" \
  ./scripts/run_postman.sh -c "${COLLECTION}" -e "${ENV_FILE}" -r "${REPORTERS}" -o "${OUT_DIR}"

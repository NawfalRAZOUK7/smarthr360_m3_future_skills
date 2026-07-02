#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

START_YEAR="${START_YEAR:-2018}"
END_YEAR="${END_YEAR:-2026}"
START_DATE="${START_DATE:-${START_YEAR}-01-01}"
END_DATE="${END_DATE:-${END_YEAR}-01-01}"
BASELINE_DAYS="${BASELINE_DAYS:-540}"
RECENT_DAYS="${RECENT_DAYS:-540}"
MIN_SAMPLES="${MIN_SAMPLES:-100}"
SIMULATE="${SIMULATE:-1}"
REPLAY_RUNS="${REPLAY_RUNS:-5}"
RUN_SHIFT_MINUTES="${RUN_SHIFT_MINUTES:-30}"

ARCHIVE_DIR="${ARCHIVE_DIR:-$ROOT_DIR/prediction_skills/logs/archive}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "Activate your venv first (source .venv/bin/activate)." >&2
  exit 1
fi

mkdir -p "$ARCHIVE_DIR"

archive_log() {
  local path="$1"
  if [[ -f "$path" ]]; then
    mv "$path" "$ARCHIVE_DIR/$(basename "$path").$TIMESTAMP"
  fi
}

archive_log "$ROOT_DIR/prediction_skills/logs/predictions_monitoring.jsonl"
archive_log "$ROOT_DIR/prediction_skills/logs/predictions_monitoring_professional.jsonl"
archive_log "$ROOT_DIR/prediction_skills/logs/future_skills_drift_report.json"
archive_log "$ROOT_DIR/prediction_skills/logs/future_skills_drift_report_professional.json"

cd "$ROOT_DIR"

python prediction_skills/scripts/seed_economic_trends.py --start-year "$START_YEAR" --end-year "$END_YEAR" --overwrite
python prediction_skills/manage.py generate_future_skill_snapshots \
  --start-date "$START_DATE" \
  --end-date "$END_DATE" \
  --frequency monthly \
  --overwrite

for ((run=1; run<=REPLAY_RUNS; run++)); do
  replay_args=(--baseline-days "$BASELINE_DAYS" --recent-days "$RECENT_DAYS" --min-samples "$MIN_SAMPLES")
  if [[ "$run" -eq 1 ]]; then
    replay_args+=(--reset-log)
  fi
  if [[ "$SIMULATE" == "1" ]]; then
    replay_args+=(--simulate)
  fi
  shift_minutes=$(( (run - 1) * RUN_SHIFT_MINUTES ))
  replay_args+=(--timestamp-shift-minutes "$shift_minutes")

  python prediction_skills/scripts/replay_future_skills_snapshots.py "${replay_args[@]}"
done

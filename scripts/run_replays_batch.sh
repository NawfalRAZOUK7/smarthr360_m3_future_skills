#!/usr/bin/env bash
# Run multiple replays of future_skills snapshots with incremental timestamp shifts.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

RUNS="${RUNS:-5}"
SHIFT_MINUTES="${SHIFT_MINUTES:-30}"
BASELINE_DAYS="${BASELINE_DAYS:-540}"
RECENT_DAYS="${RECENT_DAYS:-540}"
MIN_SAMPLES="${MIN_SAMPLES:-100}"
SIMULATE="${SIMULATE:-1}"
RESET_FIRST="${RESET_FIRST:-1}"
MAX_DATES="${MAX_DATES:-}"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "Activate your venv first (source .venv/bin/activate)." >&2
  exit 1
fi

cd "$ROOT_DIR"

for ((run=1; run<=RUNS; run++)); do
  shift_minutes=$(( (run - 1) * SHIFT_MINUTES ))
  args=(--baseline-days "$BASELINE_DAYS" --recent-days "$RECENT_DAYS" --min-samples "$MIN_SAMPLES" --timestamp-shift-minutes "$shift_minutes")
  if [[ -n "$MAX_DATES" ]]; then
    args+=(--max-dates "$MAX_DATES")
  fi
  if [[ "$SIMULATE" == "1" ]]; then
    args+=(--simulate)
  fi
  if [[ "$run" -eq 1 && "$RESET_FIRST" == "1" ]]; then
    args=(--reset-log "${args[@]}")
  fi

  echo "▶️  Replay run $run/$RUNS (shift=${shift_minutes}m)..."
  python prediction_skills/scripts/replay_future_skills_snapshots.py "${args[@]}"
done

echo "✅ Replays completed."

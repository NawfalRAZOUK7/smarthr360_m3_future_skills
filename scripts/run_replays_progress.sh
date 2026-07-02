#!/usr/bin/env bash
set -euo pipefail

# Progress-friendly batch wrapper around replay_future_skills_snapshots.py.
# Environment variables (override defaults as needed):
#   RUNS (default 3)              : number of replays to run
#   SHIFT_MINUTES (default 20)    : per-run timestamp shift to de-correlate windows
#   BASELINE_DAYS (default 720)   : baseline window size
#   RECENT_DAYS (default 720)     : recent window size
#   MIN_SAMPLES (default 100)     : minimum samples per window
#   MAX_DATES (default 30)        : cap number of snapshot dates to accelerate runs
#   RESET_FIRST (default 1)       : reset monitoring log before first run if 1

RUNS="${RUNS:-3}"
SHIFT_MINUTES="${SHIFT_MINUTES:-20}"
BASELINE_DAYS="${BASELINE_DAYS:-720}"
RECENT_DAYS="${RECENT_DAYS:-720}"
MIN_SAMPLES="${MIN_SAMPLES:-100}"
MAX_DATES="${MAX_DATES:-30}"
RESET_FIRST="${RESET_FIRST:-1}"
export PYTHONWARNINGS="${PYTHONWARNINGS:-ignore::UserWarning:sklearn.utils.parallel}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPLAY="$SCRIPT_DIR/replay_future_skills_snapshots.py"

if [[ "${RESET_FIRST}" == "1" ]]; then
  echo "🧹 Resetting log before first run..."
  python "$REPLAY" --reset-log --simulate \
    --baseline-days "$BASELINE_DAYS" \
    --recent-days "$RECENT_DAYS" \
    --min-samples "$MIN_SAMPLES" \
    --max-dates "$MAX_DATES" \
    --timestamp-shift-minutes 0
fi

for i in $(seq 1 "$RUNS"); do
  shift_val=$(( (i-1) * SHIFT_MINUTES ))
  echo ""
  echo "▶️  Replay run $i/$RUNS (shift=${shift_val}m)…"
  start_ts=$(date +%s)
  python "$REPLAY" --simulate \
    --baseline-days "$BASELINE_DAYS" \
    --recent-days "$RECENT_DAYS" \
    --min-samples "$MIN_SAMPLES" \
    --max-dates "$MAX_DATES" \
    --timestamp-shift-minutes "$shift_val"
  end_ts=$(date +%s)
  echo "⏱️  Run $i finished in $((end_ts - start_ts))s"
done

echo ""
echo "✅ Batch complete. Latest drift report:"
echo "    prediction_skills/logs/future_skills_drift_report_professional.json"

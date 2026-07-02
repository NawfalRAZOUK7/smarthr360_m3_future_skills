#!/usr/bin/env python3
"""Run repeated recalculations, backfill baseline logs, and recompute drift."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

DEFAULT_FEATURES = [
    "trend_score",
    "internal_usage",
    "training_requests",
    "scarcity_index",
    "economic_indicator",
]


def _parse_timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _window_bounds(
    now: datetime,
    *,
    baseline_days: int,
    recent_days: int,
) -> Tuple[datetime, datetime, datetime, datetime]:
    recent_end = now
    recent_start = recent_end - timedelta(days=recent_days)
    baseline_end = recent_start
    baseline_start = baseline_end - timedelta(days=baseline_days)
    return baseline_start, baseline_end, recent_start, recent_end


def _load_entries(log_path: Path) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    if not log_path.exists():
        return entries
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            entries.append(entry)
    return entries


def _count_window_samples(
    entries: Iterable[Dict[str, Any]],
    *,
    features: Iterable[str],
    baseline_start: datetime,
    baseline_end: datetime,
    recent_start: datetime,
    recent_end: datetime,
) -> Dict[str, Dict[str, int]]:
    counts = {feature: {"baseline": 0, "recent": 0} for feature in features}
    for entry in entries:
        timestamp = _parse_timestamp(entry.get("timestamp"))
        if not timestamp:
            continue
        if baseline_start <= timestamp < baseline_end:
            window = "baseline"
        elif recent_start <= timestamp <= recent_end:
            window = "recent"
        else:
            continue

        feature_payload = entry.get("features") or {}
        for feature in features:
            value = feature_payload.get(feature)
            if value is None:
                continue
            counts[feature][window] += 1
    return counts


def _eligible_entries(entries: Iterable[Dict[str, Any]], *, features: Iterable[str]) -> List[Dict[str, Any]]:
    required = set(features)
    eligible: List[Dict[str, Any]] = []
    for entry in entries:
        payload = entry.get("features") or {}
        if required.issubset(payload.keys()):
            eligible.append(entry)
    return eligible


def _build_backfill_entries(
    source_entries: List[Dict[str, Any]],
    *,
    count: int,
    baseline_start: datetime,
    baseline_end: datetime,
) -> List[Dict[str, Any]]:
    if not source_entries or count <= 0:
        return []

    span_seconds = int((baseline_end - baseline_start).total_seconds())
    if span_seconds <= 1:
        raise ValueError("Baseline window is too small to backfill.")

    backfilled: List[Dict[str, Any]] = []
    step = 997  # prime-ish step to spread timestamps deterministically
    for idx in range(count):
        source = deepcopy(source_entries[idx % len(source_entries)])
        offset = (idx * step) % (span_seconds - 1)
        source["timestamp"] = (baseline_start + timedelta(seconds=offset)).isoformat()
        backfilled.append(source)
    return backfilled


def _append_entries(log_path: Path, entries: Iterable[Dict[str, Any]]) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with log_path.open("a", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
            written += 1
    return written


def _run_management_command(base_dir: Path, args: List[str]) -> None:
    cmd = [sys.executable, str(base_dir / "manage.py"), *args]
    subprocess.run(cmd, cwd=base_dir, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate monitoring data by running predictions and backfilling baseline logs.",
    )
    parser.add_argument("--runs", type=int, default=1, help="Number of recalculation runs to execute.")
    parser.add_argument("--horizon", type=int, default=5, help="Prediction horizon in years.")
    parser.add_argument("--baseline-days", type=int, default=90, help="Baseline window size in days.")
    parser.add_argument("--recent-days", type=int, default=30, help="Recent window size in days.")
    parser.add_argument("--min-samples", type=int, default=100, help="Minimum samples required per window.")
    parser.add_argument(
        "--backfill-buffer",
        type=int,
        default=25,
        help="Extra baseline entries to add above the minimum to avoid window shifts.",
    )
    parser.add_argument(
        "--backfill-margin-minutes",
        type=int,
        default=360,
        help="Minutes to keep clear from baseline window edges when backfilling.",
    )
    parser.add_argument(
        "--features",
        nargs="*",
        default=DEFAULT_FEATURES,
        help="Features to enforce minimum counts on.",
    )
    parser.add_argument("--log-path", type=str, default=None, help="Override predictions_monitoring.jsonl path.")
    parser.add_argument("--backfill-baseline", action="store_true", help="Backfill baseline window using recent logs.")
    parser.add_argument(
        "--backfill-count",
        type=int,
        default=0,
        help="Explicit number of baseline entries to backfill (overrides auto).",
    )
    parser.add_argument("--dry-run-backfill", action="store_true", help="Show counts without writing backfill logs.")
    parser.add_argument("--no-recalc", action="store_true", help="Skip prediction recalculation runs.")
    parser.add_argument("--no-drift", action="store_true", help="Skip drift recomputation.")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]
    log_path = Path(args.log_path) if args.log_path else base_dir / "logs" / "predictions_monitoring.jsonl"

    if not args.no_recalc:
        for _ in range(args.runs):
            _run_management_command(
                base_dir,
                ["recalculate_future_skills", "--horizon", str(args.horizon)],
            )

    entries = _load_entries(log_path)
    now = datetime.now(timezone.utc)
    baseline_start, baseline_end, recent_start, recent_end = _window_bounds(
        now,
        baseline_days=args.baseline_days,
        recent_days=args.recent_days,
    )
    counts = _count_window_samples(
        entries,
        features=args.features,
        baseline_start=baseline_start,
        baseline_end=baseline_end,
        recent_start=recent_start,
        recent_end=recent_end,
    )
    print("Window counts:")
    for feature in args.features:
        print(
            f"- {feature}: baseline={counts[feature]['baseline']} recent={counts[feature]['recent']}"
        )

    if args.backfill_baseline:
        target = args.min_samples + max(0, args.backfill_buffer)
        needed_by_feature = [
            max(0, target - counts[feature]["baseline"]) for feature in args.features
        ]
        needed = max(needed_by_feature) if needed_by_feature else 0
        backfill_count = args.backfill_count or needed

        if backfill_count <= 0:
            print("Backfill not required for baseline window.")
        else:
            eligible = _eligible_entries(entries, features=args.features)
            if not eligible:
                print("No eligible entries with full feature set to backfill.")
            else:
                margin = timedelta(minutes=max(0, args.backfill_margin_minutes))
                adjusted_start = baseline_start + margin
                adjusted_end = baseline_end - margin
                if adjusted_end <= adjusted_start:
                    adjusted_start = baseline_start
                    adjusted_end = baseline_end
                backfill_entries = _build_backfill_entries(
                    eligible,
                    count=backfill_count,
                    baseline_start=adjusted_start,
                    baseline_end=adjusted_end,
                )
                if args.dry_run_backfill:
                    print(f"Dry run: would backfill {len(backfill_entries)} entries.")
                else:
                    written = _append_entries(log_path, backfill_entries)
                    print(f"Backfilled {written} baseline entries into {log_path}.")
                    entries = _load_entries(log_path)
                    counts = _count_window_samples(
                        entries,
                        features=args.features,
                        baseline_start=baseline_start,
                        baseline_end=baseline_end,
                        recent_start=recent_start,
                        recent_end=recent_end,
                    )
                    print("Window counts after backfill:")
                    for feature in args.features:
                        print(
                            f"- {feature}: baseline={counts[feature]['baseline']} recent={counts[feature]['recent']}"
                        )

    if not args.no_drift:
        _run_management_command(base_dir, ["compute_future_skills_drift"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

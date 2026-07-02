#!/usr/bin/env python3
"""Seed MarketTrend and EconomicReport time series for data variability."""

from __future__ import annotations

import argparse
import os
import random
import sys
from dataclasses import dataclass
from typing import Iterable, List

import django


@dataclass
class SeriesConfig:
    base: float
    drift: float
    noise: float
    min_value: float
    max_value: float


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _normalize_sector(value: str) -> str:
    return (value or "").strip() or "General"


def _build_series(
    *,
    years: Iterable[int],
    seed: int,
    config: SeriesConfig,
) -> List[tuple[int, float]]:
    rand = random.Random(seed)
    value = _clamp(config.base + rand.uniform(-config.noise, config.noise), config.min_value, config.max_value)
    series = []
    for year in years:
        value = _clamp(
            value + config.drift + rand.uniform(-config.noise, config.noise),
            config.min_value,
            config.max_value,
        )
        series.append((year, round(value, 4)))
    return series


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed synthetic MarketTrend and EconomicReport time series per sector.",
    )
    parser.add_argument("--start-year", type=int, default=2019, help="First year to generate.")
    parser.add_argument("--end-year", type=int, default=2026, help="Last year to generate.")
    parser.add_argument("--seed", type=int, default=42, help="Base seed for deterministic series.")
    parser.add_argument(
        "--sectors",
        type=str,
        default=None,
        help="Comma-separated list of sectors (defaults to JobRole departments + Tech/RH).",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing rows.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing.")
    args = parser.parse_args()

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    django.setup()

    from future_skills.models import EconomicReport, JobRole, MarketTrend

    years = list(range(args.start_year, args.end_year + 1))
    if not years:
        print("No years to generate.")
        return 0

    sectors: List[str] = []
    if args.sectors:
        sectors = [_normalize_sector(value) for value in args.sectors.split(",") if value.strip()]
    else:
        sectors = sorted(
            {_normalize_sector(item) for item in JobRole.objects.values_list("department", flat=True)}
        )
        sectors.extend(["Tech", "RH"])
        sectors = sorted(set(sectors))

    # Near-zero drift/noise for a healthy baseline (lower PSI/KS expected)
    trend_config = SeriesConfig(base=0.55, drift=0.001, noise=0.005, min_value=0.2, max_value=0.95)
    econ_config = SeriesConfig(base=55.0, drift=0.1, noise=0.2, min_value=35.0, max_value=85.0)

    created_trends = 0
    updated_trends = 0
    created_econ = 0
    updated_econ = 0

    for sector in sectors:
        sector_seed = args.seed + (hash(sector) & 0xFFFF)
        trend_series = _build_series(years=years, seed=sector_seed, config=trend_config)
        econ_series = _build_series(years=years, seed=sector_seed + 1000, config=econ_config)

        for year, trend_value in trend_series:
            defaults = {
                "title": f"Trend {sector} {year}",
                "source_name": "Synthetic Series",
                "sector": sector,
                "year": year,
                "trend_score": trend_value,
            }
            if args.dry_run:
                continue
            qs = MarketTrend.objects.filter(sector=sector, year=year)
            if qs.exists():
                if args.overwrite:
                    updated_trends += qs.update(**defaults)
                continue
            MarketTrend.objects.create(**defaults)
            created_trends += 1

        for year, econ_value in econ_series:
            defaults = {
                "title": f"Economic outlook {sector} {year}",
                "source_name": "Synthetic Series",
                "indicator": "Sector Index",
                "sector": sector,
                "year": year,
                "value": econ_value,
            }
            if args.dry_run:
                continue
            qs = EconomicReport.objects.filter(sector=sector, year=year, indicator="Sector Index")
            if qs.exists():
                if args.overwrite:
                    updated_econ += qs.update(**defaults)
                continue
            EconomicReport.objects.create(**defaults)
            created_econ += 1

    if args.dry_run:
        print("Dry run complete. No changes written.")
        return 0

    print(
        "Seed complete: "
        f"MarketTrend created={created_trends} updated={updated_trends}; "
        f"EconomicReport created={created_econ} updated={updated_econ}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

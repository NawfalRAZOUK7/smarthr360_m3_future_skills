"""Generate FutureSkillSnapshot records for silver label derivation."""

import random
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from future_skills.models import FutureSkillSnapshot, JobRole, Skill
from future_skills.services.prediction_engine import _estimate_internal_usage, _estimate_training_requests
from future_skills.services.snapshot_service import (
    add_months,
    apply_time_drift,
    estimate_avg_salary,
    estimate_hiring_difficulty,
    estimate_scarcity_index,
    get_economic_indicator,
    get_market_trend_for_context,
    normalize_training_requests,
)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _iter_snapshot_dates(
    as_of_date: date | None,
    start_date: date | None,
    end_date: date | None,
    frequency: str,
) -> list[date]:
    if as_of_date:
        return [as_of_date]

    if (start_date and not end_date) or (end_date and not start_date):
        raise CommandError("Provide both --start-date and --end-date for a range.")

    if start_date and end_date:
        if start_date > end_date:
            raise CommandError("--start-date must be before or equal to --end-date.")
        step_months = 1 if frequency == "monthly" else 3
        dates = []
        current = start_date
        while current <= end_date:
            dates.append(current)
            current = add_months(current, step_months)
        return dates

    return [timezone.now().date()]


class Command(BaseCommand):
    """Generate snapshot records for future skill signals."""

    help = "Generate FutureSkillSnapshot rows for a date or a date range."

    def add_arguments(self, parser):
        parser.add_argument(
            "--as-of-date",
            type=str,
            default=None,
            help="Snapshot date (YYYY-MM-DD). Overrides start/end range if provided.",
        )
        parser.add_argument(
            "--start-date",
            type=str,
            default=None,
            help="Range start date (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--end-date",
            type=str,
            default=None,
            help="Range end date (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--frequency",
            type=str,
            default="monthly",
            choices=["monthly", "quarterly"],
            help="Snapshot frequency for date ranges (monthly or quarterly).",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Update existing snapshots instead of skipping them.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Base seed used to create deterministic random factors.",
        )

    def handle(self, *args, **options):
        as_of_date = _parse_date(options.get("as_of_date"))
        start_date = _parse_date(options.get("start_date"))
        end_date = _parse_date(options.get("end_date"))
        frequency = options.get("frequency")
        overwrite = options.get("overwrite")
        seed_base = options.get("seed")

        dates = _iter_snapshot_dates(as_of_date, start_date, end_date, frequency)

        job_roles = list(JobRole.objects.all())
        skills = list(Skill.objects.all())

        if not job_roles or not skills:
            self.stdout.write(
                self.style.ERROR("Aucun JobRole ou Skill trouvé. Peuple d'abord la base.")
            )
            return

        existing_keys = set(
            FutureSkillSnapshot.objects.filter(as_of_date__in=dates).values_list(
                "job_role_id",
                "skill_id",
                "as_of_date",
            )
        )

        to_create = []
        updated_count = 0
        skipped_count = 0

        for snapshot_date in dates:
            for job_role in job_roles:
                for skill in skills:
                    key = (job_role.id, skill.id, snapshot_date)
                    if not overwrite and key in existing_keys:
                        skipped_count += 1
                        continue

                    seed_value = hash((seed_base, job_role.id, skill.id, snapshot_date.toordinal())) & 0xFFFFFFFF
                    rand = random.Random(seed_value)

                    skill_profile = f"{skill.name or ''} {skill.category or ''}".lower()
                    positive_keywords = ("ai", "data", "cloud", "cyber", "python", "ml", "machine")
                    negative_keywords = ("legacy", "obsolete", "deprecated")
                    if any(keyword in skill_profile for keyword in positive_keywords):
                        drift_sign = 1.0
                    elif any(keyword in skill_profile for keyword in negative_keywords):
                        drift_sign = -1.0
                    else:
                        drift_sign = 0.2

                    trend_base = get_market_trend_for_context(job_role, skill, as_of_date=snapshot_date)
                    trend_score = apply_time_drift(
                        trend_base,
                        snapshot_date,
                        drift_per_month=0.0015 * drift_sign,
                        seasonal_amplitude=0.04,
                        noise_amplitude=0.02,
                        rand=rand,
                    )

                    internal_base = _estimate_internal_usage(job_role, skill)
                    internal_usage = apply_time_drift(
                        internal_base,
                        snapshot_date,
                        drift_per_month=0.001 * drift_sign,
                        seasonal_amplitude=0.02,
                        noise_amplitude=0.02,
                        rand=rand,
                    )

                    training_base = _estimate_training_requests(job_role, skill)
                    training_norm = normalize_training_requests(training_base)
                    training_norm = apply_time_drift(
                        training_norm,
                        snapshot_date,
                        drift_per_month=0.001 * drift_sign,
                        seasonal_amplitude=0.03,
                        noise_amplitude=0.01,
                        rand=rand,
                    )
                    training_requests = max(5.0, min(60.0, round(training_norm * 100.0, 1)))

                    scarcity_index = estimate_scarcity_index(job_role, skill, internal_usage)
                    hiring_difficulty = estimate_hiring_difficulty(job_role, skill, scarcity_index, rand=rand)
                    avg_salary_k = estimate_avg_salary(job_role, skill, hiring_difficulty, rand=rand)
                    economic_indicator = get_economic_indicator(job_role, as_of_date=snapshot_date)

                    snapshot_payload = {
                        "trend_score": trend_score,
                        "internal_usage": internal_usage,
                        "training_requests": training_requests,
                        "scarcity_index": scarcity_index,
                        "hiring_difficulty": hiring_difficulty,
                        "avg_salary_k": avg_salary_k,
                        "economic_indicator": economic_indicator,
                    }

                    if overwrite and key in existing_keys:
                        FutureSkillSnapshot.objects.filter(
                            job_role=job_role,
                            skill=skill,
                            as_of_date=snapshot_date,
                        ).update(**snapshot_payload)
                        updated_count += 1
                    else:
                        to_create.append(
                            FutureSkillSnapshot(
                                job_role=job_role,
                                skill=skill,
                                as_of_date=snapshot_date,
                                **snapshot_payload,
                            )
                        )

        if to_create:
            FutureSkillSnapshot.objects.bulk_create(to_create, batch_size=1000)

        created_count = len(to_create)
        self.stdout.write(
            self.style.SUCCESS(
                "Snapshots générés. "
                f"Dates: {len(dates)} | Créés: {created_count} | "
                f"Mis à jour: {updated_count} | Ignorés: {skipped_count}"
            )
        )

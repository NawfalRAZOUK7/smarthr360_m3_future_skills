# future_skills/management/commands/export_future_skills_dataset.py

"""Export a synthetic Future Skills dataset for ML training."""

import csv
import random
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from future_skills.models import FutureSkillLabel, FutureSkillSnapshot, JobRole, Skill
from future_skills.services.prediction_engine import (
    _estimate_internal_usage,
    _estimate_training_requests,
    _normalize_training_requests,
    calculate_level,
)
from future_skills.services.snapshot_service import (
    add_months,
    compute_interaction_features,
    compute_time_features,
    estimate_avg_salary,
    estimate_hiring_difficulty,
    estimate_scarcity_index,
    get_economic_indicator,
    get_market_trend_for_context,
)

ALLOWED_PROVENANCE = {"BRONZE", "SILVER", "GOLD"}
TIME_WINDOW_MONTHS = 6


def _quantile_threshold(values: list[float], quantile: float) -> float:
    """Return the nearest-rank quantile threshold from the values."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int((len(ordered) - 1) * quantile)
    return ordered[index]


def _compute_silver_thresholds(scores: list[float]) -> tuple[float, float]:
    """Compute LOW/MED/HIGH thresholds for silver label bucketing."""
    low_threshold = _quantile_threshold(scores, 0.33)
    high_threshold = _quantile_threshold(scores, 0.66)
    return low_threshold, high_threshold


def _assign_level_from_thresholds(score: float, low_threshold: float, high_threshold: float) -> str:
    """Assign LOW/MEDIUM/HIGH based on provided thresholds."""
    if low_threshold == high_threshold:
        if score < low_threshold:
            return "LOW"
        if score > high_threshold:
            return "HIGH"
        return "MEDIUM"

    if score <= low_threshold:
        return "LOW"
    if score <= high_threshold:
        return "MEDIUM"
    return "HIGH"


def _compute_silver_delta_score(current: FutureSkillSnapshot, future: FutureSkillSnapshot) -> float:
    """Compute a delta score from snapshot deltas between T and T+H."""
    trend_delta = future.trend_score - current.trend_score
    internal_delta = future.internal_usage - current.internal_usage
    training_delta = _normalize_training_requests(future.training_requests) - _normalize_training_requests(
        current.training_requests
    )
    return 0.5 * trend_delta + 0.3 * internal_delta + 0.2 * training_delta


def _get_window_snapshots(
    snapshot_lookup: dict,
    job_id: int,
    skill_id: int,
    as_of_date: date,
    window_months: int,
) -> list[FutureSkillSnapshot]:
    dates = [add_months(as_of_date, -offset) for offset in range(window_months - 1, -1, -1)]
    snapshots = [snapshot_lookup.get((job_id, skill_id, snap_date)) for snap_date in dates]
    return [snapshot for snapshot in snapshots if snapshot is not None]


def _assign_levels_by_rank(rows: list[dict]) -> None:
    """Assign LOW/MEDIUM/HIGH by rank when thresholds collapse."""
    if not rows:
        return

    ordered = sorted(
        rows,
        key=lambda row: (
            row["delta_score"],
            row["job"].id,
            row["skill"].id,
            row["as_of_date"],
        ),
    )
    total = len(ordered)

    if total < 3:
        for row in ordered:
            row["level"] = "MEDIUM"
        ordered[0]["level"] = "LOW"
        if total > 1:
            ordered[-1]["level"] = "HIGH"
        return

    low_cut = total // 3
    high_cut = (2 * total) // 3

    for index, row in enumerate(ordered):
        if index < low_cut:
            row["level"] = "LOW"
        elif index < high_cut:
            row["level"] = "MEDIUM"
        else:
            row["level"] = "HIGH"


def _iter_export_dates(
    as_of_date: date | None,
    start_date: date | None,
    end_date: date | None,
    frequency: str,
) -> list[date]:
    if as_of_date:
        return [as_of_date]

    if (start_date and not end_date) or (end_date and not start_date):
        raise ValueError("Provide both --start-date and --end-date for a range.")

    if start_date and end_date:
        if start_date > end_date:
            raise ValueError("--start-date must be before or equal to --end-date.")
        step_months = 1 if frequency == "monthly" else 3
        dates = []
        current = start_date
        while current <= end_date:
            dates.append(current)
            current = add_months(current, step_months)
        return dates

    return [timezone.now().date()]


class Command(BaseCommand):
    """Generate and export the enriched Future Skills CSV dataset."""

    help = (
        "Exporte un dataset CSV pour le futur modèle de ML du Module 3 "
        "à partir des données (JobRole, Skill) et du moteur de règles actuel."
    )

    def add_arguments(self, parser):
        """Add CLI options for dataset export."""
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Chemin du fichier CSV de sortie (par défaut: BASE_DIR/artifacts/datasets/future_skills_dataset.csv).",
        )
        parser.add_argument(
            "--as-of-date",
            type=str,
            default=None,
            help="Date snapshot (YYYY-MM-DD). Par défaut: date du jour.",
        )
        parser.add_argument(
            "--start-date",
            type=str,
            default=None,
            help="Date de début pour une exportation multi-snapshots (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--end-date",
            type=str,
            default=None,
            help="Date de fin pour une exportation multi-snapshots (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--frequency",
            type=str,
            default="monthly",
            choices=["monthly", "quarterly"],
            help="Fréquence des snapshots pour une plage de dates (monthly/quarterly).",
        )
        parser.add_argument(
            "--horizon-months",
            type=int,
            default=12,
            help="Horizon en mois (par défaut: 12).",
        )
        parser.add_argument(
            "--label-provenance",
            type=str,
            default="BRONZE",
            help="Provenance du label (BRONZE/SILVER/GOLD). Par défaut: BRONZE.",
        )

    def handle(self, *args, **options):
        """Build the dataset rows and write them to CSV."""
        # Set random seed for reproducibility
        random.seed(42)

        as_of_date_raw = options.get("as_of_date")
        horizon_months = options.get("horizon_months")
        label_provenance = (options.get("label_provenance") or "BRONZE").upper()

        if label_provenance not in ALLOWED_PROVENANCE:
            raise ValueError(
                f"label_provenance must be one of {sorted(ALLOWED_PROVENANCE)}; got {label_provenance}"
            )

        if horizon_months is None or horizon_months <= 0:
            raise ValueError("horizon_months must be a positive integer")

        start_date_raw = options.get("start_date")
        end_date_raw = options.get("end_date")
        frequency = options.get("frequency") or "monthly"

        as_of_date = date.fromisoformat(as_of_date_raw) if as_of_date_raw else None
        start_date = date.fromisoformat(start_date_raw) if start_date_raw else None
        end_date = date.fromisoformat(end_date_raw) if end_date_raw else None

        export_dates = _iter_export_dates(as_of_date, start_date, end_date, frequency)

        # Déterminer le chemin de sortie
        output_path = options["output"]
        if not output_path:
            ml_data_dir = settings.ML_DATASETS_DIR
            ml_data_dir.mkdir(parents=True, exist_ok=True)
            output_path = ml_data_dir / "future_skills_dataset.csv"
        else:
            output_path = Path(output_path)

        self.stdout.write(self.style.WARNING(f"Export du dataset vers : {output_path}"))
        if len(export_dates) > 1:
            self.stdout.write(
                self.style.WARNING(
                    f"Export multi-dates: {export_dates[0].isoformat()} -> {export_dates[-1].isoformat()} "
                    f"({len(export_dates)} snapshots, {frequency})"
                )
            )

        # Préparer les données
        job_roles = JobRole.objects.all()
        skills = Skill.objects.all()

        if not job_roles.exists() or not skills.exists():
            self.stdout.write(
                self.style.ERROR(
                    "Aucun JobRole ou Skill trouvé en base. " "Peuple d'abord la base avec des données de démo."
                )
            )
            return

        # Ouvrir le CSV et écrire l'en-tête avec les nouvelles colonnes
        with open(output_path, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "job_role_name",
                    "skill_name",
                    "skill_category",
                    "job_department",
                    "as_of_date",
                    "horizon_months",
                    "label_provenance",
                    "trend_score",
                    "internal_usage",
                    "training_requests",
                    "scarcity_index",
                    "hiring_difficulty",
                    "avg_salary_k",
                    "economic_indicator",
                    "trend_momentum",
                    "trend_acceleration",
                    "trend_volatility",
                    "trend_persistence",
                    "internal_usage_momentum",
                    "training_requests_momentum",
                    "internal_usage_lag_1",
                    "internal_usage_lag_2",
                    "internal_usage_roll_mean_3",
                    "training_requests_lag_1",
                    "training_requests_lag_2",
                    "training_requests_roll_mean_3",
                    "economic_indicator_lag_1",
                    "economic_indicator_lag_2",
                    "economic_indicator_roll_mean_3",
                    "trend_stability_flag",
                    "internal_usage_stability_flag",
                    "training_requests_stability_flag",
                    "data_quality_window_coverage",
                    "data_quality_missing_flag",
                    "data_quality_stale_flag",
                    "data_quality_low_sample_flag",
                    "forecast_trend_score",
                    "forecast_internal_usage",
                    "forecast_training_requests",
                    "forecast_need_score",
                    "is_it_department",
                    "is_senior_role",
                    "is_technical_skill",
                    "dept_skill_alignment",
                    "future_need_level",
                ]
            )

            row_count = 0
            if label_provenance == "SILVER":
                target_dates = {add_months(export_date, horizon_months) for export_date in export_dates}
                window_dates = {
                    add_months(export_date, -offset)
                    for export_date in export_dates
                    for offset in range(TIME_WINDOW_MONTHS)
                }
                snapshots = FutureSkillSnapshot.objects.filter(
                    as_of_date__in=list(set(export_dates) | target_dates | window_dates),
                    job_role__in=job_roles,
                    skill__in=skills,
                )

                snapshot_lookup = {
                    (snapshot.job_role_id, snapshot.skill_id, snapshot.as_of_date): snapshot for snapshot in snapshots
                }

                rows = []
                missing_pairs = 0
                for export_date in export_dates:
                    target_date = add_months(export_date, horizon_months)
                    for job in job_roles:
                        for skill in skills:
                            current = snapshot_lookup.get((job.id, skill.id, export_date))
                            future = snapshot_lookup.get((job.id, skill.id, target_date))
                            if not current or not future:
                                missing_pairs += 1
                                continue
                            delta_score = _compute_silver_delta_score(current, future)
                            rows.append(
                                {
                                    "job": job,
                                    "skill": skill,
                                    "snapshot": current,
                                    "delta_score": delta_score,
                                    "as_of_date": export_date,
                                }
                            )

                if not rows:
                    self.stdout.write(
                        self.style.ERROR(
                            "Aucun snapshot disponible pour construire les labels SILVER. "
                            "Lance d'abord generate_future_skill_snapshots pour T et T+H."
                        )
                    )
                    return

                self.stdout.write(
                    self.style.WARNING(
                        "Seuils SILVER (delta_score) calculés par date; "
                        "fallback par rang si nécessaire."
                    )
                )
                if missing_pairs:
                    self.stdout.write(
                        self.style.WARNING(
                            f"{missing_pairs} couples ignorés (snapshots manquants pour T ou T+H)."
                        )
                    )

                rows_by_date: dict[date, list] = {}
                for row in rows:
                    rows_by_date.setdefault(row["as_of_date"], []).append(row)

                for export_date, date_rows in rows_by_date.items():
                    low_threshold, high_threshold = _compute_silver_thresholds(
                        [row["delta_score"] for row in date_rows]
                    )
                    fallback_rank = low_threshold == high_threshold
                    if fallback_rank:
                        _assign_levels_by_rank(date_rows)

                    for row in date_rows:
                        snapshot = row["snapshot"]
                        window_snapshots = _get_window_snapshots(
                            snapshot_lookup,
                            row["job"].id,
                            row["skill"].id,
                            row["as_of_date"],
                            TIME_WINDOW_MONTHS,
                        )
                        time_features = compute_time_features(
                            window_snapshots,
                            expected_window_months=TIME_WINDOW_MONTHS,
                            as_of_date=row["as_of_date"],
                            horizon_months=horizon_months,
                        )
                        interaction_features = compute_interaction_features(row["job"], row["skill"])
                        level = row.get("level") or _assign_level_from_thresholds(
                            row["delta_score"], low_threshold, high_threshold
                        )
                        writer.writerow(
                            [
                                row["job"].name,
                                row["skill"].name,
                                row["skill"].category or "General",
                                row["job"].department or "General",
                                row["as_of_date"].isoformat(),
                                horizon_months,
                                label_provenance,
                                f"{snapshot.trend_score:.3f}",
                                f"{snapshot.internal_usage:.3f}",
                                f"{snapshot.training_requests:.3f}",
                                f"{snapshot.scarcity_index:.3f}",
                                f"{snapshot.hiring_difficulty:.3f}",
                                f"{snapshot.avg_salary_k:.2f}",
                                f"{snapshot.economic_indicator:.3f}",
                                f"{time_features['trend_momentum']:.4f}",
                                f"{time_features['trend_acceleration']:.4f}",
                                f"{time_features['trend_volatility']:.4f}",
                                f"{time_features['trend_persistence']:.4f}",
                                f"{time_features['internal_usage_momentum']:.4f}",
                                f"{time_features['training_requests_momentum']:.4f}",
                                f"{time_features['internal_usage_lag_1']:.4f}",
                                f"{time_features['internal_usage_lag_2']:.4f}",
                                f"{time_features['internal_usage_roll_mean_3']:.4f}",
                                f"{time_features['training_requests_lag_1']:.4f}",
                                f"{time_features['training_requests_lag_2']:.4f}",
                                f"{time_features['training_requests_roll_mean_3']:.4f}",
                                f"{time_features['economic_indicator_lag_1']:.4f}",
                                f"{time_features['economic_indicator_lag_2']:.4f}",
                                f"{time_features['economic_indicator_roll_mean_3']:.4f}",
                                f"{time_features['trend_stability_flag']:.4f}",
                                f"{time_features['internal_usage_stability_flag']:.4f}",
                                f"{time_features['training_requests_stability_flag']:.4f}",
                                f"{time_features['data_quality_window_coverage']:.4f}",
                                f"{time_features['data_quality_missing_flag']:.4f}",
                                f"{time_features['data_quality_stale_flag']:.4f}",
                                f"{time_features['data_quality_low_sample_flag']:.4f}",
                                f"{time_features['forecast_trend_score']:.4f}",
                                f"{time_features['forecast_internal_usage']:.4f}",
                                f"{time_features['forecast_training_requests']:.4f}",
                                f"{time_features['forecast_need_score']:.2f}",
                                f"{interaction_features['is_it_department']:.4f}",
                                f"{interaction_features['is_senior_role']:.4f}",
                                f"{interaction_features['is_technical_skill']:.4f}",
                                f"{interaction_features['dept_skill_alignment']:.4f}",
                                level,
                            ]
                        )
                        row_count += 1
            elif label_provenance == "GOLD":
                gold_labels = FutureSkillLabel.objects.filter(
                    as_of_date__in=export_dates,
                    horizon_months=horizon_months,
                ).select_related("job_role", "skill")

                if not gold_labels.exists():
                    self.stdout.write(
                        self.style.ERROR(
                            "Aucun label GOLD trouvé pour les dates/horizon demandés. "
                            "Renseigne FutureSkillLabel avant d'exporter."
                        )
                    )
                    return

                window_dates = {
                    add_months(export_date, -offset)
                    for export_date in export_dates
                    for offset in range(TIME_WINDOW_MONTHS)
                }
                snapshots = FutureSkillSnapshot.objects.filter(
                    as_of_date__in=list(set(export_dates) | window_dates),
                    job_role__in=job_roles,
                    skill__in=skills,
                )
                snapshot_lookup = {
                    (snapshot.job_role_id, snapshot.skill_id, snapshot.as_of_date): snapshot for snapshot in snapshots
                }

                missing_snapshots = 0
                for label in gold_labels:
                    snapshot = snapshot_lookup.get((label.job_role_id, label.skill_id, label.as_of_date))
                    if not snapshot:
                        missing_snapshots += 1
                        continue

                    window_snapshots = _get_window_snapshots(
                        snapshot_lookup,
                        label.job_role_id,
                        label.skill_id,
                        label.as_of_date,
                        TIME_WINDOW_MONTHS,
                    )
                    time_features = compute_time_features(
                        window_snapshots,
                        expected_window_months=TIME_WINDOW_MONTHS,
                        as_of_date=label.as_of_date,
                        horizon_months=horizon_months,
                    )
                    interaction_features = compute_interaction_features(label.job_role, label.skill)

                    writer.writerow(
                        [
                            label.job_role.name,
                            label.skill.name,
                            label.skill.category or "General",
                            label.job_role.department or "General",
                            label.as_of_date.isoformat(),
                            horizon_months,
                            label.provenance or label_provenance,
                            f"{snapshot.trend_score:.3f}",
                            f"{snapshot.internal_usage:.3f}",
                            f"{snapshot.training_requests:.3f}",
                            f"{snapshot.scarcity_index:.3f}",
                            f"{snapshot.hiring_difficulty:.3f}",
                            f"{snapshot.avg_salary_k:.2f}",
                            f"{snapshot.economic_indicator:.3f}",
                            f"{time_features['trend_momentum']:.4f}",
                            f"{time_features['trend_acceleration']:.4f}",
                            f"{time_features['trend_volatility']:.4f}",
                            f"{time_features['trend_persistence']:.4f}",
                            f"{time_features['internal_usage_momentum']:.4f}",
                            f"{time_features['training_requests_momentum']:.4f}",
                            f"{time_features['internal_usage_lag_1']:.4f}",
                            f"{time_features['internal_usage_lag_2']:.4f}",
                            f"{time_features['internal_usage_roll_mean_3']:.4f}",
                            f"{time_features['training_requests_lag_1']:.4f}",
                            f"{time_features['training_requests_lag_2']:.4f}",
                            f"{time_features['training_requests_roll_mean_3']:.4f}",
                            f"{time_features['economic_indicator_lag_1']:.4f}",
                            f"{time_features['economic_indicator_lag_2']:.4f}",
                            f"{time_features['economic_indicator_roll_mean_3']:.4f}",
                            f"{time_features['trend_stability_flag']:.4f}",
                            f"{time_features['internal_usage_stability_flag']:.4f}",
                            f"{time_features['training_requests_stability_flag']:.4f}",
                            f"{time_features['data_quality_window_coverage']:.4f}",
                            f"{time_features['data_quality_missing_flag']:.4f}",
                            f"{time_features['data_quality_stale_flag']:.4f}",
                            f"{time_features['data_quality_low_sample_flag']:.4f}",
                            f"{time_features['forecast_trend_score']:.4f}",
                            f"{time_features['forecast_internal_usage']:.4f}",
                            f"{time_features['forecast_training_requests']:.4f}",
                            f"{time_features['forecast_need_score']:.2f}",
                            f"{interaction_features['is_it_department']:.4f}",
                            f"{interaction_features['is_senior_role']:.4f}",
                            f"{interaction_features['is_technical_skill']:.4f}",
                            f"{interaction_features['dept_skill_alignment']:.4f}",
                            label.level,
                        ]
                    )
                    row_count += 1

                if missing_snapshots:
                    self.stdout.write(
                        self.style.WARNING(
                            f"{missing_snapshots} labels GOLD ignorés (snapshots manquants)."
                        )
                    )

            else:
                # Générer une ligne pour chaque couple (JobRole, Skill)
                for export_date in export_dates:
                    for job in job_roles:
                        for skill in skills:
                            trend_score = get_market_trend_for_context(job, skill, as_of_date=export_date)
                            internal_usage = _estimate_internal_usage(job, skill)
                            training_requests = _estimate_training_requests(job, skill)
                            scarcity_index = estimate_scarcity_index(
                                job_role=job,
                                skill=skill,
                                internal_usage=internal_usage,
                            )

                            hiring_difficulty = estimate_hiring_difficulty(job, skill, scarcity_index)
                            avg_salary = estimate_avg_salary(job, skill, hiring_difficulty)
                            economic_indicator = get_economic_indicator(job, as_of_date=export_date)

                            level, _score_0_100 = calculate_level(
                                trend_score=trend_score,
                                internal_usage=internal_usage,
                                training_requests=training_requests,
                            )

                            if level == "MEDIUM" and scarcity_index > 0.7 and hiring_difficulty > 0.7:
                                level = "HIGH"
                            elif level == "LOW" and scarcity_index > 0.6 and trend_score > 0.6:
                                level = "MEDIUM"

                            time_features = compute_time_features(
                                [],
                                expected_window_months=TIME_WINDOW_MONTHS,
                                as_of_date=export_date,
                                horizon_months=horizon_months,
                            )
                            interaction_features = compute_interaction_features(job, skill)

                            writer.writerow(
                                [
                                    job.name,
                                    skill.name,
                                    skill.category or "General",
                                    job.department or "General",
                                    export_date.isoformat(),
                                    horizon_months,
                                    label_provenance,
                                    f"{trend_score:.3f}",
                                    f"{internal_usage:.3f}",
                                    f"{training_requests:.3f}",
                                    f"{scarcity_index:.3f}",
                                    f"{hiring_difficulty:.3f}",
                                    f"{avg_salary:.2f}",
                                    f"{economic_indicator:.3f}",
                                    f"{time_features['trend_momentum']:.4f}",
                                    f"{time_features['trend_acceleration']:.4f}",
                                    f"{time_features['trend_volatility']:.4f}",
                                    f"{time_features['trend_persistence']:.4f}",
                                    f"{time_features['internal_usage_momentum']:.4f}",
                                    f"{time_features['training_requests_momentum']:.4f}",
                                    f"{time_features['internal_usage_lag_1']:.4f}",
                                    f"{time_features['internal_usage_lag_2']:.4f}",
                                    f"{time_features['internal_usage_roll_mean_3']:.4f}",
                                    f"{time_features['training_requests_lag_1']:.4f}",
                                    f"{time_features['training_requests_lag_2']:.4f}",
                                    f"{time_features['training_requests_roll_mean_3']:.4f}",
                                    f"{time_features['economic_indicator_lag_1']:.4f}",
                                    f"{time_features['economic_indicator_lag_2']:.4f}",
                                    f"{time_features['economic_indicator_roll_mean_3']:.4f}",
                                    f"{time_features['trend_stability_flag']:.4f}",
                                    f"{time_features['internal_usage_stability_flag']:.4f}",
                                    f"{time_features['training_requests_stability_flag']:.4f}",
                                    f"{time_features['data_quality_window_coverage']:.4f}",
                                    f"{time_features['data_quality_missing_flag']:.4f}",
                                    f"{time_features['data_quality_stale_flag']:.4f}",
                                    f"{time_features['data_quality_low_sample_flag']:.4f}",
                                    f"{time_features['forecast_trend_score']:.4f}",
                                    f"{time_features['forecast_internal_usage']:.4f}",
                                    f"{time_features['forecast_training_requests']:.4f}",
                                    f"{time_features['forecast_need_score']:.2f}",
                                    f"{interaction_features['is_it_department']:.4f}",
                                    f"{interaction_features['is_senior_role']:.4f}",
                                    f"{interaction_features['is_technical_skill']:.4f}",
                                    f"{interaction_features['dept_skill_alignment']:.4f}",
                                    level,  # LOW / MEDIUM / HIGH
                                ]
                            )
                            row_count += 1

        self.stdout.write(self.style.SUCCESS(f"Export terminé. {row_count} lignes écrites dans {output_path}."))

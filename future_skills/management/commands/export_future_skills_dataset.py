# future_skills/management/commands/export_future_skills_dataset.py

import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from future_skills.models import JobRole, Skill
from future_skills.services.prediction_engine import (
    _find_relevant_trend,
    _estimate_internal_usage,
    _estimate_training_requests,
    calculate_level,
)


def _estimate_scarcity_index(job_role, skill, internal_usage: float) -> float:
    """
    Indice très simple de rareté (0-1).
    Plus l'utilisation interne est faible, plus la compétence est considérée rare.

    1.0  → très rare
    0.0  → pas rare
    """
    # Ici on part sur une logique simple, tu pourras l'améliorer plus tard
    scarcity = 1.0 - internal_usage
    # clamp entre 0 et 1
    return max(0.0, min(1.0, scarcity))


class Command(BaseCommand):
    help = (
        "Exporte un dataset CSV pour le futur modèle de ML du Module 3 "
        "à partir des données (JobRole, Skill) et du moteur de règles actuel."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Chemin du fichier CSV de sortie (par défaut: BASE_DIR/ml/future_skills_dataset.csv).",
        )

    def handle(self, *args, **options):
        # Déterminer le chemin de sortie
        output_path = options["output"]
        if not output_path:
            ml_dir = os.path.join(settings.BASE_DIR, "ml")
            os.makedirs(ml_dir, exist_ok=True)
            output_path = os.path.join(ml_dir, "future_skills_dataset.csv")

        self.stdout.write(self.style.WARNING(f"Export du dataset vers : {output_path}"))

        # Préparer les données
        job_roles = JobRole.objects.all()
        skills = Skill.objects.all()

        if not job_roles.exists() or not skills.exists():
            self.stdout.write(
                self.style.ERROR(
                    "Aucun JobRole ou Skill trouvé en base. "
                    "Peuple d'abord la base avec des données de démo."
                )
            )
            return

        # Ouvrir le CSV et écrire l'en-tête
        with open(output_path, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "job_role_name",
                    "skill_name",
                    "trend_score",
                    "internal_usage",
                    "training_requests",
                    "scarcity_index",
                    "future_need_level",
                ]
            )

            row_count = 0

            # Générer une ligne pour chaque couple (JobRole, Skill)
            for job in job_roles:
                for skill in skills:
                    trend_score = _find_relevant_trend(job, skill)
                    internal_usage = _estimate_internal_usage(job, skill)
                    training_requests = _estimate_training_requests(job, skill)
                    scarcity_index = _estimate_scarcity_index(
                        job_role=job,
                        skill=skill,
                        internal_usage=internal_usage,
                    )

                    # Utiliser le moteur de règles actuel pour générer le label (future_need_level)
                    level, _score_0_100 = calculate_level(
                        trend_score=trend_score,
                        internal_usage=internal_usage,
                        training_requests=training_requests,
                    )

                    writer.writerow(
                        [
                            job.name,
                            skill.name,
                            f"{trend_score:.3f}",
                            f"{internal_usage:.3f}",
                            f"{training_requests:.3f}",
                            f"{scarcity_index:.3f}",
                            level,  # LOW / MEDIUM / HIGH
                        ]
                    )
                    row_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Export terminé. {row_count} lignes écrites dans {output_path}."
            )
        )

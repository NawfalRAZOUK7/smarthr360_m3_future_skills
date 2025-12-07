# future_skills/management/commands/export_future_skills_dataset.py

import csv
import os
import random
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from future_skills.models import EconomicReport, JobRole, MarketTrend, Skill
from future_skills.services.prediction_engine import (
    _estimate_internal_usage,
    _estimate_training_requests,
    calculate_level,
)

# Constants for skill classification
TECHNICAL_KEYWORDS = [
    "python",
    "ia",
    "data",
    "cloud",
    "devops",
    "machine learning",
    "blockchain",
    "cybersecurity",
    "kubernetes",
    "java",
    "javascript",
    "aws",
    "azure",
    "docker",
    "sql",
    "nosql",
]

SENIOR_KEYWORDS = ["senior", "lead", "manager", "director", "chief", "head"]

IT_DEPARTMENTS = ["IT", "Tech", "Data", "Engineering", "R&D"]


def _estimate_scarcity_index(job_role, skill, internal_usage: float) -> float:
    """
    Indice de rareté (0-1) basé sur plusieurs facteurs.

    1.0  → très rare
    0.0  → pas rare

    Facteurs considérés:
    - Faible utilisation interne → plus rare
    - Compétences techniques avancées → plus rare
    - Départements IT → compétences plus spécialisées
    """
    # Base scarcity from internal usage
    base_scarcity = 1.0 - internal_usage

    # Bonus for technical/specialized skills
    skill_name_lower = skill.name.lower()
    is_technical = any(keyword in skill_name_lower for keyword in TECHNICAL_KEYWORDS)

    # Bonus for IT departments
    is_it_dept = any(dept in (job_role.department or "") for dept in IT_DEPARTMENTS)

    # Calculate adjusted scarcity
    scarcity = base_scarcity
    if is_technical:
        scarcity = min(1.0, scarcity + 0.15)
    if is_it_dept:
        scarcity = min(1.0, scarcity + 0.10)

    return max(0.0, min(1.0, scarcity))


def _estimate_hiring_difficulty(job_role, skill, scarcity_index: float) -> float:
    """
    Estime la difficulté de recrutement (0-1) pour un couple (job_role, skill).

    Basé sur:
    - Indice de rareté de la compétence
    - Compétences techniques → plus difficile à recruter
    - Postes seniors/managers → pool de candidats plus restreint
    """
    # Base difficulty from scarcity
    difficulty = scarcity_index

    # Technical skills are harder to recruit
    skill_name_lower = skill.name.lower()
    is_technical = any(keyword in skill_name_lower for keyword in TECHNICAL_KEYWORDS)

    # Senior/manager positions are harder to fill
    job_name_lower = job_role.name.lower()
    is_senior = any(keyword in job_name_lower for keyword in SENIOR_KEYWORDS)

    if is_technical:
        difficulty = min(1.0, difficulty + 0.20)
    if is_senior:
        difficulty = min(1.0, difficulty + 0.15)

    # Add some realistic randomness (±10%)
    difficulty = difficulty * random.uniform(0.90, 1.10)

    return max(0.0, min(1.0, difficulty))


def _estimate_avg_salary(job_role, skill, hiring_difficulty: float) -> float:
    """
    Estime le salaire moyen en K€/an pour un profil (job_role, skill).

    Basé sur:
    - Difficulté de recrutement
    - Type de poste (junior/senior, technique/non-technique)
    - Département
    """
    # Base salary by department
    dept = job_role.department or "Other"
    base_salaries = {
        "IT": 50.0,
        "Tech": 50.0,
        "Data": 55.0,
        "Engineering": 52.0,
        "RH": 40.0,
        "Finance": 48.0,
        "Marketing": 42.0,
        "Sales": 45.0,
    }
    base_salary = base_salaries.get(dept, 40.0)

    # Multiplier for senior positions
    job_name_lower = job_role.name.lower()
    is_senior = any(keyword in job_name_lower for keyword in SENIOR_KEYWORDS)

    if is_senior:
        base_salary *= 1.5

    # Multiplier for technical skills
    skill_name_lower = skill.name.lower()
    is_technical = any(keyword in skill_name_lower for keyword in TECHNICAL_KEYWORDS)

    if is_technical:
        base_salary *= 1.2

    # Adjust by hiring difficulty (scarce skills command higher salaries)
    base_salary = base_salary * (1.0 + hiring_difficulty * 0.4)

    # Add realistic randomness (±15%)
    salary = base_salary * random.uniform(0.85, 1.15)

    return round(salary, 2)


def _get_market_trend_for_context(job_role, skill) -> float:
    """
    Récupère le trend_score le plus pertinent pour le contexte (job_role, skill).

    Priorise:
    1. Trends matching skill category or job department
    2. Recent trends (latest year)
    3. Tech sector as default
    """
    # Try to match by job department first
    if job_role.department:
        trend = (
            MarketTrend.objects.filter(sector__icontains=job_role.department)
            .order_by("-year", "-trend_score")
            .first()
        )
        if trend:
            return max(0.0, min(1.0, float(trend.trend_score)))

    # Try to match by skill category
    if skill.category:
        trend = (
            MarketTrend.objects.filter(sector__icontains=skill.category)
            .order_by("-year", "-trend_score")
            .first()
        )
        if trend:
            return max(0.0, min(1.0, float(trend.trend_score)))

    # Default to Tech sector or most recent trend
    trend = (
        MarketTrend.objects.filter(sector__iexact="Tech")
        .order_by("-year", "-trend_score")
        .first()
    ) or MarketTrend.objects.order_by("-year", "-trend_score").first()

    if trend:
        return max(0.0, min(1.0, float(trend.trend_score)))

    return 0.5  # neutral default


def _get_economic_indicator(job_role) -> float:
    """
    Récupère un indicateur économique pertinent pour le contexte.

    Retourne une valeur normalisée (0-1) basée sur les rapports économiques.
    """
    # Try to find relevant economic report
    dept = job_role.department or "Tech"

    report = (
        EconomicReport.objects.filter(sector__icontains=dept).order_by("-year").first()
    )

    if report:
        # Normalize value (assuming values are in reasonable ranges)
        # This is a simplification - you might need different normalization per indicator type
        normalized = report.value / 100.0  # Assuming percentages
        return max(0.0, min(1.0, normalized))

    return 0.5  # neutral default


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
            help="Chemin du fichier CSV de sortie (par défaut: BASE_DIR/artifacts/datasets/future_skills_dataset.csv).",
        )

    def handle(self, *args, **options):
        # Set random seed for reproducibility
        random.seed(42)

        # Déterminer le chemin de sortie
        output_path = options["output"]
        if not output_path:
            ml_data_dir = settings.ML_DATASETS_DIR
            ml_data_dir.mkdir(parents=True, exist_ok=True)
            output_path = ml_data_dir / "future_skills_dataset.csv"
        else:
            output_path = Path(output_path)

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

        # Ouvrir le CSV et écrire l'en-tête avec les nouvelles colonnes
        with open(output_path, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "job_role_name",
                    "skill_name",
                    "skill_category",
                    "job_department",
                    "trend_score",
                    "internal_usage",
                    "training_requests",
                    "scarcity_index",
                    "hiring_difficulty",
                    "avg_salary_k",
                    "economic_indicator",
                    "future_need_level",
                ]
            )

            row_count = 0

            # Générer une ligne pour chaque couple (JobRole, Skill)
            for job in job_roles:
                for skill in skills:
                    # Use enhanced trend calculation
                    trend_score = _get_market_trend_for_context(job, skill)
                    internal_usage = _estimate_internal_usage(job, skill)
                    training_requests = _estimate_training_requests(job, skill)
                    scarcity_index = _estimate_scarcity_index(
                        job_role=job,
                        skill=skill,
                        internal_usage=internal_usage,
                    )

                    # New features
                    hiring_difficulty = _estimate_hiring_difficulty(
                        job, skill, scarcity_index
                    )
                    avg_salary = _estimate_avg_salary(job, skill, hiring_difficulty)
                    economic_indicator = _get_economic_indicator(job)

                    # Enhanced future_need_level calculation using more factors
                    # We'll use the enhanced trend_score and combine it with scarcity
                    level, _score_0_100 = calculate_level(
                        trend_score=trend_score,
                        internal_usage=internal_usage,
                        training_requests=training_requests,
                    )

                    # Optionally upgrade level if scarcity + hiring difficulty is very high
                    if (
                        level == "MEDIUM"
                        and scarcity_index > 0.7
                        and hiring_difficulty > 0.7
                    ):
                        level = "HIGH"
                    elif level == "LOW" and scarcity_index > 0.6 and trend_score > 0.6:
                        level = "MEDIUM"

                    writer.writerow(
                        [
                            job.name,
                            skill.name,
                            skill.category or "General",
                            job.department or "General",
                            f"{trend_score:.3f}",
                            f"{internal_usage:.3f}",
                            f"{training_requests:.3f}",
                            f"{scarcity_index:.3f}",
                            f"{hiring_difficulty:.3f}",
                            f"{avg_salary:.2f}",
                            f"{economic_indicator:.3f}",
                            level,  # LOW / MEDIUM / HIGH
                        ]
                    )
                    row_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Export terminé. {row_count} lignes écrites dans {output_path}."
            )
        )

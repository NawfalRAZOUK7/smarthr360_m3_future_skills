# future_skills/services/prediction_engine.py

from typing import Tuple

from future_skills.models import (
    Skill,
    JobRole,
    MarketTrend,
    FutureSkillPrediction,
    PredictionRun,
)


def normalize_training_requests(training_requests: int, max_requests: int = 10) -> float:
    """
    Normalise le nombre de demandes de formation sur [0, 1].
    Pour l'instant, on utilisera des valeurs simples / simulées.
    """
    if training_requests <= 0:
        return 0.0
    value = training_requests / max_requests
    return 1.0 if value > 1.0 else value


def calculate_level(
    trend_score: float,
    internal_usage: float,
    training_requests: int,
) -> Tuple[str, float]:
    """
    Calcule un niveau LOW / MEDIUM / HIGH + un score (0–100) à partir
    de trois facteurs simples :
      - trend_score : intensité de la tendance marché (0–1)
      - internal_usage : niveau d'utilisation interne (0–1)
      - training_requests : nb. de demandes de formation (0+)

    Ce n'est PAS encore du ML, mais un moteur de règles structuré.
    """

    # Sécurité : clamp sur [0, 1]
    trend_score = max(0.0, min(1.0, trend_score))
    internal_usage = max(0.0, min(1.0, internal_usage))
    training_norm = normalize_training_requests(training_requests)

    # Pondération simple (tu pourras la documenter dans ton rapport)
    raw_score = (
        0.5 * trend_score
        + 0.3 * internal_usage
        + 0.2 * training_norm
    )

    # Convertir en score 0–100 pour stocker dans le modèle
    score_0_100 = round(raw_score * 100, 1)

    if raw_score >= 0.7:
        level = FutureSkillPrediction.LEVEL_HIGH
    elif raw_score >= 0.4:
        level = FutureSkillPrediction.LEVEL_MEDIUM
    else:
        level = FutureSkillPrediction.LEVEL_LOW

    return level, score_0_100


def _estimate_internal_usage(job_role: JobRole, skill: Skill) -> float:
    """
    Fonction utilitaire pour estimer l'utilisation interne d'une compétence
    par un métier. Pour l'instant : heuristiques simples / codées en dur.

    Tu pourras plus tard connecter cela à de vraies données (logs, évaluations, etc.).
    """

    # Exemple d'heuristiques très simples :
    if job_role.department == "IT" and skill.category == "Technique":
        return 0.8
    if job_role.department == "RH" and skill.category == "Soft Skill":
        return 0.7

    # Valeur par défaut
    return 0.5


def _estimate_training_requests(job_role: JobRole, skill: Skill) -> int:
    """
    Estime grossièrement le nombre de demandes de formation.
    Pour l'instant, on simule quelques variations.
    """

    # Exemples de règles totalement simplifiées :
    if skill.name.lower() in {"python", "analyse de données", "data"}:
        return 8  # très demandé
    if "projet" in skill.name.lower():
        return 5

    # Valeur par défaut
    return 3


def _find_relevant_trend(job_role: JobRole, skill: Skill) -> float:
    """
    Trouve un score de tendance 'logiquement' lié au métier / à la compétence.
    Pour l'instant, on utilise des règles simples :
      - on essaie de matcher sur le département ou la catégorie,
      - sinon on prend la tendance la plus forte.
    """

    # Essayer de matcher secteur ~ département ou catégorie
    queryset = MarketTrend.objects.all()

    # Match par secteur sur le département
    if job_role.department:
        sector_match = queryset.filter(sector__iexact=job_role.department)
        if sector_match.exists():
            return sector_match.order_by("-trend_score").first().trend_score

    # Match par secteur sur la catégorie de la compétence
    if skill.category:
        sector_match = queryset.filter(sector__iexact=skill.category)
        if sector_match.exists():
            return sector_match.order_by("-trend_score").first().trend_score

    # Fallback : on prend la tendance la plus forte globale, sinon 0.5
    strongest = queryset.order_by("-trend_score").first()
    if strongest:
        return strongest.trend_score

    return 0.5  # valeur par défaut si aucune tendance n'est présente


def recalculate_predictions(horizon_years: int = 5) -> int:
    """
    Recalcule toutes les prédictions FutureSkillPrediction pour tous les
    couples (JobRole, Skill) en utilisant le moteur de règles simple.

    Retourne le nombre total de prédictions créées / mises à jour.
    """

    total_predictions = 0

    job_roles = JobRole.objects.all()
    skills = Skill.objects.all()

    for job in job_roles:
        for skill in skills:
            trend_score = _find_relevant_trend(job, skill)
            internal_usage = _estimate_internal_usage(job, skill)
            training_requests = _estimate_training_requests(job, skill)

            level, score_0_100 = calculate_level(
                trend_score=trend_score,
                internal_usage=internal_usage,
                training_requests=training_requests,
            )

            rationale = (
                f"Prédiction basée sur les tendances marché (score={trend_score:.2f}), "
                f"l'utilisation interne estimée (score={internal_usage:.2f}) "
                f"et les demandes de formation (~{training_requests})."
            )

            FutureSkillPrediction.objects.update_or_create(
                job_role=job,
                skill=skill,
                horizon_years=horizon_years,
                defaults={
                    "score": score_0_100,
                    "level": level,
                    "rationale": rationale,
                },
            )
            total_predictions += 1

    PredictionRun.objects.create(
        description=f"Recalcul des prédictions à horizon {horizon_years} ans (moteur de règles).",
        total_predictions=total_predictions,
    )

    return total_predictions

# future_skills/services/recommendation_engine.py

from typing import Optional

from future_skills.models import (
    FutureSkillPrediction,
    HRInvestmentRecommendation,
    JobRole,
    Skill,
)


def _decide_action(job_role: Optional[JobRole], skill: Skill) -> str:
    """
    Décide l'action RH recommandée en fonction du type de compétence
    et éventuellement du département du rôle.
    """
    # Exemple d'heuristiques très simples :
    # - Compétence technique & rôle IT → plutôt formation
    # - Compétence technique & rôle non IT → recrutement
    # - Soft skill → reskilling / formation interne

    name_lower = (skill.name or "").lower()
    category = (skill.category or "").lower()
    dept = (job_role.department or "").lower() if job_role and job_role.department else ""

    # Cas soft skills
    if "soft" in category or "projet" in name_lower or "communication" in name_lower:
        return HRInvestmentRecommendation.ACTION_RESKILL

    # Cas techniques pour IT
    if dept == "it" and category == "technique":
        return HRInvestmentRecommendation.ACTION_TRAINING

    # Par défaut, on considère qu'il faut recruter sur une compétence rare
    return HRInvestmentRecommendation.ACTION_HIRING


def generate_recommendations_from_predictions(horizon_years: int = 5) -> int:
    """
    Génère des recommandations RH à partir des prédictions existantes
    pour un horizon donné.

    Règles simples :
      - On ne considère que les prédictions avec level = HIGH.
      - On crée/MAJ une HRInvestmentRecommendation par couple (job_role, skill, horizon).
    """
    total = 0

    high_predictions = FutureSkillPrediction.objects.filter(
        horizon_years=horizon_years,
        level=FutureSkillPrediction.LEVEL_HIGH,
    ).select_related("job_role", "skill")

    for prediction in high_predictions:
        job = prediction.job_role
        skill = prediction.skill

        action = _decide_action(job, skill)

        # Exemple très simple : budget_hint = score * 10 (à adapter selon ton contexte)
        budget_hint = round(prediction.score * 10, 1)

        rationale = (
            f"Basée sur un score de {prediction.score} et un niveau HIGH pour la compétence "
            f"'{skill.name}' sur le rôle '{job.name if job else 'Global'}', "
            f"il est recommandé de {action} à horizon {horizon_years} ans."
        )

        # On crée ou met à jour la recommandation
        obj, created = HRInvestmentRecommendation.objects.update_or_create(
            job_role=job,
            skill=skill,
            horizon_years=horizon_years,
            defaults={
                "priority_level": HRInvestmentRecommendation.PRIORITY_HIGH,
                "recommended_action": action,
                "budget_hint": budget_hint,
                "rationale": rationale,
            },
        )

        total += 1

    return total

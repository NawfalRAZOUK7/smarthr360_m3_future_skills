"""Recommendation engine for HR Investment (Module 3).

This module generates HRInvestmentRecommendation objects from
FutureSkillPrediction entries.

Key points:
- Only HIGH predictions are used in the normal path.
- If no HIGH prediction exists for a given horizon, a small fallback
  strategy selects the top-scoring predictions to still provide
  recommendations (useful for demos / very small datasets).
- Priority level and recommended action are derived from the
  prediction level and basic heuristics on job_role / skill.

Public API:
- generate_recommendations_from_predictions(horizon_years: int = 5) -> int

Internal helpers:
- _choose_priority_from_level(level: str) -> str
- _choose_recommended_action(job_role, skill) -> str
- _decide_action(job_role, skill) -> str (backward-compatible alias)
"""

from __future__ import annotations

import logging

from future_skills.models import FutureSkillPrediction, HRInvestmentRecommendation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _choose_priority_from_level(level: str) -> str:
    """Map prediction level (LOW/MEDIUM/HIGH) to HR priority.

    This is intentionally simple and transparent so it can be
    documented easily and, if needed, tuned later.
    """

    if level == FutureSkillPrediction.LEVEL_HIGH:
        return HRInvestmentRecommendation.PRIORITY_HIGH
    if level == FutureSkillPrediction.LEVEL_MEDIUM:
        return HRInvestmentRecommendation.PRIORITY_MEDIUM
    return HRInvestmentRecommendation.PRIORITY_LOW


def _choose_recommended_action(job_role, skill) -> str:
    """Very simple heuristic for the recommended HR action.

    Current rule (can be refined later):
      - If the department looks like HR or the skill category
        contains "soft" → TRAINING.
      - Otherwise → HIRING.
    """

    dept = (getattr(job_role, "department", None) or "").lower()
    category = (getattr(skill, "category", None) or "").lower()

    if "rh" in dept or "soft" in category:
        return HRInvestmentRecommendation.ACTION_TRAINING

    # Default: we consider hiring as the main lever
    return HRInvestmentRecommendation.ACTION_HIRING


def _decide_action(job_role, skill) -> str:
    """Backward-compatible alias used in earlier drafts.

    Some code/tests might still refer to `_decide_action`, so we keep it
    as a thin wrapper around `_choose_recommended_action`.
    """

    return _choose_recommended_action(job_role, skill)


# ---------------------------------------------------------------------------
# Core service
# ---------------------------------------------------------------------------


def generate_recommendations_from_predictions(horizon_years: int = 5) -> int:
    """Generate HRInvestmentRecommendation objects from predictions.

    Rules:
      1. Filter FutureSkillPrediction on the given horizon_years.
      2. Normal case: only consider predictions with level = HIGH.
      3. If there is no HIGH at all for this horizon:
         - Fallback: take the top scoring predictions so that the
           system can still show something meaningful (useful for
           demos / very small synthetic datasets).

    Returns the number of recommendations created/updated.
    """

    logger.info("========================================")
    logger.info("📊 Starting recommendation generation...")
    logger.info("Horizon: %s years", horizon_years)

    queryset = FutureSkillPrediction.objects.filter(horizon_years=horizon_years)
    total_available = queryset.count()
    logger.info("Total predictions available: %s", total_available)

    # Normal case: use only HIGH predictions
    high_predictions = queryset.filter(level=FutureSkillPrediction.LEVEL_HIGH)
    high_count = high_predictions.count()

    if high_predictions.exists():
        target_predictions = high_predictions
        logger.info(
            "✅ Found %s HIGH level predictions (normal mode)",
            high_count,
        )
        logger.info("Generating recommendations from HIGH predictions only")
    else:
        # Fallback: if no HIGH, pick the top-scoring predictions.
        # This does NOT change the behaviour when HIGH exists,
        # thus stays compatible with the tests that expect only HIGH
        # to be used in the normal path.
        target_predictions = queryset.order_by("-score")[:3]
        fallback_count = target_predictions.count()
        logger.warning(
            "⚠️  No HIGH predictions found for horizon=%s years",
            horizon_years,
        )
        logger.warning(
            "Fallback mode activated: using top %s predictions by score",
            fallback_count,
        )

    total = 0
    priority_stats = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    action_stats = {"HIRING": 0, "TRAINING": 0}

    for prediction in target_predictions:
        job_role = prediction.job_role
        skill = prediction.skill

        priority = _choose_priority_from_level(prediction.level)
        action = _choose_recommended_action(job_role, skill)

        # Track statistics
        priority_stats[priority] = priority_stats.get(priority, 0) + 1
        action_stats[action] = action_stats.get(action, 0) + 1

        rationale = prediction.rationale or (
            f"Basée sur un score de {prediction.score} et un niveau {prediction.level}, "
            f"il est recommandé de {action} pour {skill.name} à horizon {horizon_years} ans."
        )

        obj, created = HRInvestmentRecommendation.objects.update_or_create(
            skill=skill,
            job_role=job_role,
            horizon_years=horizon_years,
            defaults={
                "priority_level": priority,
                "recommended_action": action,
                "budget_hint": None,
                "rationale": rationale,
            },
        )
        total += 1

        logger.debug(
            "Recommendation %s for skill=%s, job_role=%s, priority=%s, action=%s (created=%s)",
            obj.id,
            skill.name,
            job_role.name if job_role else None,
            priority,
            action,
            created,
        )

    logger.info("✅ Recommendation generation completed successfully")
    logger.info("Total recommendations created/updated: %s", total)
    logger.info(
        "Priority distribution: HIGH=%s, MEDIUM=%s, LOW=%s",
        priority_stats.get("HIGH", 0),
        priority_stats.get("MEDIUM", 0),
        priority_stats.get("LOW", 0),
    )
    logger.info(
        "Action distribution: HIRING=%s, TRAINING=%s",
        action_stats.get("HIRING", 0),
        action_stats.get("TRAINING", 0),
    )
    logger.info("========================================")

    return total

"""Prediction engine for Future Skills (Module 3).

This module provides:
- A simple rule-based engine (Phase 1).
- Optional integration with a trained ML model (Phase 2).
- A recalculate_predictions(...) function used by management commands
  and API views to refresh FutureSkillPrediction records.

⚠️ IMPORTANT:
- The public API of this module is recalculate_predictions(...) and
  calculate_level(...). Existing callers/tests should continue to work.
"""

from __future__ import annotations

import logging
from typing import Tuple, Dict, Any

from django.conf import settings

from future_skills.models import (
    JobRole,
    Skill,
    MarketTrend,
    FutureSkillPrediction,
    PredictionRun,
)
from future_skills.ml_model import FutureSkillsModel

# Lazy import pour éviter erreur si SHAP pas installé
try:
    from future_skills.services.explanation_engine import ExplanationEngine
    EXPLANATION_ENGINE_AVAILABLE = True
except ImportError:
    EXPLANATION_ENGINE_AVAILABLE = False
    logger.warning(
        "ExplanationEngine non disponible. Les explications ne seront pas générées. "
        "Installez 'shap' pour activer cette fonctionnalité."
    )


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers for the rule-based engine
# ---------------------------------------------------------------------------


def _normalize_training_requests(training_requests: float, max_requests: float = 100.0) -> float:
    """Normalize training_requests to [0, 1].

    The max_requests is a soft upper bound; values above it are clipped.
    """

    if max_requests <= 0:
        return 0.0
    value = training_requests / max_requests
    return max(0.0, min(1.0, value))


def calculate_level(
    trend_score: float,
    internal_usage: float,
    training_requests: float,
) -> Tuple[str, float]:
    """Simple heuristic engine used in Phase 1.

    Returns (level, score_0_100) where:
    - level ∈ {"LOW", "MEDIUM", "HIGH"}
    - score_0_100 is a float in [0, 100].

    The logic is intentionally simple and transparent so it can be
    explained in documentation and compared to the ML model later.
    """

    # Clamp basic inputs to [0, 1] just in case
    trend_score = max(0.0, min(1.0, trend_score))
    internal_usage = max(0.0, min(1.0, internal_usage))
    training_norm = _normalize_training_requests(training_requests)

    # Weighted combination (these weights can be tuned/documented)
    score_0_1 = 0.5 * trend_score + 0.3 * internal_usage + 0.2 * training_norm

    # Map to discrete level
    if score_0_1 >= 0.7:
        level = "HIGH"
    elif score_0_1 >= 0.4:
        level = "MEDIUM"
    else:
        level = "LOW"

    score_0_100 = round(score_0_1 * 100.0, 2)
    return level, score_0_100


def _find_relevant_trend(job_role: JobRole, skill: Skill) -> float:
    """Return a trend_score in [0, 1] for the given (job_role, skill).

    Current implementation is intentionally simple: it tries to
    fetch a MarketTrend matching the job/skill context, otherwise
    falls back to a neutral value.
    """

    # This can be refined later (sector mapping, tech categories, etc.)
    trend = (
        MarketTrend.objects.filter(sector__iexact="Tech").order_by("-year").first()
        or MarketTrend.objects.order_by("-year").first()
    )
    if trend is None:
        return 0.5  # neutral default
    return max(0.0, min(1.0, float(trend.trend_score)))


def _estimate_internal_usage(job_role: JobRole, skill: Skill) -> float:
    """Estimate internal usage of a skill for a given job role.

    For now, this is a placeholder heuristic.
    It can later be replaced by real usage metrics.
    """

    # Example heuristic: managers use more transversal skills
    base = 0.6 if "manager" in job_role.name.lower() else 0.4
    return max(0.0, min(1.0, base))


def _estimate_training_requests(job_role: JobRole, skill: Skill) -> float:
    """Estimate how many training requests exist for this (job, skill).

    Placeholder for now; later it can be replaced by real stats.
    """

    # Example simple heuristic
    if "data" in skill.name.lower() or "ia" in skill.name.lower():
        return 40.0
    return 10.0


def _estimate_scarcity_index(job_role: JobRole, skill: Skill, internal_usage: float) -> float:
    """Very simple scarcity index based on internal usage.

    - Low internal usage → skill considered more rare (scarce).
    - Value clamped to [0, 1].
    """

    scarcity = 1.0 - internal_usage
    return max(0.0, min(1.0, scarcity))


# ---------------------------------------------------------------------------
# Core function: recalculate_predictions
# ---------------------------------------------------------------------------


def recalculate_predictions(
    horizon_years: int = 5,
    run_by=None,
    parameters: Dict[str, Any] | None = None,
    generate_explanations: bool = False,
) -> int:
    """Recalculate all FutureSkillPrediction entries for all (JobRole, Skill).

    Behaviour:
    - If settings.FUTURE_SKILLS_USE_ML is True and the ML model is available,
      use the trained ML pipeline (FutureSkillsModel) to predict (level, score).
    - Otherwise, fall back to the simple rule-based engine (calculate_level).

    A PredictionRun is created to trace:
    - which engine was used (rules_v1 vs ml_random_forest_v1)
    - the horizon_years
    - who triggered the run (run_by)
    - optional parameters (trigger = api/management_command, etc.).
    
    Args:
        horizon_years: Horizon de prédiction en années (défaut: 5)
        run_by: Utilisateur ayant déclenché le recalcul (optionnel)
        parameters: Paramètres additionnels (optionnel)
        generate_explanations: Si True, génère des explications SHAP/LIME (défaut: False)

    Returns the total number of predictions created/updated.
    """

    logger.info("========================================")
    logger.info("🚀 Starting prediction recalculation...")
    logger.info("Horizon: %s years | Triggered by: %s", horizon_years, run_by or "system")
    
    total_predictions = 0

    job_roles = JobRole.objects.all()
    skills = Skill.objects.all()
    
    logger.info("Dataset size: %s job roles × %s skills = %s combinations",
                job_roles.count(), skills.count(), job_roles.count() * skills.count())

    # Decide which engine to use
    use_ml_flag = getattr(settings, "FUTURE_SKILLS_USE_ML", False)
    ml_model = None
    use_ml_effective = False

    logger.info("Configuration: FUTURE_SKILLS_USE_ML=%s", use_ml_flag)
    
    if use_ml_flag:
        ml_model = FutureSkillsModel.instance()
        if ml_model.is_available():
            use_ml_effective = True
            logger.info("✅ ML model loaded and available for predictions")
        else:
            logger.warning(
                "⚠️  FUTURE_SKILLS_USE_ML=True but ML model is not available. "
                "Falling back to rule-based engine (rules_v1)."
            )
            logger.warning("Check that model file exists at: %s",
                          getattr(settings, "FUTURE_SKILLS_MODEL_PATH", "N/A"))
    else:
        logger.info("Using rule-based engine as per configuration")

    engine_label = "ml_random_forest_v1" if use_ml_effective else "rules_v1"
    logger.info("🔧 Engine selected: %s", engine_label)
    
    # Initialize explanation engine if requested and available
    explanation_engine = None
    if generate_explanations and use_ml_effective and EXPLANATION_ENGINE_AVAILABLE:
        try:
            explanation_engine = ExplanationEngine(ml_model)
            if explanation_engine.is_available():
                logger.info("✅ Explanation engine initialized (SHAP)")
            else:
                logger.warning("⚠️  Explanation engine not available, skipping explanations")
                explanation_engine = None
        except Exception as exc:
            logger.warning("⚠️  Failed to initialize explanation engine: %s", exc)
            explanation_engine = None
    elif generate_explanations and not use_ml_effective:
        logger.warning("⚠️  Explanations only available with ML model, skipping")
    elif generate_explanations and not EXPLANATION_ENGINE_AVAILABLE:
        logger.warning("⚠️  Explanation engine not installed, skipping")

    for job in job_roles:
        for skill in skills:
            trend_score = _find_relevant_trend(job, skill)
            internal_usage = _estimate_internal_usage(job, skill)
            training_requests = _estimate_training_requests(job, skill)
            scarcity_index = _estimate_scarcity_index(job, skill, internal_usage)

            if use_ml_effective:
                # Use the trained ML model
                level, score_0_100 = ml_model.predict_level(
                    job_role_name=job.name,
                    skill_name=skill.name,
                    trend_score=trend_score,
                    internal_usage=internal_usage,
                    training_requests=training_requests,
                    scarcity_index=scarcity_index,
                )
            else:
                # Fallback to rule-based engine
                level, score_0_100 = calculate_level(
                    trend_score=trend_score,
                    internal_usage=internal_usage,
                    training_requests=training_requests,
                )

            rationale = (
                f"Prédiction basée sur les tendances marché (score={trend_score:.2f}), "
                f"l'utilisation interne estimée (score={internal_usage:.2f}), "
                f"les demandes de formation (~{training_requests:.1f}) "
                f"et l'indice de rareté (~{scarcity_index:.2f}). "
                f"Moteur utilisé : {engine_label}."
            )
            
            # Generate explanation if requested and available
            explanation_data = None
            if explanation_engine is not None:
                try:
                    explanation_data = explanation_engine.generate_explanation(
                        job_role_name=job.name,
                        skill_name=skill.name,
                        trend_score=trend_score,
                        internal_usage=internal_usage,
                        training_requests=training_requests,
                        scarcity_index=scarcity_index,
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to generate explanation for %s × %s: %s",
                        job.name, skill.name, exc
                    )

            defaults = {
                "score": score_0_100,
                "level": level,
                "rationale": rationale,
            }
            
            if explanation_data is not None:
                defaults["explanation"] = explanation_data

            FutureSkillPrediction.objects.update_or_create(
                job_role=job,
                skill=skill,
                horizon_years=horizon_years,
                defaults=defaults,
            )
            total_predictions += 1

    # Build parameters for PredictionRun
    params: Dict[str, Any] = parameters.copy() if isinstance(parameters, dict) else {}
    params["engine"] = engine_label  # always reflect the engine actually used
    params.setdefault("horizon_years", horizon_years)

    if use_ml_effective:
        params["model_version"] = getattr(
            settings,
            "FUTURE_SKILLS_MODEL_VERSION",
            "unknown",
        )
        logger.info("Model version: %s", params["model_version"])
    else:
        # If rule-based, ensure we don't keep a stale model_version
        params.pop("model_version", None)

    PredictionRun.objects.create(
        description=(
            f"Recalcul des prédictions à horizon {horizon_years} ans "
            f"({engine_label})."
        ),
        total_predictions=total_predictions,
        run_by=run_by,
        parameters=params,
    )
    
    logger.info("✅ Prediction recalculation completed successfully")
    logger.info("Total predictions created/updated: %s", total_predictions)
    logger.info("Engine used: %s | Horizon: %s years", engine_label, horizon_years)
    logger.info("========================================")

    return total_predictions

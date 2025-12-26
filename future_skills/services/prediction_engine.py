"""Prediction engine for Future Skills (Module 3).

This module provides:
- A PredictionEngine class for ML and rules-based predictions
- A recalculate_predictions() function for batch updates
- Prediction logging for monitoring and drift detection

Usage:
    # Initialize engine
    engine = PredictionEngine(enable_explanations=generate_explanations)

    # Single prediction
    score, level, rationale, explanation = engine.predict(
        job_role_id=1,
        skill_id=5,
        horizon_years=5
    )

    # Batch prediction
    results = engine.batch_predict([
        {'job_role_id': 1, 'skill_id': 5, 'horizon_years': 5},
        {'job_role_id': 2, 'skill_id': 6, 'horizon_years': 3},
    ])

    # Use in management command or API
    from future_skills.services.prediction_engine import recalculate_predictions
    total = recalculate_predictions(horizon_years=5)

⚠️ IMPORTANT:
- The public API is PredictionEngine, recalculate_predictions(), and calculate_level()
- PredictionEngine auto-detects ML vs rules-based from settings
- Existing callers/tests continue to work with backward compatibility
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Tuple

from django.conf import settings

from future_skills.ml_model import FutureSkillsModel
from future_skills.models import FutureSkillPrediction, JobRole, MarketTrend, PredictionRun, Skill

logger = logging.getLogger(__name__)

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


# ---------------------------------------------------------------------------
# Unified Prediction Engine Class (Section 5.1)
# ---------------------------------------------------------------------------


class PredictionEngine:
    """Unified prediction engine that can use either rules-based or ML models.

    Usage:
        engine = PredictionEngine()
        predictions = engine.predict(job_role_id, skill_id, horizon_years)
    """

    def __init__(
        self,
        use_ml=None,
        model_path=None,
        enable_explanations: bool | None = None,
    ):
        """Initialize the prediction engine.

        Args:
            use_ml: If True, use ML model. If None, use settings.FUTURE_SKILLS_USE_ML.
            model_path: Path to ML model file. If None, use settings.FUTURE_SKILLS_MODEL_PATH.
            enable_explanations: Toggle SHAP/LIME explanations; defaults to settings flag.
        """
        self.use_ml = use_ml if use_ml is not None else getattr(settings, "FUTURE_SKILLS_USE_ML", False)
        self.model_path = model_path or getattr(settings, "FUTURE_SKILLS_MODEL_PATH", None)
        self.model = None
        self.enable_explanations = (
            enable_explanations
            if enable_explanations is not None
            else getattr(settings, "FUTURE_SKILLS_ENABLE_EXPLANATIONS", True)
        )
        self.explanation_engine = None

        if self.use_ml:
            self._load_model()

    def _load_model(self):
        """Load the ML model using FutureSkillsModel.instance()."""
        try:
            self.model = FutureSkillsModel.instance()
            if self.model.is_available():
                logger.info("ML model loaded successfully")

                if self.enable_explanations and EXPLANATION_ENGINE_AVAILABLE:
                    self.explanation_engine = ExplanationEngine(self.model)
                    logger.info("Explanation engine initialized")
            else:
                logger.warning("ML model not available. Using rules-based engine.")
                self.use_ml = False
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}. Falling back to rules-based engine.")
            self.use_ml = False

    def predict(self, job_role_id: int, skill_id: int, horizon_years: int) -> Tuple[float, str, str, Dict]:
        """Generate a prediction for a given job role, skill, and horizon.

        Args:
            job_role_id: ID of the JobRole
            skill_id: ID of the Skill
            horizon_years: Prediction horizon in years

        Returns:
            Tuple of (score, level, rationale, explanation)
        """
        if self.use_ml and self.model:
            score, level, explanation = self._predict_ml(job_role_id, skill_id)
            rationale = self._build_ml_rationale(horizon_years)
        else:
            score, level, rationale, explanation = self._predict_rules(job_role_id, skill_id)

        return score, level, rationale, explanation

    def _predict_ml(self, job_role_id, skill_id):
        """Use ML model for prediction."""
        # Get job role and skill objects
        job_role = JobRole.objects.get(pk=job_role_id)
        skill = Skill.objects.get(pk=skill_id)

        # Extract features using existing helper functions
        trend_score = _find_relevant_trend(job_role, skill)
        internal_usage = _estimate_internal_usage(job_role, skill)
        training_requests = _estimate_training_requests(job_role, skill)
        scarcity_index = _estimate_scarcity_index(job_role, skill, internal_usage)

        # Get prediction from ML model
        level, score = self.model.predict_level(
            job_role_name=job_role.name,
            skill_name=skill.name,
            trend_score=trend_score,
            internal_usage=internal_usage,
            training_requests=training_requests,
            scarcity_index=scarcity_index,
        )

        # Generate explanation
        explanation = {}
        if self.explanation_engine:
            try:
                explanation = self.explanation_engine.generate_explanation(
                    job_role_name=job_role.name,
                    skill_name=skill.name,
                    trend_score=trend_score,
                    internal_usage=internal_usage,
                    training_requests=training_requests,
                    scarcity_index=scarcity_index,
                )
            except Exception as e:
                logger.warning(f"Failed to generate explanation: {e}")

        return score, level, explanation

    def _predict_rules(self, job_role_id, skill_id):
        """Use rules-based engine for prediction."""
        # Get job role and skill objects
        job_role = JobRole.objects.get(pk=job_role_id)
        skill = Skill.objects.get(pk=skill_id)

        # Extract features using existing helper functions
        trend_score = _find_relevant_trend(job_role, skill)
        internal_usage = _estimate_internal_usage(job_role, skill)
        training_requests = _estimate_training_requests(job_role, skill)
        scarcity_index = _estimate_scarcity_index(job_role, skill, internal_usage)

        # Use rules-based engine
        level, score = calculate_level(
            trend_score=trend_score,
            internal_usage=internal_usage,
            training_requests=training_requests,
        )

        rationale = (
            f"Prédiction basée sur les tendances marché (score={trend_score:.2f}), "
            f"l'utilisation interne estimée (score={internal_usage:.2f}), "
            f"les demandes de formation (~{training_requests:.1f}) "
            f"et l'indice de rareté (~{scarcity_index:.2f}). "
            f"Moteur utilisé : rules_v1."
        )
        explanation = {}

        return score, level, rationale, explanation

    @staticmethod
    def _build_ml_rationale(horizon_years: int) -> str:
        """Generate a standard rationale string for ML-based predictions."""
        return f"ML prediction based on {horizon_years}-year horizon"

    def batch_predict(self, predictions_data: list) -> list:
        """Generate predictions for multiple job_role/skill/horizon combinations.

        Args:
            predictions_data: List of dicts with keys: job_role_id, skill_id, horizon_years

        Returns:
            List of prediction results
        """
        results = []
        for data in predictions_data:
            score, level, rationale, explanation = self.predict(
                data["job_role_id"], data["skill_id"], data["horizon_years"]
            )
            results.append(
                {
                    "job_role_id": data["job_role_id"],
                    "skill_id": data["skill_id"],
                    "horizon_years": data["horizon_years"],
                    "score": score,
                    "level": level,
                    "rationale": rationale,
                    "explanation": explanation,
                }
            )

        return results


# ---------------------------------------------------------------------------
# Prediction Logging for Drift Detection
# ---------------------------------------------------------------------------


def _log_prediction_for_monitoring(
    job_role_id: int,
    skill_id: int,
    predicted_level: str,
    score: float,
    engine: str,
    model_version: str = None,
    features: Dict[str, float] = None,
):
    """Log prediction details to a dedicated file for long-term monitoring.

    This enables:
    - Data drift detection (comparing feature distributions over time)
    - Model performance tracking
    - Comparison between predictions and actual HR decisions

    Logs are anonymized (using IDs instead of names) and stored in JSON format.
    """
    # Only log if monitoring is enabled (default: True)
    if not getattr(settings, "FUTURE_SKILLS_ENABLE_MONITORING", True):
        return

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "job_role_id": job_role_id,
        "skill_id": skill_id,
        "predicted_level": predicted_level,
        "score": round(score, 2),
        "engine": engine,
        "model_version": model_version,
        "features": features or {},
    }

    # Write to monitoring log file
    try:
        monitoring_log_path = getattr(
            settings,
            "FUTURE_SKILLS_MONITORING_LOG",
            settings.BASE_DIR / "logs" / "predictions_monitoring.jsonl",
        )

        # Ensure logs directory exists
        monitoring_log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(monitoring_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    except Exception as exc:
        logger.warning(f"Failed to write monitoring log: {exc}")


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

    Attempts to prioritize sector/category matches before falling back to
    the most recent global trend.
    """
    sector_hints = [
        (getattr(job_role, "department", "") or "").strip(),
        (getattr(skill, "category", "") or "").strip(),
    ]

    for hint in sector_hints:
        if hint:
            trend = MarketTrend.objects.filter(sector__iexact=hint).order_by("-year").first()
            if trend:
                return max(0.0, min(1.0, float(trend.trend_score)))

    trend = MarketTrend.objects.order_by("-year").first()
    if trend is None:
        return 0.5  # neutral default
    return max(0.0, min(1.0, float(trend.trend_score)))


def _estimate_internal_usage(job_role: JobRole, skill: Skill) -> float:
    """Estimate internal usage of a skill for a given job role.

    For now, this is a placeholder heuristic.
    It can later be replaced by real usage metrics.
    """
    role_name = (job_role.name or "").lower()
    base = 0.6 if "manager" in role_name else 0.4

    skill_profile = (getattr(skill, "category", "") or skill.name or "").lower()
    if any(keyword in skill_profile for keyword in ("data", "cloud", "ai")):
        base += 0.1
    elif any(keyword in skill_profile for keyword in ("ops", "support")):
        base -= 0.05

    return max(0.0, min(1.0, base))


def _estimate_training_requests(job_role: JobRole, skill: Skill) -> float:
    """Estimate how many training requests exist for this (job, skill).

    Placeholder for now; later it can be replaced by real stats.
    """
    skill_name = (skill.name or "").lower()
    keywords = ("data", "ia", "ai", "cloud", "intelligence", "artificiel")
    base_requests = 40.0 if any(keyword in skill_name for keyword in keywords) else 10.0

    dept = (getattr(job_role, "department", "") or "").lower()
    if "tech" in dept or "digital" in dept:
        base_requests *= 1.1

    role_name = (getattr(job_role, "name", "") or "").lower()
    if "junior" in role_name:
        base_requests *= 1.2
    elif "lead" in role_name or "senior" in role_name:
        base_requests *= 0.9

    return max(5.0, min(60.0, base_requests))


def _estimate_scarcity_index(job_role: JobRole, skill: Skill, internal_usage: float) -> float:
    """Very simple scarcity index based on internal usage.

    - Low internal usage → skill considered more rare (scarce).
    - Value clamped to [0, 1].
    """
    scarcity = 1.0 - internal_usage

    skill_profile = (getattr(skill, "category", "") or skill.name or "").lower()
    if any(keyword in skill_profile for keyword in ("cloud", "ia", "data")):
        scarcity += 0.1

    dept = (getattr(job_role, "department", "") or "").lower()
    if "operations" in dept or "support" in dept:
        scarcity -= 0.05
    elif "innovation" in dept:
        scarcity += 0.05

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

    Now uses PredictionEngine internally for unified prediction logic.

    Behaviour:
    - Creates a PredictionEngine instance that automatically detects whether
      to use ML or rules-based predictions based on settings
    - Uses batch_predict() for efficient processing of all predictions
    - Maintains backward compatibility with existing function signature

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

    # Initialize PredictionEngine (auto-detects ML vs rules-based)
    engine = PredictionEngine(enable_explanations=generate_explanations)

    job_roles = list(JobRole.objects.all())
    skills = list(Skill.objects.all())
    total_combinations = len(job_roles) * len(skills) if job_roles and skills else 0

    logger.info(
        "Dataset size: %s job roles × %s skills = %s combinations",
        len(job_roles),
        len(skills),
        total_combinations,
    )

    # Determine engine label for logging
    engine_label = "ml_random_forest_v1" if engine.use_ml else "rules_v1"
    logger.info("🔧 Engine selected: %s", engine_label)

    # Prepare batch prediction data
    predictions_data = _build_batch_prediction_payload(
        job_roles=job_roles,
        skills=skills,
        horizon_years=horizon_years,
    )

    logger.info("Prepared %s predictions for batch processing", len(predictions_data))

    # Use batch prediction for efficiency
    results = engine.batch_predict(predictions_data)

    total_predictions = _persist_prediction_results(
        results=results,
        horizon_years=horizon_years,
        engine_label=engine_label,
        use_ml_engine=engine.use_ml,
        job_role_map={job_role.id: job_role for job_role in job_roles},
        skill_map={skill.id: skill for skill in skills},
    )

    # Build parameters for PredictionRun
    params = _build_prediction_run_params(
        parameters=parameters,
        engine_label=engine_label,
        horizon_years=horizon_years,
        use_ml_engine=engine.use_ml,
    )

    PredictionRun.objects.create(
        description=(f"Recalcul des prédictions à horizon {horizon_years} ans " f"({engine_label})."),
        total_predictions=total_predictions,
        run_by=run_by,
        parameters=params,
    )

    logger.info("✅ Prediction recalculation completed successfully")
    logger.info("Total predictions created/updated: %s", total_predictions)
    logger.info("Engine used: %s | Horizon: %s years", engine_label, horizon_years)
    logger.info("========================================")

    return total_predictions


def _build_batch_prediction_payload(
    job_roles: list[JobRole],
    skills: list[Skill],
    horizon_years: int,
) -> list[Dict[str, int]]:
    """Create the payload consumed by PredictionEngine.batch_predict."""
    return [
        {
            "job_role_id": job_role.id,
            "skill_id": skill.id,
            "horizon_years": horizon_years,
        }
        for job_role in job_roles
        for skill in skills
    ]


def _persist_prediction_results(
    *,
    results: list[Dict[str, Any]],
    horizon_years: int,
    engine_label: str,
    use_ml_engine: bool,
    job_role_map: Dict[int, JobRole],
    skill_map: Dict[int, Skill],
) -> int:
    """Store prediction results and emit monitoring logs."""
    total_predictions = 0
    model_version = getattr(settings, "FUTURE_SKILLS_MODEL_VERSION", "unknown") if use_ml_engine else None

    for result in results:
        job_role = job_role_map.get(result["job_role_id"])
        skill = skill_map.get(result["skill_id"])

        if job_role is None or skill is None:
            continue

        defaults = {
            "score": result["score"],
            "level": result["level"],
            "rationale": result["rationale"],
        }

        if explanation := result.get("explanation"):
            defaults["explanation"] = explanation

        FutureSkillPrediction.objects.update_or_create(
            job_role=job_role,
            skill=skill,
            horizon_years=horizon_years,
            defaults=defaults,
        )
        total_predictions += 1

        trend_score = _find_relevant_trend(job_role, skill)
        internal_usage = _estimate_internal_usage(job_role, skill)
        training_requests = _estimate_training_requests(job_role, skill)
        scarcity_index = _estimate_scarcity_index(job_role, skill, internal_usage)

        _log_prediction_for_monitoring(
            job_role_id=job_role.id,
            skill_id=skill.id,
            predicted_level=result["level"],
            score=result["score"],
            engine=engine_label,
            model_version=model_version,
            features={
                "trend_score": trend_score,
                "internal_usage": internal_usage,
                "training_requests": training_requests,
                "scarcity_index": scarcity_index,
            },
        )

    return total_predictions


def _build_prediction_run_params(
    *,
    parameters: Dict[str, Any] | None,
    engine_label: str,
    horizon_years: int,
    use_ml_engine: bool,
) -> Dict[str, Any]:
    """Prepare the payload stored in PredictionRun.parameters."""
    params: Dict[str, Any] = parameters.copy() if isinstance(parameters, dict) else {}
    params["engine"] = engine_label
    params.setdefault("horizon_years", horizon_years)

    if use_ml_engine:
        params["model_version"] = getattr(
            settings,
            "FUTURE_SKILLS_MODEL_VERSION",
            "unknown",
        )
        logger.info("Model version: %s", params["model_version"])
    else:
        params.pop("model_version", None)

    return params

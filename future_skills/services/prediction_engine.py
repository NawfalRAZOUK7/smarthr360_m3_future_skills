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
import hashlib
from datetime import datetime
from typing import Any, Dict, Tuple

from django.conf import settings
from django.utils import timezone

from future_skills.ml_model import FutureSkillsModel
from future_skills.models import FutureSkillPrediction, JobRole, MarketTrend, PredictionRun, Skill
from future_skills.services.recommendation_engine import (
    _choose_priority_from_level,
    _choose_recommended_action,
)
from future_skills.services.snapshot_service import (
    LOW_SAMPLE_THRESHOLD,
    compute_interaction_features,
    get_time_features,
)
from future_skills.services.prediction_metrics import update_prediction_metrics

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
        result = self.predict_with_metadata(job_role_id, skill_id, horizon_years)
        return result["score"], result["level"], result["rationale"], result["explanation"]

    def predict_with_metadata(
        self,
        job_role_id: int,
        skill_id: int,
        horizon_years: int,
        *,
        as_of_date=None,
        feature_overrides: Dict[str, float] | None = None,
    ) -> Dict[str, Any]:
        """Generate a prediction with enriched metadata for API/output contract."""
        job_role = JobRole.objects.get(pk=job_role_id)
        skill = Skill.objects.get(pk=skill_id)

        as_of_date = as_of_date or timezone.now().date()
        horizon_months = horizon_years * 12

        feature_context = _build_feature_context(
            job_role,
            skill,
            as_of_date=as_of_date,
            horizon_months=horizon_months,
        )
        if feature_overrides:
            feature_context = _apply_feature_overrides(feature_context, feature_overrides)

        base_engine_label = "ml_random_forest_v1" if self.use_ml else "rules_v1"
        final_engine_label = base_engine_label
        confidence_threshold, high_confidence_threshold = _resolve_confidence_thresholds()
        fallback_applied = False
        fallback_reason = None

        if self.use_ml and self.model:
            ml_prediction = self._predict_ml_with_metadata(job_role, skill, feature_context)
            confidence = ml_prediction.get("confidence")
            fallback_applied, fallback_reason = _should_fallback(
                confidence,
                ml_prediction["level"],
                confidence_threshold,
                high_confidence_threshold,
            )
            if fallback_applied:
                prediction = self._predict_rules_with_metadata(job_role, skill, feature_context)
                rationale = (
                    f"{prediction['rationale']} Fallback rules_v1 "
                    f"(reason={fallback_reason}, confidence={confidence})."
                )
                final_engine_label = "rules_v1"
            else:
                prediction = ml_prediction
                rationale = self._build_ml_rationale(horizon_years)
        else:
            prediction = self._predict_rules_with_metadata(job_role, skill, feature_context)
            rationale = prediction["rationale"]

        raw_level = prediction["level"]
        level_source = "model_level"
        presentation_thresholds = {}
        if getattr(settings, "FUTURE_SKILLS_DERIVE_LEVEL_FROM_SCORE", False):
            low_threshold, high_threshold = _resolve_presentation_thresholds()
            prediction["level"] = _derive_level_from_score(
                prediction["score"],
                low_threshold,
                high_threshold,
            )
            level_source = "score_thresholds"
            presentation_thresholds = {"low": low_threshold, "high": high_threshold}

        explanation = prediction.get("explanation", {})
        confidence = prediction.get("confidence")
        if confidence is None:
            confidence = round(prediction["score"] / 100.0, 4)
        top_drivers = _build_top_drivers(explanation, feature_context)
        recommended_actions = _build_recommended_actions(job_role, skill, prediction["level"], rationale)

        model_version = getattr(settings, "FUTURE_SKILLS_MODEL_VERSION", None) if self.use_ml else None
        label_provenance_used = _resolve_label_provenance(final_engine_label != "rules_v1")

        decision_policy = _build_decision_policy(
            base_engine=base_engine_label,
            final_engine=final_engine_label,
            confidence_threshold=confidence_threshold,
            high_confidence_threshold=high_confidence_threshold,
            fallback_applied=fallback_applied,
            fallback_reason=fallback_reason,
            presentation_thresholds=presentation_thresholds,
            level_source=level_source,
            raw_level=raw_level,
        )
        data_window = {
            "as_of_date": as_of_date.isoformat(),
            "horizon_months": horizon_months,
        }

        audit_payload = _build_audit_payload(
            feature_context=feature_context,
            score=prediction["score"],
            level=prediction["level"],
            raw_level=raw_level,
            probabilities=prediction.get("probabilities", {}),
            confidence=prediction.get("confidence"),
            engine_label=final_engine_label,
            model_version=model_version,
            as_of_date=as_of_date,
        )

        return {
            "job_role_id": job_role_id,
            "skill_id": skill_id,
            "horizon_years": horizon_years,
            "horizon_months": horizon_months,
            "as_of_date": as_of_date,
            "score": prediction["score"],
            "level": prediction["level"],
            "rationale": rationale,
            "explanation": explanation,
            "probabilities": prediction.get("probabilities", {}),
            "confidence": confidence,
            "top_drivers": top_drivers,
            "recommended_actions": recommended_actions,
            "label_provenance_used": label_provenance_used,
            "model_version": model_version,
            "data_window": data_window,
            "decision_policy": decision_policy,
            "audit_payload": audit_payload,
        }

    def _predict_ml(self, job_role_id, skill_id):
        """Use ML model for prediction."""
        job_role = JobRole.objects.get(pk=job_role_id)
        skill = Skill.objects.get(pk=skill_id)
        feature_context = _build_feature_context(job_role, skill, horizon_months=12)
        prediction = self._predict_ml_with_metadata(job_role, skill, feature_context)
        return prediction["score"], prediction["level"], prediction.get("explanation", {})

    def _predict_ml_with_metadata(self, job_role, skill, feature_context: Dict[str, float]) -> Dict[str, Any]:
        """Use ML model for prediction with probabilities/confidence."""
        prediction = self.model.predict_with_metadata(
            job_role_name=job_role.name,
            skill_name=skill.name,
            trend_score=feature_context["trend_score"],
            internal_usage=feature_context["internal_usage"],
            training_requests=feature_context["training_requests"],
            scarcity_index=feature_context["scarcity_index"],
            trend_momentum=feature_context.get("trend_momentum", 0.0),
            trend_acceleration=feature_context.get("trend_acceleration", 0.0),
            trend_volatility=feature_context.get("trend_volatility", 0.0),
            trend_persistence=feature_context.get("trend_persistence", 0.0),
            internal_usage_momentum=feature_context.get("internal_usage_momentum", 0.0),
            training_requests_momentum=feature_context.get("training_requests_momentum", 0.0),
            internal_usage_lag_1=feature_context.get("internal_usage_lag_1", 0.0),
            internal_usage_lag_2=feature_context.get("internal_usage_lag_2", 0.0),
            internal_usage_roll_mean_3=feature_context.get("internal_usage_roll_mean_3", 0.0),
            training_requests_lag_1=feature_context.get("training_requests_lag_1", 0.0),
            training_requests_lag_2=feature_context.get("training_requests_lag_2", 0.0),
            training_requests_roll_mean_3=feature_context.get("training_requests_roll_mean_3", 0.0),
            economic_indicator_lag_1=feature_context.get("economic_indicator_lag_1", 0.0),
            economic_indicator_lag_2=feature_context.get("economic_indicator_lag_2", 0.0),
            economic_indicator_roll_mean_3=feature_context.get("economic_indicator_roll_mean_3", 0.0),
            trend_stability_flag=feature_context.get("trend_stability_flag", 0.0),
            internal_usage_stability_flag=feature_context.get("internal_usage_stability_flag", 0.0),
            training_requests_stability_flag=feature_context.get("training_requests_stability_flag", 0.0),
            data_quality_window_coverage=feature_context.get("data_quality_window_coverage", 0.0),
            data_quality_missing_flag=feature_context.get("data_quality_missing_flag", 0.0),
            data_quality_stale_flag=feature_context.get("data_quality_stale_flag", 0.0),
            data_quality_low_sample_flag=feature_context.get("data_quality_low_sample_flag", 0.0),
            is_it_department=feature_context.get("is_it_department", 0.0),
            is_senior_role=feature_context.get("is_senior_role", 0.0),
            is_technical_skill=feature_context.get("is_technical_skill", 0.0),
            dept_skill_alignment=feature_context.get("dept_skill_alignment", 0.0),
            forecast_trend_score=feature_context.get("forecast_trend_score", 0.0),
            forecast_internal_usage=feature_context.get("forecast_internal_usage", 0.0),
            forecast_training_requests=feature_context.get("forecast_training_requests", 0.0),
            forecast_need_score=feature_context.get("forecast_need_score", 0.0),
        )

        explanation = {}
        if self.explanation_engine:
            try:
                extra_features = {
                    key: value
                    for key, value in feature_context.items()
                    if key not in {"trend_score", "internal_usage", "training_requests", "scarcity_index"}
                }
                explanation = self.explanation_engine.generate_explanation(
                    job_role_name=job_role.name,
                    skill_name=skill.name,
                    trend_score=feature_context["trend_score"],
                    internal_usage=feature_context["internal_usage"],
                    training_requests=feature_context["training_requests"],
                    scarcity_index=feature_context["scarcity_index"],
                    **extra_features,
                )
            except Exception as e:
                logger.warning(f"Failed to generate explanation: {e}")

        return {
            "score": prediction["score"],
            "level": prediction["level"],
            "probabilities": prediction.get("probabilities", {}),
            "confidence": prediction.get("confidence"),
            "explanation": explanation,
        }

    def _predict_rules(self, job_role_id, skill_id):
        """Use rules-based engine for prediction."""
        job_role = JobRole.objects.get(pk=job_role_id)
        skill = Skill.objects.get(pk=skill_id)
        feature_context = _build_feature_context(job_role, skill, horizon_months=12)
        prediction = self._predict_rules_with_metadata(job_role, skill, feature_context)
        return prediction["score"], prediction["level"], prediction["rationale"], prediction.get("explanation", {})

    @staticmethod
    def _predict_rules_with_metadata(job_role, skill, feature_context: Dict[str, float]) -> Dict[str, Any]:
        """Use rules-based engine for prediction with minimal metadata."""
        level, score = calculate_level(
            trend_score=feature_context["trend_score"],
            internal_usage=feature_context["internal_usage"],
            training_requests=feature_context["training_requests"],
        )

        rationale = (
            f"Prédiction basée sur les tendances marché (score={feature_context['trend_score']:.2f}), "
            f"l'utilisation interne estimée (score={feature_context['internal_usage']:.2f}), "
            f"les demandes de formation (~{feature_context['training_requests']:.1f}) "
            f"et l'indice de rareté (~{feature_context['scarcity_index']:.2f}). "
            f"Moteur utilisé : rules_v1."
        )

        confidence = round(score / 100.0, 4)

        return {
            "score": score,
            "level": level,
            "rationale": rationale,
            "probabilities": {},
            "confidence": confidence,
            "explanation": {},
        }

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
            as_of_date = data.get("as_of_date")
            result = self.predict_with_metadata(
                data["job_role_id"],
                data["skill_id"],
                data["horizon_years"],
                as_of_date=as_of_date,
            )
            results.append(result)

        return results


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------


def _build_feature_context(
    job_role: JobRole,
    skill: Skill,
    as_of_date=None,
    horizon_months: int | None = None,
) -> Dict[str, float]:
    """Build the feature context used for scoring and audit logs."""
    trend_score = _find_relevant_trend(job_role, skill, as_of_date=as_of_date)
    internal_usage = _estimate_internal_usage(job_role, skill)
    training_requests = _estimate_training_requests(job_role, skill)
    scarcity_index = _estimate_scarcity_index(job_role, skill, internal_usage)
    time_features = {}
    if as_of_date:
        time_features = get_time_features(
            job_role_id=job_role.id,
            skill_id=skill.id,
            as_of_date=as_of_date,
            horizon_months=horizon_months,
        )
    interaction_features = compute_interaction_features(job_role, skill)
    low_sample_flag = 1.0 if training_requests < LOW_SAMPLE_THRESHOLD else 0.0
    if "data_quality_low_sample_flag" in time_features:
        time_features["data_quality_low_sample_flag"] = max(
            float(time_features.get("data_quality_low_sample_flag", 0.0)),
            low_sample_flag,
        )

    return {
        "trend_score": trend_score,
        "internal_usage": internal_usage,
        "training_requests": training_requests,
        "scarcity_index": scarcity_index,
        **time_features,
        **interaction_features,
    }


def _apply_feature_overrides(feature_context: Dict[str, float], overrides: Dict[str, float]) -> Dict[str, float]:
    """Apply scenario overrides to the feature context."""
    updated = feature_context.copy()
    for key, value in overrides.items():
        if key not in updated:
            continue
        try:
            updated[key] = float(value)
        except (TypeError, ValueError):
            continue

    if "training_requests" in overrides:
        low_sample_flag = 1.0 if updated["training_requests"] < LOW_SAMPLE_THRESHOLD else 0.0
        if "data_quality_low_sample_flag" in updated:
            updated["data_quality_low_sample_flag"] = max(
                float(updated.get("data_quality_low_sample_flag", 0.0)),
                low_sample_flag,
            )

    return updated


def _build_top_drivers(explanation: Dict[str, Any], feature_context: Dict[str, float]) -> list:
    """Return top drivers from explanation or fall back to rule-based drivers."""
    if explanation and isinstance(explanation, dict) and explanation.get("top_factors"):
        return explanation["top_factors"]
    return _build_rule_based_drivers(feature_context)


def _build_rule_based_drivers(feature_context: Dict[str, float]) -> list:
    """Derive simple top drivers from feature values."""
    readable = {
        "trend_score": "market trend",
        "internal_usage": "internal usage",
        "training_requests": "training requests",
        "scarcity_index": "scarcity index",
    }

    def _strength(value: float) -> str:
        if value >= 0.7:
            return "high"
        if value <= 0.3:
            return "low"
        return "medium"

    candidates = []
    trend_score = feature_context["trend_score"]
    internal_usage = feature_context["internal_usage"]
    training_requests = _normalize_training_requests(feature_context["training_requests"])
    scarcity_index = feature_context["scarcity_index"]

    candidates.append(
        {
            "feature": "trend_score",
            "feature_readable": readable["trend_score"],
            "impact": "positive" if trend_score >= 0.5 else "negative",
            "strength": _strength(trend_score),
            "value": round(trend_score, 3),
            "weight": abs(trend_score - 0.5),
        }
    )
    candidates.append(
        {
            "feature": "internal_usage",
            "feature_readable": readable["internal_usage"],
            "impact": "positive" if internal_usage < 0.5 else "negative",
            "strength": _strength(1 - internal_usage),
            "value": round(internal_usage, 3),
            "weight": abs(0.5 - internal_usage),
        }
    )
    candidates.append(
        {
            "feature": "training_requests",
            "feature_readable": readable["training_requests"],
            "impact": "positive" if training_requests >= 0.5 else "negative",
            "strength": _strength(training_requests),
            "value": round(training_requests, 3),
            "weight": abs(training_requests - 0.5),
        }
    )
    candidates.append(
        {
            "feature": "scarcity_index",
            "feature_readable": readable["scarcity_index"],
            "impact": "positive" if scarcity_index >= 0.5 else "negative",
            "strength": _strength(scarcity_index),
            "value": round(scarcity_index, 3),
            "weight": abs(scarcity_index - 0.5),
        }
    )

    candidates.sort(key=lambda item: item["weight"], reverse=True)
    top = candidates[:3]
    for item in top:
        item.pop("weight", None)
    return top


def _build_recommended_actions(job_role: JobRole, skill: Skill, level: str, rationale: str) -> list:
    """Build a single recommended action payload for the prediction."""
    action = _choose_recommended_action(job_role, skill)
    priority = _choose_priority_from_level(level)
    return [
        {
            "action": action,
            "priority": priority,
            "rationale": rationale,
            "policy": "simple_rules_v1",
        }
    ]


def _resolve_label_provenance(use_ml_engine: bool) -> str:
    """Resolve label provenance used for the model that generated the prediction."""
    configured = getattr(settings, "FUTURE_SKILLS_LABEL_PROVENANCE", None)
    if configured:
        return str(configured).upper()
    return "SILVER" if use_ml_engine else "BRONZE"


def _resolve_confidence_thresholds() -> Tuple[float | None, float | None]:
    """Resolve confidence thresholds from settings (None disables threshold)."""
    threshold = getattr(settings, "FUTURE_SKILLS_CONFIDENCE_THRESHOLD", 0.6)
    high_threshold = getattr(settings, "FUTURE_SKILLS_HIGH_CONFIDENCE_THRESHOLD", 0.7)

    threshold = None if threshold is None else float(threshold)
    high_threshold = None if high_threshold is None else float(high_threshold)

    return threshold, high_threshold


def _should_fallback(
    confidence: float | None,
    level: str,
    confidence_threshold: float | None,
    high_confidence_threshold: float | None,
) -> Tuple[bool, str | None]:
    """Decide if we should fallback to rules based on confidence."""
    if confidence is None:
        return False, None

    if level == FutureSkillPrediction.LEVEL_HIGH and high_confidence_threshold is not None:
        if confidence < high_confidence_threshold:
            return True, "low_confidence_high"

    if confidence_threshold is not None and confidence < confidence_threshold:
        return True, "low_confidence"

    return False, None


def _build_decision_policy(
    *,
    base_engine: str,
    final_engine: str,
    confidence_threshold: float | None,
    high_confidence_threshold: float | None,
    fallback_applied: bool,
    fallback_reason: str | None,
    presentation_thresholds: Dict[str, float] | None = None,
    level_source: str | None = None,
    raw_level: str | None = None,
) -> Dict[str, Any]:
    """Return decision policy metadata for auditability."""
    return {
        "engine": base_engine,
        "final_engine": final_engine,
        "abstain_enabled": confidence_threshold is not None or high_confidence_threshold is not None,
        "confidence_threshold": confidence_threshold,
        "high_confidence_threshold": high_confidence_threshold,
        "fallback_engine": "rules_v1" if base_engine != "rules_v1" else None,
        "fallback_applied": fallback_applied,
        "fallback_reason": fallback_reason,
        "level_source": level_source,
        "presentation_thresholds": presentation_thresholds or {},
        "raw_level": raw_level,
    }


def _build_audit_payload(
    *,
    feature_context: Dict[str, float],
    score: float,
    level: str,
    raw_level: str | None,
    probabilities: Dict[str, float],
    confidence: Any,
    engine_label: str,
    model_version: str | None,
    as_of_date,
) -> Dict[str, Any]:
    """Build an audit payload with inputs, outputs, and lineage."""
    feature_hash = hashlib.sha256(
        json.dumps(feature_context, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "timestamp": timezone.now().isoformat(),
        "engine": engine_label,
        "model_version": model_version,
        "as_of_date": as_of_date.isoformat() if as_of_date else None,
        "feature_snapshot_hash": feature_hash,
        "inputs": feature_context,
        "outputs": {
            "score": score,
            "level": level,
            "raw_level": raw_level,
            "probabilities": probabilities,
            "confidence": confidence,
        },
    }


def _resolve_presentation_thresholds() -> Tuple[float, float]:
    """Resolve score thresholds for deriving LOW/MEDIUM/HIGH."""
    thresholds = getattr(settings, "FUTURE_SKILLS_SCORE_THRESHOLDS", {"low": 40.0, "high": 70.0})
    low = float(thresholds.get("low", 40.0))
    high = float(thresholds.get("high", 70.0))
    if low >= high:
        logger.warning("Invalid FUTURE_SKILLS_SCORE_THRESHOLDS: low >= high; using defaults.")
        low, high = 40.0, 70.0
    return low, high


def _derive_level_from_score(score: float, low_threshold: float, high_threshold: float) -> str:
    """Derive LOW/MEDIUM/HIGH from a continuous score."""
    if score >= high_threshold:
        return FutureSkillPrediction.LEVEL_HIGH
    if score >= low_threshold:
        return FutureSkillPrediction.LEVEL_MEDIUM
    return FutureSkillPrediction.LEVEL_LOW


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
    confidence: float | None = None,
    probabilities: Dict[str, float] | None = None,
    label_provenance: str | None = None,
    decision_policy: Dict[str, Any] | None = None,
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
        "confidence": confidence,
        "probabilities": probabilities or {},
        "label_provenance_used": label_provenance,
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

    update_prediction_metrics(
        level=predicted_level,
        confidence=confidence,
        decision_policy=decision_policy,
        features=features,
    )


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


def _find_relevant_trend(job_role: JobRole, skill: Skill, as_of_date=None) -> float:
    """Return a trend_score in [0, 1] for the given (job_role, skill).

    Attempts to prioritize sector/category matches before falling back to
    the most recent global trend.
    """
    trends = MarketTrend.objects.all()
    if as_of_date:
        trends = trends.filter(year__lte=as_of_date.year)

    sector_hints = [
        (getattr(job_role, "department", "") or "").strip(),
        (getattr(skill, "category", "") or "").strip(),
    ]

    for hint in sector_hints:
        if hint:
            trend = trends.filter(sector__iexact=hint).order_by("-year").first()
            if trend:
                return max(0.0, min(1.0, float(trend.trend_score)))

    trend = trends.order_by("-year").first()
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

    return round(max(0.0, min(1.0, scarcity)), 3)


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

    as_of_date = timezone.now().date()

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
        as_of_date=as_of_date,
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
        as_of_date=as_of_date,
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
    as_of_date=None,
) -> list[Dict[str, int]]:
    """Create the payload consumed by PredictionEngine.batch_predict with safe defaults."""
    payload: list[Dict[str, Any]] = []

    for job_role in job_roles:
        for skill in skills:
            trend_score = _find_relevant_trend(job_role, skill, as_of_date=as_of_date)
            internal_usage = _estimate_internal_usage(job_role, skill)
            training_requests = _estimate_training_requests(job_role, skill)
            scarcity_index = _estimate_scarcity_index(job_role, skill, internal_usage)

            payload.append(
                {
                    "job_role_id": job_role.id,
                    "skill_id": skill.id,
                    "horizon_years": horizon_years,
                    "as_of_date": as_of_date,
                    "job_role_name": job_role.name,
                    "skill_name": skill.name,
                    "skill_category": (skill.category or "Unspecified"),
                    "job_department": (job_role.department or "General"),
                    "trend_score": trend_score,
                    "internal_usage": internal_usage,
                    "training_requests": training_requests,
                    "scarcity_index": scarcity_index,
                    # Sensible defaults to satisfy ML feature set even if data is sparse
                    "hiring_difficulty": 0.5,
                    "avg_salary_k": 50.0,
                    "economic_indicator": 0.5,
                }
            )

    return payload


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
            "horizon_months": result.get("horizon_months"),
            "as_of_date": result.get("as_of_date"),
            "probabilities": result.get("probabilities", {}),
            "confidence": result.get("confidence"),
            "top_drivers": result.get("top_drivers", []),
            "recommended_actions": result.get("recommended_actions", []),
            "label_provenance_used": result.get("label_provenance_used"),
            "model_version": result.get("model_version"),
            "data_window": result.get("data_window", {}),
            "decision_policy": result.get("decision_policy", {}),
            "audit_payload": result.get("audit_payload", {}),
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

        audit_inputs = result.get("audit_payload", {}).get("inputs") or {}
        if audit_inputs:
            features_for_logging = audit_inputs
        else:
            trend_score = _find_relevant_trend(job_role, skill, as_of_date=result.get("as_of_date"))
            internal_usage = _estimate_internal_usage(job_role, skill)
            training_requests = _estimate_training_requests(job_role, skill)
            scarcity_index = _estimate_scarcity_index(job_role, skill, internal_usage)
            features_for_logging = {
                "trend_score": trend_score,
                "internal_usage": internal_usage,
                "training_requests": training_requests,
                "scarcity_index": scarcity_index,
            }

        decision_policy = result.get("decision_policy", {})
        engine_for_logging = decision_policy.get("final_engine") or engine_label

        _log_prediction_for_monitoring(
            job_role_id=job_role.id,
            skill_id=skill.id,
            predicted_level=result["level"],
            score=result["score"],
            engine=engine_for_logging,
            model_version=model_version,
            features=features_for_logging,
            confidence=result.get("confidence"),
            probabilities=result.get("probabilities"),
            label_provenance=result.get("label_provenance_used"),
            decision_policy=decision_policy,
        )

    return total_predictions


def _build_prediction_run_params(
    *,
    parameters: Dict[str, Any] | None,
    engine_label: str,
    horizon_years: int,
    use_ml_engine: bool,
    as_of_date=None,
) -> Dict[str, Any]:
    """Prepare the payload stored in PredictionRun.parameters."""
    params: Dict[str, Any] = parameters.copy() if isinstance(parameters, dict) else {}
    params["engine"] = engine_label
    params.setdefault("horizon_years", horizon_years)
    params.setdefault("horizon_months", horizon_years * 12)
    if as_of_date:
        params.setdefault("as_of_date", as_of_date.isoformat())
    params.setdefault("label_provenance_used", _resolve_label_provenance(use_ml_engine))

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

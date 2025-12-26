# future_skills/ml_model.py

"""Lightweight wrapper around the trained Future Skills ML pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

from django.conf import settings

try:  # pragma: no cover - runtime dependency guard
    import joblib  # type: ignore
except Exception as exc:  # pragma: no cover - import guard
    joblib = None  # type: ignore[assignment]
    logging.getLogger(__name__).warning("FutureSkillsModel: joblib indisponible, le modèle ML sera désactivé: %s", exc)

try:  # pragma: no cover - runtime dependency guard
    import pandas as pd  # type: ignore
except Exception as exc:  # pragma: no cover - import guard
    pd = None  # type: ignore[assignment]
    logging.getLogger(__name__).warning("FutureSkillsModel: pandas indisponible, le modèle ML sera désactivé: %s", exc)

logger = logging.getLogger(__name__)


class FutureSkillsModel:
    """Wrapper autour du pipeline scikit-learn entraîné pour le Module 3.

    - Charge le modèle une seule fois (singleton).
    - Fournit une méthode predict_level(...) qui retourne (level, score_0_100).
    """

    _instance: "FutureSkillsModel | None" = None

    def __init__(self, model_path: Path | None = None) -> None:
        """Initialize the model wrapper and eagerly load the pipeline."""
        self.model_path = Path(model_path or settings.FUTURE_SKILLS_MODEL_PATH)
        self.pipeline = None
        self._loaded = False
        self._load()

    @classmethod
    def instance(cls) -> "FutureSkillsModel":
        """Return a singleton instance of the model wrapper."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self) -> None:
        if joblib is None:
            logger.warning("FutureSkillsModel: joblib manquant, impossible de charger le modèle ML.")
            self.pipeline = None
            self._loaded = False
            return

        if not self.model_path.exists():
            logger.warning(
                "FutureSkillsModel: fichier modèle introuvable à %s. " "Fallback sur le moteur de règles.",
                self.model_path,
            )
            self.pipeline = None
            self._loaded = False
            return

        try:
            self.pipeline = joblib.load(self.model_path)
            self._loaded = True
            logger.info(
                "FutureSkillsModel: modèle ML chargé depuis %s",
                self.model_path,
            )
        except Exception as exc:  # pragma: no cover (log uniquement)
            logger.exception("FutureSkillsModel: échec du chargement du modèle ML: %s", exc)
            self.pipeline = None
            self._loaded = False

    def is_available(self) -> bool:
        """Return True if the pipeline is loaded and ready."""
        return self._loaded and self.pipeline is not None

    def predict_level(
        self,
        job_role_name: str,
        skill_name: str,
        trend_score: float,
        internal_usage: float,
        training_requests: float,
        scarcity_index: float,
    ) -> Tuple[str, float]:
        """Retourne (future_need_level, score_0_100) en utilisant le pipeline ML.

        - future_need_level ∈ {LOW, MEDIUM, HIGH}
        - score_0_100 basé sur la probabilité maximale de la prédiction.
        """
        if pd is None:
            raise RuntimeError("FutureSkillsModel: pandas n'est pas disponible pour préparer les données d'entrée.")
        if not self.is_available():
            raise RuntimeError("FutureSkillsModel: modèle ML non disponible (non chargé ou invalide).")

        data = {
            "job_role_name": [job_role_name],
            "skill_name": [skill_name],
            # Catégoriels additionnels attendus par le pipeline
            "skill_category": ["Unspecified"],
            "job_department": ["General"],
            # Numériques additionnels attendus par le pipeline
            "hiring_difficulty": [0.5],
            "avg_salary_k": [50.0],
            "economic_indicator": [0.5],
            "trend_score": [trend_score],
            "internal_usage": [internal_usage],
            "training_requests": [training_requests],
            "scarcity_index": [scarcity_index],
        }
        df = pd.DataFrame(data)

        pipeline = self.pipeline

        # Prédiction du label
        level = pipeline.predict(df)[0]

        score_0_100 = 100.0
        try:
            # Pipeline scikit-learn propage généralement predict_proba
            if hasattr(pipeline, "predict_proba"):
                proba = pipeline.predict_proba(df)[0]
                proba_max = float(proba.max())
                score_0_100 = round(proba_max * 100.0, 2)
        except Exception as exc:  # pragma: no cover (log uniquement)
            logger.warning("FutureSkillsModel: erreur lors du calcul des probabilités : %s", exc)
            # On garde le score par défaut (100.0)

        return level, score_0_100

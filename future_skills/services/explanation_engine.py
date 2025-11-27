# future_skills/services/explanation_engine.py

"""
Module pour générer des explications simplifiées des prédictions ML.

Utilise SHAP (SHapley Additive exPlanations) pour identifier les features
qui contribuent le plus à une prédiction donnée, et les traduit en phrases
compréhensibles pour les utilisateurs RH.

Exemple d'utilisation:
    from future_skills.services.explanation_engine import ExplanationEngine
    from future_skills.ml_model import FutureSkillsModel
    
    model = FutureSkillsModel.instance()
    engine = ExplanationEngine(model)
    
    explanation = engine.generate_explanation(
        job_role_name="Data Engineer",
        skill_name="Python",
        trend_score=0.85,
        internal_usage=0.3,
        training_requests=12,
        scarcity_index=0.7
    )
    
    # explanation = {
    #     "text": "Score élevé car : tendance marché forte + rareté interne importante",
    #     "top_factors": [
    #         {"feature": "trend_score", "impact": "positive", "strength": "forte"},
    #         {"feature": "scarcity_index", "impact": "positive", "strength": "importante"},
    #         {"feature": "internal_usage", "impact": "negative", "strength": "limitée"}
    #     ]
    # }
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Tentative d'import de SHAP (optionnel)
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning(
        "SHAP non disponible. Les explications détaillées ne seront pas générées. "
        "Installez avec: pip install shap"
    )


class ExplanationEngine:
    """
    Génère des explications textuelles simplifiées pour les prédictions ML.
    
    Utilise SHAP pour calculer l'importance des features et les mapper
    vers des termes compréhensibles pour les utilisateurs métier.
    """
    
    # Mapping des features techniques vers des termes métier
    FEATURE_READABLE_NAMES = {
        'trend_score': 'tendance marché',
        'scarcity_index': 'rareté interne',
        'internal_usage': 'usage interne actuel',
        'training_requests': 'demandes de formation',
        'hiring_difficulty': 'difficulté de recrutement',
        'avg_salary_k': 'niveau de salaire',
        'economic_indicator': 'indicateur économique',
        'skill_category': 'catégorie de compétence',
        'job_department': 'département métier',
    }
    
    def __init__(self, ml_model: Any) -> None:
        """
        Initialise l'ExplanationEngine.
        
        Args:
            ml_model: Instance de FutureSkillsModel contenant le pipeline ML
        """
        self.ml_model = ml_model
        self._explainer: Optional[Any] = None
        self._feature_names: Optional[List[str]] = None
        self._initialized = False
        
        if SHAP_AVAILABLE and ml_model.is_available():
            self._initialize_explainer()
    
    def _initialize_explainer(self) -> None:
        """Initialise le SHAP explainer si possible."""
        if not SHAP_AVAILABLE or not self.ml_model.is_available():
            return
        
        try:
            pipeline = self.ml_model.pipeline
            clf = pipeline.named_steps.get('clf')
            
            if clf and hasattr(clf, 'estimators_'):  # RandomForest ou similaire
                self._explainer = shap.TreeExplainer(clf)
                
                # Récupérer les noms de features après transformation
                self._feature_names = self._get_feature_names_from_pipeline(pipeline)
                
                self._initialized = True
                logger.info("ExplanationEngine: SHAP explainer initialisé avec succès")
        except Exception as exc:
            logger.warning(
                "ExplanationEngine: échec de l'initialisation SHAP: %s", exc
            )
            self._initialized = False
    
    def _get_feature_names_from_pipeline(self, pipeline: Any) -> List[str]:
        """Extrait les noms de features après preprocessing."""
        feature_names = []
        
        try:
            preprocessor = pipeline.named_steps.get('preprocess')
            if not preprocessor:
                return feature_names
            
            # Features catégorielles (OneHot encoded)
            if 'cat' in preprocessor.named_transformers_:
                cat_transformer = preprocessor.named_transformers_['cat']
                if hasattr(cat_transformer, 'get_feature_names_out'):
                    # Récupérer les features originales
                    cat_features = preprocessor.transformers_[0][2]  # Liste des colonnes cat
                    cat_names = cat_transformer.get_feature_names_out(cat_features)
                    feature_names.extend(cat_names)
            
            # Features numériques
            if 'num' in preprocessor.named_transformers_:
                num_features = preprocessor.transformers_[1][2]  # Liste des colonnes num
                feature_names.extend(num_features)
        
        except Exception as exc:
            logger.warning(
                "ExplanationEngine: erreur lors de l'extraction des feature names: %s", exc
            )
        
        return feature_names
    
    def is_available(self) -> bool:
        """Vérifie si le moteur d'explication est disponible."""
        return SHAP_AVAILABLE and self._initialized
    
    def generate_explanation(
        self,
        job_role_name: str,
        skill_name: str,
        trend_score: float,
        internal_usage: float,
        training_requests: float,
        scarcity_index: float,
        **extra_features,
    ) -> Dict[str, Any]:
        """
        Génère une explication textuelle pour une prédiction.
        
        Args:
            job_role_name: Nom du métier/rôle
            skill_name: Nom de la compétence
            trend_score: Score de tendance marché (0-1)
            internal_usage: Usage interne actuel (0-1)
            training_requests: Nombre de demandes de formation
            scarcity_index: Indice de rareté (0-1)
            **extra_features: Autres features optionnelles (hiring_difficulty, etc.)
        
        Returns:
            Dictionnaire avec:
                - text: Explication textuelle simple
                - top_factors: Liste des facteurs principaux avec leur impact
                - prediction_level: Niveau prédit (HIGH/MEDIUM/LOW)
                - confidence: Score de confiance (0-100)
        """
        # Si SHAP n'est pas disponible, retourner une explication basique
        if not self.is_available():
            return self._generate_rule_based_explanation(
                trend_score=trend_score,
                scarcity_index=scarcity_index,
                internal_usage=internal_usage,
                training_requests=training_requests,
            )
        
        try:
            # Faire la prédiction
            level, confidence = self.ml_model.predict_level(
                job_role_name=job_role_name,
                skill_name=skill_name,
                trend_score=trend_score,
                internal_usage=internal_usage,
                training_requests=training_requests,
                scarcity_index=scarcity_index,
            )
            
            # Calculer les SHAP values
            import pandas as pd
            
            data = {
                "job_role_name": [job_role_name],
                "skill_name": [skill_name],
                "trend_score": [trend_score],
                "internal_usage": [internal_usage],
                "training_requests": [training_requests],
                "scarcity_index": [scarcity_index],
            }
            data.update({k: [v] for k, v in extra_features.items()})
            
            df = pd.DataFrame(data)
            
            # Transformer les données
            preprocessor = self.ml_model.pipeline.named_steps['preprocess']
            X_transformed = preprocessor.transform(df)
            
            # Calculer SHAP values
            shap_values = self._explainer.shap_values(X_transformed)
            
            # Extraire les top factors
            top_factors = self._extract_top_factors(
                shap_values=shap_values,
                prediction_level=level,
                feature_names=self._feature_names,
            )
            
            # Générer le texte d'explication
            explanation_text = self._generate_explanation_text(
                top_factors=top_factors,
                prediction_level=level,
            )
            
            return {
                "text": explanation_text,
                "top_factors": top_factors,
                "prediction_level": level,
                "confidence": confidence,
            }
        
        except Exception as exc:
            logger.exception("ExplanationEngine: erreur lors de la génération: %s", exc)
            # Fallback sur explication basée sur des règles
            return self._generate_rule_based_explanation(
                trend_score=trend_score,
                scarcity_index=scarcity_index,
                internal_usage=internal_usage,
                training_requests=training_requests,
            )
    
    def _extract_top_factors(
        self,
        shap_values: Any,
        prediction_level: str,
        feature_names: List[str],
        top_n: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Extrait les top N features qui ont le plus contribué à la prédiction.
        
        Args:
            shap_values: SHAP values calculées
            prediction_level: Niveau prédit (HIGH/MEDIUM/LOW)
            feature_names: Noms des features
            top_n: Nombre de top features à retourner
        
        Returns:
            Liste de dicts avec feature, impact, strength
        """
        # SHAP peut retourner une liste (multi-class) ou un array (binary)
        if isinstance(shap_values, list):
            # Multi-class: identifier l'index de la classe prédite
            clf = self.ml_model.pipeline.named_steps['clf']
            class_idx = list(clf.classes_).index(prediction_level)
            shap_vals = shap_values[class_idx][0]
        else:
            shap_vals = shap_values[0]
        
        # Trier par valeur absolue (importance)
        abs_values = np.abs(shap_vals)
        top_indices = np.argsort(abs_values)[-top_n:][::-1]
        
        top_factors = []
        for idx in top_indices:
            feat_name = feature_names[idx]
            shap_val = float(shap_vals[idx])
            
            # Identifier la feature de base (sans le préfixe OneHot)
            base_feature = self._identify_base_feature(feat_name)
            
            # Déterminer l'impact et la force
            impact = "positive" if shap_val > 0 else "negative"
            
            # Seuils pour la force
            abs_val = abs(shap_val)
            if abs_val > 0.3:
                strength = "très forte" if impact == "positive" else "très faible"
            elif abs_val > 0.15:
                strength = "forte" if impact == "positive" else "faible"
            else:
                strength = "modérée" if impact == "positive" else "limitée"
            
            # Nom lisible
            readable_name = self.FEATURE_READABLE_NAMES.get(base_feature, base_feature)
            
            top_factors.append({
                "feature": base_feature,
                "feature_readable": readable_name,
                "impact": impact,
                "strength": strength,
                "shap_value": round(shap_val, 4),
            })
        
        return top_factors
    
    def _identify_base_feature(self, feature_name: str) -> str:
        """Identifie la feature de base à partir du nom transformé."""
        # Nettoyer les préfixes OneHot (ex: "cat__job_role_name_Data Engineer" -> "job_role_name")
        for base_feat in self.FEATURE_READABLE_NAMES.keys():
            if base_feat in feature_name.lower():
                return base_feat
        
        # Si pas trouvé, retourner le nom nettoyé
        return feature_name.replace("cat__", "").replace("num__", "").split("_")[0]
    
    def _generate_explanation_text(
        self,
        top_factors: List[Dict[str, Any]],
        prediction_level: str,
    ) -> str:
        """
        Génère une phrase d'explication simple.
        
        Args:
            top_factors: Liste des facteurs principaux
            prediction_level: Niveau prédit
        
        Returns:
            Phrase d'explication
        """
        # Préfixe selon le niveau
        if prediction_level == "HIGH":
            prefix = "Score élevé car :"
        elif prediction_level == "MEDIUM":
            prefix = "Score modéré car :"
        else:
            prefix = "Score faible car :"
        
        # Construire la liste des facteurs
        parts = []
        for factor in top_factors:
            readable = factor["feature_readable"]
            strength = factor["strength"]
            parts.append(f"{readable} {strength}")
        
        if parts:
            return f"{prefix} {' + '.join(parts)}"
        else:
            return f"{prefix} multiple facteurs combinés"
    
    def _generate_rule_based_explanation(
        self,
        trend_score: float,
        scarcity_index: float,
        internal_usage: float,
        training_requests: float,
    ) -> Dict[str, Any]:
        """
        Génère une explication simple basée sur des règles (fallback sans SHAP).
        
        Args:
            trend_score: Score de tendance (0-1)
            scarcity_index: Indice de rareté (0-1)
            internal_usage: Usage interne (0-1)
            training_requests: Demandes de formation
        
        Returns:
            Dict avec explication simple
        """
        # Calculer un niveau basique
        score = (trend_score * 0.4 + scarcity_index * 0.3 + 
                 (1 - internal_usage) * 0.2 + min(training_requests / 10, 1) * 0.1)
        
        if score >= 0.7:
            level = "HIGH"
            prefix = "Score élevé car :"
        elif score >= 0.4:
            level = "MEDIUM"
            prefix = "Score modéré car :"
        else:
            level = "LOW"
            prefix = "Score faible car :"
        
        # Identifier les facteurs principaux
        factors = []
        
        if trend_score > 0.7:
            factors.append("tendance marché forte")
        elif trend_score < 0.3:
            factors.append("tendance marché faible")
        
        if scarcity_index > 0.7:
            factors.append("rareté interne importante")
        elif scarcity_index < 0.3:
            factors.append("rareté interne limitée")
        
        if internal_usage < 0.3:
            factors.append("usage interne faible")
        elif internal_usage > 0.7:
            factors.append("usage interne déjà satisfaisant")
        
        if training_requests > 5:
            factors.append("demandes de formation nombreuses")
        
        explanation = f"{prefix} {' + '.join(factors)}" if factors else f"{prefix} facteurs variés"
        
        return {
            "text": explanation,
            "top_factors": [
                {
                    "feature": "trend_score",
                    "feature_readable": "tendance marché",
                    "impact": "positive" if trend_score > 0.5 else "negative",
                    "strength": "forte" if trend_score > 0.7 else "modérée",
                },
                {
                    "feature": "scarcity_index",
                    "feature_readable": "rareté interne",
                    "impact": "positive" if scarcity_index > 0.5 else "negative",
                    "strength": "importante" if scarcity_index > 0.7 else "modérée",
                },
                {
                    "feature": "internal_usage",
                    "feature_readable": "usage interne actuel",
                    "impact": "negative" if internal_usage > 0.5 else "positive",
                    "strength": "limitée" if internal_usage > 0.7 else "modérée",
                },
            ],
            "prediction_level": level,
            "confidence": round(score * 100, 2),
        }

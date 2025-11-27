# 🔍 LT-1 — Explainability Documentation

## Vue d'ensemble

Le système d'explicabilité permet de répondre à la question **"Pourquoi le modèle recommande-t-il cette compétence comme HIGH/MEDIUM/LOW ?"** en utilisant des techniques d'explicabilité ML (SHAP/LIME).

## Architecture

### Composants principaux

1. **`ml/explainability_analysis.ipynb`**

   - Notebook Jupyter pour analyse interactive
   - Démonstrations SHAP et LIME sur des exemples
   - Visualisations des contributions des features
   - Extraction de patterns d'importance

2. **`future_skills/services/explanation_engine.py`**

   - Module Python pour génération automatique d'explications
   - Utilise SHAP (SHapley Additive exPlanations)
   - Traduit les valeurs SHAP en phrases simples
   - Fallback sur explications basées sur des règles

3. **`future_skills/models.py`** (champ `explanation`)

   - Champ JSONField optionnel sur `FutureSkillPrediction`
   - Stocke : `text`, `top_factors`, `prediction_level`, `confidence`

4. **`future_skills/services/prediction_engine.py`**
   - Intégration du `ExplanationEngine`
   - Génération optionnelle via paramètre `generate_explanations=True`

---

## Format d'explication

### Structure JSON

```json
{
  "text": "Score élevé car : tendance marché forte + rareté interne importante",
  "top_factors": [
    {
      "feature": "trend_score",
      "feature_readable": "tendance marché",
      "impact": "positive",
      "strength": "forte",
      "shap_value": 0.3245
    },
    {
      "feature": "scarcity_index",
      "feature_readable": "rareté interne",
      "impact": "positive",
      "strength": "importante",
      "shap_value": 0.2156
    },
    {
      "feature": "internal_usage",
      "feature_readable": "usage interne actuel",
      "impact": "negative",
      "strength": "limitée",
      "shap_value": -0.0823
    }
  ],
  "prediction_level": "HIGH",
  "confidence": 87.5
}
```

### Mapping des features

Le `ExplanationEngine` mappe les features techniques vers des termes métier :

| Feature technique    | Terme métier              |
| -------------------- | ------------------------- |
| `trend_score`        | tendance marché           |
| `scarcity_index`     | rareté interne            |
| `internal_usage`     | usage interne actuel      |
| `training_requests`  | demandes de formation     |
| `hiring_difficulty`  | difficulté de recrutement |
| `avg_salary_k`       | niveau de salaire         |
| `economic_indicator` | indicateur économique     |

### Force de l'impact

Les SHAP values sont traduites en termes de force :

- **Impact positif** (pousse vers HIGH) :

  - `|shap_value| > 0.3` → "très forte"
  - `|shap_value| > 0.15` → "forte"
  - sinon → "modérée"

- **Impact négatif** (pousse vers LOW) :
  - `|shap_value| > 0.3` → "très faible"
  - `|shap_value| > 0.15` → "faible"
  - sinon → "limitée"

---

## Utilisation

### 1. Dans le notebook (analyse interactive)

```python
# Ouvrir ml/explainability_analysis.ipynb
# Exécuter les cellules pour :
# - Charger le modèle et le dataset
# - Sélectionner des exemples HIGH/MEDIUM
# - Visualiser les SHAP values (waterfall, force plots)
# - Générer des explications simplifiées
```

### 2. Via l'API Python

```python
from future_skills.services.explanation_engine import ExplanationEngine
from future_skills.ml_model import FutureSkillsModel

# Charger le modèle
model = FutureSkillsModel.instance()

# Créer l'engine
engine = ExplanationEngine(model)

# Générer une explication
explanation = engine.generate_explanation(
    job_role_name="Data Engineer",
    skill_name="Python",
    trend_score=0.85,
    internal_usage=0.3,
    training_requests=12,
    scarcity_index=0.7
)

print(explanation["text"])
# Output: "Score élevé car : tendance marché forte + rareté interne importante"

for factor in explanation["top_factors"]:
    print(f"  • {factor['feature_readable']}: {factor['strength']}")
```

### 3. Dans le moteur de prédiction

```python
from future_skills.services.prediction_engine import recalculate_predictions

# Recalculer avec génération d'explications
total = recalculate_predictions(
    horizon_years=5,
    generate_explanations=True  # Génère les explications
)
```

### 4. Vérifier les explications en DB

```python
from future_skills.models import FutureSkillPrediction

# Récupérer une prédiction avec explication
prediction = FutureSkillPrediction.objects.filter(
    explanation__isnull=False
).first()

if prediction:
    print(f"Job: {prediction.job_role}")
    print(f"Skill: {prediction.skill}")
    print(f"Level: {prediction.level}")
    print(f"\nExplication: {prediction.explanation['text']}")

    print("\nTop factors:")
    for factor in prediction.explanation['top_factors']:
        print(f"  • {factor['feature_readable']}: {factor['strength']}")
```

---

## Intégration API (future)

### Option 1 : Endpoint dédié

```python
# future_skills/views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from future_skills.models import FutureSkillPrediction
from future_skills.services.explanation_engine import ExplanationEngine
from future_skills.ml_model import FutureSkillsModel

@api_view(['GET'])
def explain_prediction(request, prediction_id):
    """
    GET /api/future-skills/predictions/{id}/explain/

    Génère une explication à la volée pour une prédiction donnée.
    """
    try:
        prediction = FutureSkillPrediction.objects.get(pk=prediction_id)
    except FutureSkillPrediction.DoesNotExist:
        return Response({"error": "Prediction not found"}, status=404)

    # Si explication déjà stockée, la retourner
    if prediction.explanation:
        return Response(prediction.explanation)

    # Sinon, la générer à la volée
    model = FutureSkillsModel.instance()
    engine = ExplanationEngine(model)

    # Récupérer les features utilisées (depuis les calculs internes)
    # Note : il faudrait stocker ces valeurs ou les recalculer
    explanation = engine.generate_explanation(
        job_role_name=prediction.job_role.name,
        skill_name=prediction.skill.name,
        trend_score=0.5,  # À calculer dynamiquement
        internal_usage=0.5,
        training_requests=10,
        scarcity_index=0.5,
    )

    return Response(explanation)
```

### Option 2 : Paramètre optionnel sur listing

```python
# future_skills/serializers.py

from rest_framework import serializers
from future_skills.models import FutureSkillPrediction

class FutureSkillPredictionSerializer(serializers.ModelSerializer):
    explanation_text = serializers.SerializerMethodField()

    class Meta:
        model = FutureSkillPrediction
        fields = [
            'id', 'job_role', 'skill', 'score', 'level',
            'rationale', 'explanation', 'explanation_text'
        ]

    def get_explanation_text(self, obj):
        """Retourne uniquement le texte d'explication si disponible."""
        if obj.explanation:
            return obj.explanation.get('text')
        return None

# future_skills/views.py

class FutureSkillPredictionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FutureSkillPrediction.objects.all()
    serializer_class = FutureSkillPredictionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Paramètre optionnel : ?include_explanation=true
        if self.request.query_params.get('include_explanation') == 'true':
            # Ne retourner que les prédictions avec explication
            queryset = queryset.filter(explanation__isnull=False)

        return queryset
```

### Exemples de requêtes

```bash
# Récupérer toutes les prédictions
GET /api/future-skills/predictions/

# Récupérer uniquement celles avec explications
GET /api/future-skills/predictions/?include_explanation=true

# Récupérer l'explication d'une prédiction spécifique
GET /api/future-skills/predictions/123/explain/

# Réponse JSON
{
  "text": "Score élevé car : tendance marché forte + rareté interne importante",
  "top_factors": [
    {
      "feature": "trend_score",
      "feature_readable": "tendance marché",
      "impact": "positive",
      "strength": "forte",
      "shap_value": 0.3245
    },
    ...
  ],
  "prediction_level": "HIGH",
  "confidence": 87.5
}
```

---

## Intégration UI (future)

### Carte d'explication

```html
<!-- Template exemple pour afficher une explication -->
<div class="skill-recommendation-card">
  <div class="header">
    <h3>{{ skill.name }}</h3>
    <span class="badge badge-{{ level|lower }}">{{ level }}</span>
  </div>

  <div class="score">Score : {{ score }}/100</div>

  <div class="explanation" v-if="prediction.explanation">
    <h4>💡 Pourquoi cette recommandation ?</h4>
    <p class="explanation-text">{{ prediction.explanation.text }}</p>

    <div class="factors">
      <h5>Facteurs clés :</h5>
      <ul>
        <li
          v-for="factor in prediction.explanation.top_factors"
          :key="factor.feature"
        >
          <span class="factor-name">{{ factor.feature_readable }}</span>
          <span class="factor-impact" :class="factor.impact">
            {{ factor.strength }}
          </span>
        </li>
      </ul>
    </div>
  </div>

  <div class="rationale">
    <details>
      <summary>Détails techniques</summary>
      <p>{{ prediction.rationale }}</p>
    </details>
  </div>
</div>
```

### Widget interactif

```vue
<template>
  <div class="explainability-widget">
    <button @click="loadExplanation" :disabled="loading">
      🔍 Pourquoi cette compétence ?
    </button>

    <div v-if="explanation" class="explanation-modal">
      <h3>Explication de la recommandation</h3>

      <div class="prediction-info">
        <span class="level">{{ explanation.prediction_level }}</span>
        <span class="confidence"
          >Confiance : {{ explanation.confidence }}%</span
        >
      </div>

      <p class="explanation-text">{{ explanation.text }}</p>

      <div class="factors-chart">
        <!-- Barre horizontale pour chaque facteur -->
        <div
          v-for="factor in explanation.top_factors"
          :key="factor.feature"
          class="factor-bar"
        >
          <span class="factor-label">{{ factor.feature_readable }}</span>
          <div
            class="bar"
            :style="{ width: Math.abs(factor.shap_value) * 100 + '%' }"
          >
            <span class="bar-value">{{ factor.strength }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    predictionId: Number,
  },
  data() {
    return {
      explanation: null,
      loading: false,
    };
  },
  methods: {
    async loadExplanation() {
      this.loading = true;
      try {
        const response = await fetch(
          `/api/future-skills/predictions/${this.predictionId}/explain/`
        );
        this.explanation = await response.json();
      } catch (error) {
        console.error("Failed to load explanation:", error);
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>
```

---

## Installation et dépendances

### Requirements

```bash
# Installer les dépendances ML supplémentaires
pip install -r requirements_ml.txt
```

Le fichier `requirements_ml.txt` inclut maintenant :

- `shap>=0.44.0` (pour explainability)
- `lime>=0.2.0.1` (alternative)
- `matplotlib>=3.7.0` (visualisations)
- `seaborn>=0.12.0` (visualisations)

### Vérification

```python
# Vérifier que SHAP est disponible
from future_skills.services.explanation_engine import SHAP_AVAILABLE
print(f"SHAP disponible : {SHAP_AVAILABLE}")

# Tester l'engine
from future_skills.services.explanation_engine import ExplanationEngine
from future_skills.ml_model import FutureSkillsModel

model = FutureSkillsModel.instance()
engine = ExplanationEngine(model)
print(f"Explanation engine disponible : {engine.is_available()}")
```

---

## Bonnes pratiques

### 1. Performance

- **Génération à la demande** : Les explications SHAP sont coûteuses. Ne les générer que quand nécessaire.
- **Mise en cache** : Stocker les explications dans le champ `explanation` du modèle.
- **Batch processing** : Pour recalculer toutes les explications, utiliser `generate_explanations=True` lors du `recalculate_predictions()`.

### 2. Fallback gracieux

- Si SHAP n'est pas installé, le système utilise des explications basées sur des règles.
- Si le modèle ML n'est pas disponible, les explications ne sont pas générées.

### 3. Validation

- Vérifier la cohérence entre `rationale` (texte simple) et `explanation` (JSON structuré).
- Tester les explications sur différents niveaux (HIGH/MEDIUM/LOW).

### 4. Documentation utilisateur

- Expliquer clairement ce que signifie chaque facteur.
- Utiliser un langage métier, pas technique.
- Fournir des exemples concrets.

---

## Tests

### Test unitaire d'ExplanationEngine

```python
# future_skills/tests/test_explanation_engine.py

from django.test import TestCase
from future_skills.services.explanation_engine import ExplanationEngine
from future_skills.ml_model import FutureSkillsModel

class ExplanationEngineTestCase(TestCase):
    def setUp(self):
        self.model = FutureSkillsModel.instance()
        self.engine = ExplanationEngine(self.model)

    def test_generate_explanation(self):
        """Test génération d'explication basique."""
        explanation = self.engine.generate_explanation(
            job_role_name="Data Engineer",
            skill_name="Python",
            trend_score=0.85,
            internal_usage=0.3,
            training_requests=12,
            scarcity_index=0.7
        )

        # Vérifier la structure
        self.assertIn("text", explanation)
        self.assertIn("top_factors", explanation)
        self.assertIn("prediction_level", explanation)
        self.assertIn("confidence", explanation)

        # Vérifier les valeurs
        self.assertIsInstance(explanation["text"], str)
        self.assertGreater(len(explanation["top_factors"]), 0)
        self.assertIn(explanation["prediction_level"], ["LOW", "MEDIUM", "HIGH"])

    def test_fallback_without_shap(self):
        """Test fallback sur explications règles si SHAP indisponible."""
        # Même si SHAP n'est pas dispo, l'engine devrait retourner une explication
        explanation = self.engine._generate_rule_based_explanation(
            trend_score=0.8,
            scarcity_index=0.6,
            internal_usage=0.4,
            training_requests=8
        )

        self.assertIn("text", explanation)
        self.assertIn("top_factors", explanation)
```

### Test d'intégration

```python
# future_skills/tests/test_prediction_with_explanation.py

from django.test import TestCase
from future_skills.models import JobRole, Skill, FutureSkillPrediction
from future_skills.services.prediction_engine import recalculate_predictions

class PredictionExplanationTestCase(TestCase):
    def setUp(self):
        self.job_role = JobRole.objects.create(name="Test Role")
        self.skill = Skill.objects.create(name="Test Skill")

    def test_recalculate_with_explanations(self):
        """Test recalcul avec génération d'explications."""
        total = recalculate_predictions(
            horizon_years=3,
            generate_explanations=True
        )

        self.assertGreater(total, 0)

        # Vérifier qu'au moins une prédiction a une explication
        predictions_with_explanation = FutureSkillPrediction.objects.filter(
            explanation__isnull=False
        )

        # Si le modèle ML est disponible, il devrait y avoir des explications
        if predictions_with_explanation.exists():
            prediction = predictions_with_explanation.first()
            self.assertIn("text", prediction.explanation)
            self.assertIn("top_factors", prediction.explanation)
```

---

## Troubleshooting

### SHAP non disponible

**Symptôme** : `SHAP_AVAILABLE = False`

**Solution** :

```bash
pip install shap
```

### Explainer non initialisé

**Symptôme** : `engine.is_available() = False`

**Causes possibles** :

1. Modèle ML non chargé → vérifier `FUTURE_SKILLS_MODEL_PATH`
2. SHAP non installé → installer `shap`
3. Modèle incompatible → vérifier que c'est bien un RandomForest

### Performance lente

**Symptôme** : Génération d'explications très lente

**Solutions** :

1. Réduire le nombre d'exemples
2. Utiliser `TreeExplainer` (optimisé pour RandomForest)
3. Ne générer des explications que pour les prédictions HIGH

---

## Ressources

### Documentation SHAP

- [SHAP GitHub](https://github.com/slundberg/shap)
- [SHAP Documentation](https://shap.readthedocs.io/)

### Documentation LIME

- [LIME GitHub](https://github.com/marcotcr/lime)

### Articles de référence

- Lundberg, S. M., & Lee, S. I. (2017). A unified approach to interpreting model predictions. NeurIPS.
- Ribeiro, M. T., Singh, S., & Guestrin, C. (2016). "Why should I trust you?" Explaining the predictions of any classifier. KDD.

---

## Prochaines étapes

- [ ] Ajouter l'endpoint `/api/future-skills/predictions/{id}/explain/`
- [ ] Créer le serializer avec champ `explanation_text`
- [ ] Implémenter le widget UI avec visualisations
- [ ] Ajouter des tests E2E pour l'API
- [ ] Documenter dans le guide utilisateur RH
- [ ] Créer des exemples d'explications pour la formation

---

**Dernière mise à jour** : Novembre 2025  
**Auteur** : Équipe SmartHR360 ML

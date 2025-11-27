# 🔍 Explainability (SHAP/LIME) - README

## Introduction

Ce dossier contient l'implémentation complète du **LT-1 — Explainability** pour le Module 3 Future Skills. L'objectif est d'expliquer **pourquoi** le modèle ML recommande une compétence comme HIGH, MEDIUM ou LOW en utilisant SHAP (SHapley Additive exPlanations) et LIME.

---

## 📋 Table des matières

1. [Fichiers créés](#-fichiers-créés)
2. [Installation rapide](#-installation-rapide)
3. [Démarrage rapide](#-démarrage-rapide)
4. [Documentation](#-documentation)
5. [Architecture](#-architecture)
6. [Prochaines étapes](#-prochaines-étapes)

---

## 📁 Fichiers créés

### Nouveaux fichiers

| Fichier                                                  | Description                                 |
| -------------------------------------------------------- | ------------------------------------------- |
| `ml/explainability_analysis.ipynb`                       | Notebook interactif avec analyses SHAP/LIME |
| `future_skills/services/explanation_engine.py`           | Moteur de génération d'explications         |
| `future_skills/migrations/0005_add_explanation_field.py` | Migration DB pour champ `explanation`       |
| `docs/LT1_EXPLAINABILITY_GUIDE.md`                       | Guide complet d'explicabilité               |
| `docs/LT1_COMPLETION_SUMMARY.md`                         | Résumé de l'implémentation                  |
| `docs/LT1_QUICK_COMMANDS.md`                             | Commandes rapides                           |
| `ml/README_EXPLAINABILITY.md`                            | Ce fichier                                  |

### Fichiers modifiés

| Fichier                                       | Modifications                            |
| --------------------------------------------- | ---------------------------------------- |
| `requirements_ml.txt`                         | Ajout de shap, lime, matplotlib, seaborn |
| `future_skills/models.py`                     | Ajout du champ `explanation` (JSONField) |
| `future_skills/services/prediction_engine.py` | Intégration de l'ExplanationEngine       |
| `QUICK_COMMANDS.md`                           | Section Explainability                   |

---

## 🚀 Installation rapide

```bash
# 1. Installer les dépendances
pip install -r requirements_ml.txt

# 2. Appliquer la migration
python manage.py migrate future_skills

# 3. Vérifier que SHAP est disponible
python -c "import shap; print(f'✅ SHAP version: {shap.__version__}')"
```

---

## ⚡ Démarrage rapide

### Option 1 : Analyse interactive (Notebook)

```bash
# Lancer le notebook Jupyter
jupyter notebook ml/explainability_analysis.ipynb

# Ou avec JupyterLab
jupyter lab ml/explainability_analysis.ipynb
```

Le notebook contient :

- ✅ Analyses SHAP sur exemples HIGH/MEDIUM
- ✅ Visualisations (force plots, waterfall, summary)
- ✅ Analyses LIME alternatives
- ✅ Génération d'explications simplifiées

### Option 2 : Génération programmatique

```python
from future_skills.services.explanation_engine import ExplanationEngine
from future_skills.ml_model import FutureSkillsModel

# Charger le modèle
model = FutureSkillsModel.instance()
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
```

### Option 3 : Recalcul complet avec explications

```python
from future_skills.services.prediction_engine import recalculate_predictions

# Recalculer toutes les prédictions avec génération d'explications
total = recalculate_predictions(
    horizon_years=5,
    generate_explanations=True  # Active SHAP
)

print(f"✅ {total} prédictions générées avec explications")
```

---

## 📖 Documentation

### Documents clés

1. **[LT1_EXPLAINABILITY_GUIDE.md](docs/LT1_EXPLAINABILITY_GUIDE.md)** - Guide complet

   - Architecture détaillée
   - Format d'explication JSON
   - Exemples d'utilisation
   - Intégration API/UI
   - Tests et troubleshooting

2. **[LT1_COMPLETION_SUMMARY.md](docs/LT1_COMPLETION_SUMMARY.md)** - Résumé d'implémentation

   - Objectifs atteints ✅
   - Composants créés
   - Exemples concrets
   - Prochaines étapes

3. **[LT1_QUICK_COMMANDS.md](docs/LT1_QUICK_COMMANDS.md)** - Commandes rapides
   - Installation
   - Tests
   - Debugging
   - Maintenance

### Ordre de lecture recommandé

1. Ce README (vue d'ensemble)
2. `LT1_COMPLETION_SUMMARY.md` (qu'est-ce qui a été fait ?)
3. `LT1_EXPLAINABILITY_GUIDE.md` (comment ça marche ?)
4. `LT1_QUICK_COMMANDS.md` (comment l'utiliser ?)

---

## 🏗️ Architecture

### Flux de données

```
┌─────────────────────┐
│   ML Model          │
│  (RandomForest)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ ExplanationEngine   │
│  - SHAP Calculator  │
│  - Feature Mapper   │
│  - Text Generator   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Explanation       │
│  {                  │
│    text: "...",     │
│    top_factors: [], │
│    confidence: 87.5 │
│  }                  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ FutureSkillPrediction│
│  .explanation       │
│  (JSONField)        │
└─────────────────────┘
```

### Composants principaux

1. **ExplanationEngine** (`future_skills/services/explanation_engine.py`)

   - Calcule les SHAP values
   - Identifie les top features
   - Génère du texte simple
   - Fallback gracieux si SHAP indisponible

2. **Notebook** (`ml/explainability_analysis.ipynb`)

   - Analyse interactive
   - Visualisations riches
   - Expérimentation

3. **Modèle DB** (`future_skills/models.py`)

   - Champ `explanation` (JSONField)
   - Stockage persistant
   - Requêtes optimisées

4. **Intégration** (`future_skills/services/prediction_engine.py`)
   - Paramètre `generate_explanations`
   - Génération optionnelle
   - Logging détaillé

---

## 🎯 Format d'explication

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
    }
  ],
  "prediction_level": "HIGH",
  "confidence": 87.5
}
```

### Mapping des features

| Feature technique   | Terme métier          |
| ------------------- | --------------------- |
| `trend_score`       | tendance marché       |
| `scarcity_index`    | rareté interne        |
| `internal_usage`    | usage interne actuel  |
| `training_requests` | demandes de formation |

---

## 🧪 Tests

### Vérifier l'installation

```bash
# Test 1 : SHAP disponible
python -c "import shap; print('✅ SHAP OK')"

# Test 2 : ExplanationEngine chargeable
python manage.py shell -c "from future_skills.services.explanation_engine import ExplanationEngine; print('✅ Engine OK')"

# Test 3 : Migration appliquée
python manage.py showmigrations future_skills | grep "0005_add_explanation_field"
```

### Générer un exemple

```python
python manage.py shell
>>> from future_skills.services.explanation_engine import ExplanationEngine
>>> from future_skills.ml_model import FutureSkillsModel
>>>
>>> model = FutureSkillsModel.instance()
>>> if not model.is_available():
>>>     print("⚠️  Modèle ML non disponible - entraîner d'abord")
>>>     exit()
>>>
>>> engine = ExplanationEngine(model)
>>> if not engine.is_available():
>>>     print("⚠️  SHAP non disponible - vérifier installation")
>>>     exit()
>>>
>>> explanation = engine.generate_explanation(
...     job_role_name="Data Engineer",
...     skill_name="Python",
...     trend_score=0.85,
...     internal_usage=0.3,
...     training_requests=12,
...     scarcity_index=0.7
... )
>>>
>>> print("\n✅ EXPLICATION GÉNÉRÉE:")
>>> print(f"   {explanation['text']}")
>>> print(f"\n   Niveau: {explanation['prediction_level']}")
>>> print(f"   Confiance: {explanation['confidence']}%")
>>> print("\n   Top factors:")
>>> for factor in explanation['top_factors']:
...     print(f"     • {factor['feature_readable']}: {factor['strength']}")
```

---

## 🚦 Prochaines étapes

### Phase 1 : Validation (court terme)

- [x] ✅ Notebook d'analyse créé
- [x] ✅ ExplanationEngine implémenté
- [x] ✅ Champ DB ajouté
- [x] ✅ Documentation complète
- [ ] Tester sur dataset réel
- [ ] Ajuster les seuils de force

### Phase 2 : API Backend (moyen terme)

- [ ] Créer endpoint `/api/predictions/{id}/explain/`
- [ ] Ajouter paramètre `?include_explanation=true`
- [ ] Serializer avec `explanation_text`
- [ ] Tests API

### Phase 3 : UI Frontend (long terme)

- [ ] Widget "Pourquoi cette compétence ?"
- [ ] Cartes d'explication
- [ ] Visualisations interactives
- [ ] Tests utilisateurs RH

### Phase 4 : Optimisation (futur)

- [ ] Cache des explications
- [ ] Batch processing
- [ ] A/B testing formats
- [ ] Personnalisation par rôle

---

## 💡 Conseils d'utilisation

### Performance

⚠️ **SHAP est coûteux** : Génération d'explications = ~1-2 secondes par prédiction

✅ **Solutions** :

1. Générer en batch (lors du recalcul nocturne)
2. Stocker dans DB (champ `explanation`)
3. Générer à la demande uniquement pour HIGH

### Fallback

Si SHAP indisponible, l'engine utilise des règles simples :

- Analyse des seuils (trend_score > 0.7, etc.)
- Explications basiques mais compréhensibles
- Dégradation gracieuse

### Debug

```bash
# Vérifier les logs
tail -f logs/predictions.log | grep -i "explanation"

# Compter les explications générées
python manage.py shell -c "from future_skills.models import FutureSkillPrediction; print(FutureSkillPrediction.objects.filter(explanation__isnull=False).count())"
```

---

## 🎓 Ressources

- **SHAP** : https://github.com/slundberg/shap
- **LIME** : https://github.com/marcotcr/lime
- **Paper SHAP** : [Lundberg & Lee (2017)](https://arxiv.org/abs/1705.07874)
- **Paper LIME** : [Ribeiro et al. (2016)](https://arxiv.org/abs/1602.04938)

---

## 📞 Support

Pour toute question :

1. Consulter `docs/LT1_EXPLAINABILITY_GUIDE.md`
2. Voir `docs/LT1_QUICK_COMMANDS.md`
3. Vérifier les logs : `logs/predictions.log`
4. Contacter l'équipe ML SmartHR360

---

**Status** : ✅ LT-1 Complet  
**Version** : 1.0  
**Date** : Novembre 2025

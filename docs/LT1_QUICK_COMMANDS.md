# 🔍 LT-1 Explainability - Quick Commands

## Installation

```bash
# Installer les dépendances
pip install -r requirements_ml.txt

# Vérifier que SHAP est disponible
python -c "import shap; print(f'SHAP version: {shap.__version__}')"
```

## Migrations

```bash
# Appliquer la migration pour le champ explanation
python manage.py migrate future_skills

# Vérifier la migration
python manage.py showmigrations future_skills
```

## Notebook

```bash
# Lancer Jupyter pour l'analyse interactive
jupyter notebook ml/explainability_analysis.ipynb

# Ou avec JupyterLab
jupyter lab ml/explainability_analysis.ipynb
```

## Tests Python

```bash
# Tester SHAP disponible
python manage.py shell
>>> from future_skills.services.explanation_engine import SHAP_AVAILABLE
>>> print(f"SHAP disponible: {SHAP_AVAILABLE}")

# Tester ExplanationEngine
>>> from future_skills.services.explanation_engine import ExplanationEngine
>>> from future_skills.ml_model import FutureSkillsModel
>>> model = FutureSkillsModel.instance()
>>> engine = ExplanationEngine(model)
>>> print(f"Engine disponible: {engine.is_available()}")
>>>
>>> # Générer une explication
>>> explanation = engine.generate_explanation(
...     job_role_name="Data Engineer",
...     skill_name="Python",
...     trend_score=0.85,
...     internal_usage=0.3,
...     training_requests=12,
...     scarcity_index=0.7
... )
>>> print(explanation["text"])
```

## Recalcul avec explications

```bash
# Option 1 : Via management command (à créer)
python manage.py recalculate_future_skills --generate-explanations

# Option 2 : Via shell
python manage.py shell
>>> from future_skills.services.prediction_engine import recalculate_predictions
>>> total = recalculate_predictions(horizon_years=5, generate_explanations=True)
>>> print(f"Prédictions générées: {total}")
```

## Vérifier les explications en DB

```bash
python manage.py shell
>>> from future_skills.models import FutureSkillPrediction
>>>
>>> # Compter les prédictions avec explication
>>> count = FutureSkillPrediction.objects.filter(explanation__isnull=False).count()
>>> print(f"Prédictions avec explication: {count}")
>>>
>>> # Afficher une explication
>>> pred = FutureSkillPrediction.objects.filter(explanation__isnull=False).first()
>>> if pred:
...     print(f"\nJob: {pred.job_role.name}")
...     print(f"Skill: {pred.skill.name}")
...     print(f"Level: {pred.level}")
...     print(f"\nExplication: {pred.explanation['text']}")
...     print("\nTop factors:")
...     for factor in pred.explanation['top_factors']:
...         print(f"  • {factor['feature_readable']}: {factor['strength']}")
```

## Tests unitaires

```bash
# Lancer les tests du module explainability
python manage.py test future_skills.tests.test_explanation_engine

# Lancer tous les tests
python manage.py test future_skills

# Avec coverage
coverage run --source='.' manage.py test future_skills
coverage report
coverage html
```

## Debugging

```bash
# Vérifier le modèle ML
python manage.py shell
>>> from future_skills.ml_model import FutureSkillsModel
>>> model = FutureSkillsModel.instance()
>>> print(f"Modèle disponible: {model.is_available()}")
>>> print(f"Chemin: {model.model_path}")

# Vérifier le pipeline
>>> if model.is_available():
...     print(f"Pipeline: {model.pipeline.named_steps.keys()}")
...     clf = model.pipeline.named_steps['clf']
...     print(f"Classes: {clf.classes_}")
...     print(f"Features: {clf.n_features_in_}")
```

## Export de données

```bash
# Exporter les prédictions avec explications au format JSON
python manage.py shell
>>> from future_skills.models import FutureSkillPrediction
>>> import json
>>>
>>> predictions = FutureSkillPrediction.objects.filter(
...     explanation__isnull=False
... ).select_related('job_role', 'skill')
>>>
>>> data = []
>>> for pred in predictions[:10]:  # Top 10
...     data.append({
...         'job_role': pred.job_role.name,
...         'skill': pred.skill.name,
...         'level': pred.level,
...         'score': pred.score,
...         'explanation': pred.explanation
...     })
>>>
>>> with open('explanations_export.json', 'w', encoding='utf-8') as f:
...     json.dump(data, f, indent=2, ensure_ascii=False)
>>>
>>> print("Exported to explanations_export.json")
```

## API (une fois implémentée)

```bash
# Tester l'endpoint d'explication
curl -X GET "http://localhost:8000/api/future-skills/predictions/1/explain/" \
  -H "Authorization: Token YOUR_TOKEN"

# Lister avec explications
curl -X GET "http://localhost:8000/api/future-skills/predictions/?include_explanation=true" \
  -H "Authorization: Token YOUR_TOKEN"
```

## Maintenance

```bash
# Nettoyer les explications existantes
python manage.py shell
>>> from future_skills.models import FutureSkillPrediction
>>> FutureSkillPrediction.objects.update(explanation=None)
>>> print("Explications nettoyées")

# Regénérer toutes les explications
>>> from future_skills.services.prediction_engine import recalculate_predictions
>>> total = recalculate_predictions(horizon_years=5, generate_explanations=True)
>>> print(f"Régénéré: {total} prédictions avec explications")
```

## Performance monitoring

```bash
# Mesurer le temps de génération d'explications
python manage.py shell
>>> import time
>>> from future_skills.services.explanation_engine import ExplanationEngine
>>> from future_skills.ml_model import FutureSkillsModel
>>>
>>> model = FutureSkillsModel.instance()
>>> engine = ExplanationEngine(model)
>>>
>>> start = time.time()
>>> explanation = engine.generate_explanation(
...     job_role_name="Data Engineer",
...     skill_name="Python",
...     trend_score=0.85,
...     internal_usage=0.3,
...     training_requests=12,
...     scarcity_index=0.7
... )
>>> elapsed = time.time() - start
>>> print(f"Temps de génération: {elapsed:.3f}s")
```

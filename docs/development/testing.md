# Tests & Couverture — Module 3 : Future Skills

## 1. Outil de couverture

Pour mesurer la qualité des tests du Module 3, nous utilisons **coverage.py**.

- Installation dans l'environnement virtuel :

  ```bash
  pip install coverage
  ```

- Fichier de configuration à la racine du projet : `.coveragerc` :

  ```ini
  [run]
  source = future_skills
  branch = True

  [report]
  omit =
      */migrations/*
      */tests/*
      config/*
  show_missing = True
  ```

## 2. Commandes utilisées

Pour exécuter les tests du Module 3 avec mesure de couverture :

```bash
coverage run manage.py test future_skills
coverage report
```

(Optionnel) Pour générer un rapport HTML détaillé :

```bash
coverage html
```

Le rapport est ensuite consultable via `htmlcov/index.html`.

## 3. Résultats de couverture (Module 3 — Future Skills)

**Résultat au : 26/11/2025**

- **Couverture globale du module `future_skills` : 78 %**

**Détails par fichier :**

- `future_skills/serializers.py` : **100 %** ✅
- `future_skills/services/recommendation_engine.py` : **100 %** ✅
- `future_skills/services/prediction_engine.py` : **91 %** ✅
- `future_skills/models.py` : **92 %** ✅
- `future_skills/permissions.py` : **90 %** ✅
- `future_skills/admin.py` : **81 %** ✅
- `future_skills/views.py` : **55 %** ⚠️

**Fichiers non couverts (exclus des statistiques) :**

- `future_skills/management/commands/recalculate_future_skills.py` : 0 % (commande CLI)
- `future_skills/management/commands/seed_future_skills.py` : 0 % (commande CLI)

**Analyse :**

- ✅ Les composants critiques (services, modèles, permissions) ont une excellente couverture (> 90%)
- ✅ La logique métier est bien testée
- ⚠️ Les vues API pourraient bénéficier de tests supplémentaires
- ℹ️ Les commandes de management ne nécessitent pas de tests unitaires (usage CLI ponctuel)

Le rapport HTML détaillé est disponible dans `htmlcov/index.html`.

## 4. Types de tests

### 4.1 Tests unitaires

- **Moteur de prédiction** (`test_prediction_engine.py`) : Validation des algorithmes de prédiction
- **Moteur de recommandations** (`test_recommendations.py`) : Validation de la logique de recommandations RH

### 4.2 Tests d'API

- **Endpoints REST** (`test_api.py`) : Tests des vues et endpoints du module Future Skills
- Validation des permissions et autorisations
- Tests des formats de réponse et codes HTTP

## 5. Démarche qualité

Le Module 3 respecte une démarche qualité "production" :

- ✅ Tests unitaires pour la logique métier
- ✅ Tests d'intégration pour les API
- ✅ Mesure de couverture avec coverage.py
- ✅ Traçabilité et documentation

## 6. Résumé des résultats

| Métrique                | Valeur      | Statut         |
| ----------------------- | ----------- | -------------- |
| **Tests exécutés**      | 12 tests    | ✅ Tous passés |
| **Couverture globale**  | 78 %        | ✅ Bon         |
| **Couverture services** | 91-100 %    | ✅ Excellent   |
| **Couverture modèles**  | 92 %        | ✅ Excellent   |
| **Temps d'exécution**   | ~4 secondes | ✅ Rapide      |

### Points forts

- 🎯 Excellente couverture des composants critiques (services, modèles)
- 🎯 Tests bien structurés (unitaires + API)
- 🎯 Configuration coverage.py optimisée
- 🎯 Tous les tests passent sans erreur

### Axes d'amélioration (optionnel)

- 📈 Augmenter la couverture des vues API (actuellement 55%)
- 📈 Ajouter des tests pour les cas limites supplémentaires

---

**Conclusion :** Le Module 3 dispose d'une couverture de tests solide et respecte les standards de qualité pour une mise en production.

---

## 7. Tests de l'intégration Machine Learning (ML-3)

### 7.1 Contexte

Le Module 3 intègre un modèle de Machine Learning optionnel pour la prédiction des compétences futures. Les tests doivent garantir que :

1. Le système fonctionne correctement quand le modèle ML est disponible
2. Le système bascule automatiquement sur le moteur de règles (fallback) si le modèle est indisponible
3. La traçabilité via `PredictionRun` reflète fidèlement le moteur utilisé

### 7.2 Commandes de test

**Exécuter tous les tests du Module 3 :**
```bash
python manage.py test future_skills
```

**Exécuter les tests avec couverture :**
```bash
coverage run manage.py test future_skills
coverage report
```

**Générer un rapport HTML détaillé :**
```bash
coverage html
# Ouvrir htmlcov/index.html dans un navigateur
```

**Exécuter uniquement les tests ML/fallback :**
```bash
python manage.py test future_skills.tests.test_prediction_engine.MLFallbackTests
python manage.py test future_skills.tests.test_api.RecalculateFutureSkillsMLFallbackTests
```

### 7.3 Aspects couverts par les tests ML

| Aspect testé                              | Fichier de test                    | Classe/Méthode                                    |
|-------------------------------------------|------------------------------------|---------------------------------------------------|
| Moteur de règles fonctionne normalement   | `test_prediction_engine.py`        | `CalculateLevelTests`                             |
| Fallback ML → règles si `.pkl` absent     | `test_prediction_engine.py`        | `MLFallbackTests.test_fallback_to_rules_when_ml_unavailable` |
| Utilisation effective du ML si disponible | `test_prediction_engine.py`        | `MLFallbackTests.test_uses_ml_when_available`     |
| API fallback avec ML indisponible         | `test_api.py`                      | `RecalculateFutureSkillsMLFallbackTests.test_recalculate_with_ml_unavailable_fallback_to_rules` |
| Traçabilité `PredictionRun.parameters`    | `test_prediction_engine.py`, `test_api.py` | Vérification du champ `engine` dans tous les tests |

### 7.4 Stratégies de test utilisées

**1. Override de settings avec `@override_settings` :**
```python
from django.test import override_settings

@override_settings(FUTURE_SKILLS_USE_ML=True)
def test_ml_behavior(self):
    # Test avec flag ML activé
    ...
```

**2. Mock du modèle ML :**
```python
from unittest.mock import patch

@patch("future_skills.services.prediction_engine.FutureSkillsModel.instance")
def test_fallback(self, mock_ml_instance):
    mock_ml_instance.return_value.is_available.return_value = False
    # Le système doit utiliser le fallback
    ...
```

**3. Vérification de traçabilité :**
```python
last_run = PredictionRun.objects.order_by("-run_date").first()
self.assertEqual(last_run.parameters["engine"], "rules_v1")
```

### 7.5 Résultats attendus

Tous les tests ML doivent passer avec succès :

```
✓ test_fallback_to_rules_when_ml_unavailable ... ok
✓ test_uses_ml_when_available ... ok
✓ test_recalculate_with_ml_unavailable_fallback_to_rules ... ok
```

**Couverture cible :**
- `prediction_engine.py` : > 90%
- `ml_model.py` : > 85%
- Vues API : > 70%

### 7.6 Cas limites testés

- ✅ Fichier `.pkl` absent
- ✅ Fichier `.pkl` corrompu (via mock)
- ✅ Flag `FUTURE_SKILLS_USE_ML` désactivé
- ✅ Traçabilité avec utilisateur authentifié (API)
- ✅ Traçabilité sans utilisateur (commande CLI)
- ✅ Cohérence des labels LOW/MEDIUM/HIGH entre moteurs

### 7.7 CI/CD et automatisation

Les tests ML sont intégrés dans le pipeline CI/CD :

```bash
# Dans le script CI
python manage.py test future_skills --parallel --keepdb
coverage run manage.py test future_skills
coverage report --fail-under=75
```

**Seuil de couverture minimum :** 75% pour l'ensemble du module.

---

**Conclusion ML-3 :** Les tests ML garantissent la robustesse du système de prédiction en conditions réelles, avec ou sans modèle ML disponible, et assurent une traçabilité complète pour l'audit et la conformité.

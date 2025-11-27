# 🚀 MLOps Guide - Future Skills ML Pipeline

Ce guide décrit le pipeline MLOps complet mis en place pour le modèle ML Future Skills, incluant le versioning, le monitoring et les bonnes pratiques de maintenance.

---

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture MLOps](#architecture-mlops)
3. [Versioning des Modèles](#versioning-des-modèles)
4. [Pipeline de Retraining](#pipeline-de-retraining)
5. [Monitoring & Drift Detection](#monitoring--drift-detection)
6. [Permissions & Gouvernance](#permissions--gouvernance)
7. [Troubleshooting](#troubleshooting)
8. [Roadmap Future](#roadmap-future)

---

## 🎯 Vue d'ensemble

### Objectif

Passer d'un "fichier .pkl posé dans /ml" à un mini-pipeline MLOps gérable, traceable et maintenable.

### Composants Clés

- **Versioning**: Modèles nommés `future_skills_model_vX.pkl` avec métadonnées JSON
- **Registry**: Tableau de suivi dans `MODEL_REGISTRY.md`
- **Retraining**: Script automatisé `retrain_model.py`
- **Monitoring**: Logs des prédictions pour détection de drift
- **Makefile**: Commandes simplifiées pour tous les workflows

---

## 🏗️ Architecture MLOps

```
┌─────────────────────────────────────────────────────────────┐
│                     DONNÉES SOURCE                          │
│  JobRole, Skill, MarketTrend, EconomicReport, etc.        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  export_future_skills_dataset │
        │  (Management Command)         │
        └──────────────┬─────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  future_skills_dataset.csv   │
        └──────────────┬─────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  train_future_skills_model.py│
        │  --version vX                │
        │  --n-estimators N            │
        └──────────────┬─────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
┌───────────────────┐    ┌──────────────────────┐
│ future_skills_    │    │ future_skills_       │
│ model_vX.pkl      │    │ model_vX.json        │
│ (Modèle sérialisé)│    │ (Métadonnées)        │
└─────────┬─────────┘    └──────────┬───────────┘
          │                          │
          └──────────┬───────────────┘
                     ▼
          ┌──────────────────────┐
          │  MODEL_REGISTRY.md   │
          │  (Historique)        │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  config/settings.py  │
          │  FUTURE_SKILLS_      │
          │  MODEL_VERSION       │
          │  MODEL_PATH          │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  PRODUCTION          │
          │  Prédictions via API │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  predictions_        │
          │  monitoring.jsonl    │
          │  (Logs pour drift)   │
          └──────────────────────┘
```

---

## 📦 Versioning des Modèles

### Convention de Nommage

```
future_skills_model_v1.pkl        → Version initiale
future_skills_model_v2.pkl        → Améliorations majeures
future_skills_model_v2.1.pkl      → Correctifs/ajustements mineurs
```

### Fichiers Associés

Pour chaque version, deux fichiers sont créés:

1. **Modèle sérialisé** (`*.pkl`): Pipeline scikit-learn complet

   - Preprocessing (OneHotEncoder + StandardScaler)
   - Modèle (RandomForestClassifier)

2. **Métadonnées** (`*.json`): Informations de traçabilité
   ```json
   {
     "model_version": "v2",
     "training_date": "2025-11-27T10:30:00",
     "training_duration_seconds": 45.32,
     "dataset": {
       "total_samples": 1250,
       "features_used": [...],
       "class_distribution": {"LOW": 400, "MEDIUM": 450, "HIGH": 400}
     },
     "hyperparameters": {
       "n_estimators": 300,
       "random_state": 42
     },
     "metrics": {
       "accuracy": 0.8542,
       "f1_weighted": 0.8501,
       "per_class": {...}
     }
   }
   ```

### Registre Central

`ml/MODEL_REGISTRY.md` contient l'historique complet:

| Version | Date       | Samples | Accuracy | F1-Score | Notes      |
| ------- | ---------- | ------- | -------- | -------- | ---------- |
| v1      | 2025-11-20 | 1000    | 82.5%    | 0.8123   | Baseline   |
| v2      | 2025-11-27 | 1250    | 85.4%    | 0.8501   | +300 trees |

---

## 🔄 Pipeline de Retraining

### Méthode 1: Script Automatisé (Recommandé)

```bash
# Retraining complet avec mise à jour automatique
make retrain-future-skills MODEL_VERSION=v2

# Ou directement:
python ml/retrain_model.py --version v2 --auto-update-settings
```

**Ce que fait ce script:**

1. ✅ Export du dataset depuis la DB
2. ✅ Entraînement du nouveau modèle
3. ✅ Génération des métadonnées JSON
4. ✅ Mise à jour du MODEL_REGISTRY.md
5. ✅ Mise à jour automatique de settings.py (si `--auto-update-settings`)

### Méthode 2: Manuelle (Contrôle Total)

```bash
# Étape 1: Export dataset
python manage.py export_future_skills_dataset

# Étape 2: Entraînement
python ml/train_future_skills_model.py \
  --version v2 \
  --n-estimators 300 \
  --output ml/future_skills_model_v2.pkl

# Étape 3: Mise à jour manuelle
# - Consulter future_skills_model_v2.json
# - Mettre à jour MODEL_REGISTRY.md
# - Modifier settings.py si satisfait
```

### Commandes Makefile Disponibles

```bash
make help                          # Affiche toutes les commandes
make export-dataset                # Export CSV uniquement
make train-model MODEL_VERSION=v2  # Train uniquement
make evaluate-model                # Évalue les modèles
make registry                      # Affiche le registre
```

---

## 📊 Monitoring & Drift Detection

### Logging des Prédictions

Chaque prédiction est loguée dans `logs/predictions_monitoring.jsonl`:

```json
{
  "timestamp": "2025-11-27T14:30:00",
  "job_role_id": 5,
  "skill_id": 12,
  "predicted_level": "HIGH",
  "score": 87.5,
  "engine": "ML (RandomForest)",
  "model_version": "ml_random_forest_v2",
  "features": {
    "trend_score": 0.85,
    "internal_usage": 0.72,
    "training_requests": 45.0,
    "scarcity_index": 0.28
  }
}
```

### Détection de Data Drift

**Signes à surveiller:**

1. **Drift de features**:

   - Distribution des features change par rapport au training
   - Nouvelles valeurs hors range d'entraînement

2. **Drift de performance**:

   - Accuracy en baisse progressive
   - Augmentation des prédictions "incertaines" (score proche de 50)

3. **Drift de concept**:
   - Les relations features → target changent
   - Ex: une compétence devient obsolète rapidement

### Analyse du Drift (à venir)

```python
# Script d'analyse à créer: ml/analyze_drift.py
python ml/analyze_drift.py \
  --baseline-model v1 \
  --current-logs logs/predictions_monitoring.jsonl \
  --window 30days
```

**Sorties:**

- Distribution comparison plots
- KL-divergence scores
- Recommandations de retraining

---

## 🔐 Permissions & Gouvernance

### Qui Peut Faire Quoi?

| Rôle               | Export Dataset | Train Model | Deploy Model | View Registry  |
| ------------------ | -------------- | ----------- | ------------ | -------------- |
| **Data Scientist** | ✅             | ✅          | ❌ (propose) | ✅             |
| **DRH Manager**    | ✅             | ❌          | ✅ (approve) | ✅             |
| **DevOps/Admin**   | ✅             | ✅          | ✅           | ✅             |
| **Developer**      | ❌             | ❌          | ❌           | ✅ (read-only) |

### Workflow d'Approbation

1. **Data Scientist** entraîne un nouveau modèle v2
2. Consulte les métriques dans `future_skills_model_v2.json`
3. Si satisfaisant, crée un **Pull Request** ou **demande de revue**
4. **DRH Manager** valide:
   - Les métriques sont-elles meilleures?
   - Le modèle fait-il sens business?
5. **DevOps** déploie:
   - Mise à jour `settings.py`
   - Redémarrage serveur
   - Test smoke en production

### Checklist de Mise en Production

- [ ] Métriques ≥ version précédente (ou justification)
- [ ] Aucune classe < 60% accuracy
- [ ] Test manuel sur 10 cas connus
- [ ] Approbation DRH/Data
- [ ] Backup du modèle actuel
- [ ] Plan de rollback si problème
- [ ] Documentation du changement dans REGISTRY

---

## 🛠️ Troubleshooting

### Problème: Modèle performe moins bien

**Diagnostic:**

```bash
# Comparer les métadonnées
diff ml/future_skills_model_v1.json ml/future_skills_model_v2.json

# Évaluer les deux modèles
python ml/evaluate_future_skills_models.py
```

**Solutions possibles:**

- Dataset déséquilibré → Vérifier `class_distribution`
- Overfitting → Réduire `n_estimators` ou ajouter validation set
- Features manquantes → Vérifier `features_used` vs `features_missing`

### Problème: Drift détecté

**Actions:**

1. Exporter un nouveau dataset récent
2. Retraîner avec les nouvelles données
3. Comparer avant/après
4. Déployer si amélioration significative

### Problème: Import Error lors du chargement

**Cause:** Version incompatible de scikit-learn

**Solution:**

```bash
# Vérifier la version utilisée pour training
cat ml/future_skills_model_v2.json | grep sklearn_version

# Installer la même version
pip install scikit-learn==X.Y.Z
```

---

## 🚀 Roadmap Future

### Court Terme (LT-2 ✅)

- [x] Versioning des modèles
- [x] Métadonnées d'entraînement
- [x] Script de retraining automatisé
- [x] Logging des prédictions
- [x] Documentation MLOps

### Moyen Terme (MT-4)

- [ ] Script d'analyse de drift automatique
- [ ] Dashboard de monitoring (Grafana/Kibana)
- [ ] A/B testing entre versions
- [ ] CI/CD pour training automatique
- [ ] Alertes automatiques si drift > seuil

### Long Terme (LT-3+)

- [ ] MLflow pour tracking avancé
- [ ] AutoML pour hyperparameter tuning
- [ ] Explainability dashboard (SHAP/LIME)
- [ ] Online learning (retraining incrémental)
- [ ] Multi-model ensemble

---

## 📚 Références

### Fichiers Clés

- `ml/train_future_skills_model.py` - Script d'entraînement
- `ml/retrain_model.py` - Orchestration retraining
- `ml/MODEL_REGISTRY.md` - Registre des versions
- `ml/MLOPS_GUIDE.md` - Ce guide
- `config/settings.py` - Configuration production
- `Makefile` - Commandes simplifiées

### Commandes Essentielles

```bash
# Voir toutes les commandes
make help

# Workflow complet
make retrain-future-skills MODEL_VERSION=v2

# Consulter le registre
make registry

# Évaluation
make evaluate-model
```

### Logs Importants

- `logs/future_skills.log` - Logs généraux
- `logs/predictions_monitoring.jsonl` - Logs de prédictions pour drift

---

## 💡 Bonnes Pratiques

### ✅ DO

- Toujours versionner les modèles (`--version vX`)
- Documenter les changements dans MODEL_REGISTRY
- Tester avant de déployer en production
- Garder au moins 2 versions en backup
- Monitorer les logs de prédictions

### ❌ DON'T

- Ne pas écraser `future_skills_model.pkl` directement
- Ne pas déployer sans validation DRH/Data
- Ne pas ignorer une baisse de performance
- Ne pas retraîner sans exporter un nouveau dataset
- Ne pas supprimer les anciennes versions sans backup

---

**Dernière mise à jour**: 2025-11-27  
**Responsables**: Équipe Data Science & DRH  
**Contact**: [À compléter]

---

## 🆘 Support

Pour toute question ou problème:

1. Consulter ce guide
2. Vérifier `MODEL_REGISTRY.md` et les métadonnées JSON
3. Consulter les logs dans `logs/`
4. Contacter l'équipe Data Science

**Happy MLOps! 🚀**

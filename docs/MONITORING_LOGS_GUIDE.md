# 📊 Guide de Monitoring et Logs — SmartHR360 Future Skills

## Vue d'ensemble

Ce document explique comment surveiller le comportement du système de prédictions et recommandations en mode **quasi-production**. Il détaille les logs structurés, leur lecture, et comment vérifier que le bon moteur (règles vs ML) est utilisé.

---

## 🔧 Configuration du Logging

### Architecture des Logs

Le système utilise la configuration Django `LOGGING` définie dans `config/settings.py` :

```python
LOGGING = {
    'handlers': {
        'console': {...},  # Sortie console (dev)
        'file': {...},     # Fichier logs/future_skills.log
    },
    'loggers': {
        'future_skills.services.prediction_engine': {...},
        'future_skills.services.recommendation_engine': {...},
    }
}
```

**Où trouver les logs :**

- **Console** : Pendant le développement (lors de `runserver`, management commands)
- **Fichier** : `logs/future_skills.log` (en production ou pour historisation)

**Niveaux de logs utilisés :**

- `INFO` : Informations normales d'exécution
- `WARNING` : Situations anormales non critiques (ex: fallback ML → rules)
- `ERROR` : Erreurs graves
- `DEBUG` : Détails fins (désactivé par défaut)

---

## 📈 Logs du Moteur de Prédictions

### 1. Début de Recalcul

Lors du lancement d'un recalcul (via API ou management command), vous verrez :

```
[INFO] ========================================
[INFO] 🚀 Starting prediction recalculation...
[INFO] Horizon: 5 years | Triggered by: admin
[INFO] Dataset size: 10 job roles × 15 skills = 150 combinations
```

**Ce qu'il faut vérifier :**

- ✅ Le nombre de combinaisons correspond à vos données
- ✅ L'utilisateur/déclencheur est correct

### 2. Sélection du Moteur

Le système indique quel moteur sera utilisé :

#### **Cas 1 : ML activé et disponible**

```
[INFO] Configuration: FUTURE_SKILLS_USE_ML=True
[INFO] ✅ ML model loaded and available for predictions
[INFO] 🔧 Engine selected: ml_random_forest_v1
[INFO] Model version: ml_random_forest_v1
```

#### **Cas 2 : ML activé mais indisponible (fallback automatique)**

```
[INFO] Configuration: FUTURE_SKILLS_USE_ML=True
[WARNING] ⚠️  FUTURE_SKILLS_USE_ML=True but ML model is not available.
[WARNING] Falling back to rule-based engine (rules_v1).
[WARNING] Check that model file exists at: /path/to/ml/future_skills_model.pkl
[INFO] 🔧 Engine selected: rules_v1
```

**🚨 IMPORTANT :** Ce message WARNING indique un problème ! Le système a tenté d'utiliser le ML mais est retombé sur les règles. Vérifiez :

- Le fichier `ml/future_skills_model.pkl` existe
- Le modèle a été entraîné (`python ml/train_future_skills_model.py`)
- Les permissions de lecture du fichier

#### **Cas 3 : Mode règles explicite**

```
[INFO] Configuration: FUTURE_SKILLS_USE_ML=False
[INFO] Using rule-based engine as per configuration
[INFO] 🔧 Engine selected: rules_v1
```

### 3. Fin de Recalcul

À la fin, un résumé est affiché :

```
[INFO] ✅ Prediction recalculation completed successfully
[INFO] Total predictions created/updated: 150
[INFO] Engine used: ml_random_forest_v1 | Horizon: 5 years
[INFO] ========================================
```

**Vérifications clés :**

- ✅ Le nombre de prédictions correspond au dataset
- ✅ L'engine correspond à votre intention (ML ou rules)

---

## 🎯 Logs du Moteur de Recommandations

### 1. Début de Génération

```
[INFO] ========================================
[INFO] 📊 Starting recommendation generation...
[INFO] Horizon: 5 years
[INFO] Total predictions available: 150
```

### 2. Mode Normal vs Fallback

#### **Mode Normal (prédictions HIGH trouvées)**

```
[INFO] ✅ Found 25 HIGH level predictions (normal mode)
[INFO] Generating recommendations from HIGH predictions only
```

#### **Mode Fallback (aucune prédiction HIGH)**

```
[WARNING] ⚠️  No HIGH predictions found for horizon=5 years
[WARNING] Fallback mode activated: using top 3 predictions by score
```

**📌 Note :** Le fallback est normal sur de petits datasets de démo, mais en production, son absence de prédictions HIGH peut indiquer un problème avec le moteur de prédictions.

### 3. Statistiques de Distribution

À la fin :

```
[INFO] ✅ Recommendation generation completed successfully
[INFO] Total recommendations created/updated: 25
[INFO] Priority distribution: HIGH=25, MEDIUM=0, LOW=0
[INFO] Action distribution: HIRING=18, TRAINING=7
[INFO] ========================================
```

**Analyses possibles :**

- Ratio HIRING/TRAINING reflète-t-il votre stratégie RH ?
- Y a-t-il assez de diversité dans les priorités ?

---

## 🔍 Comment Vérifier le Moteur Utilisé

### Méthode 1 : Logs en Temps Réel

Lors d'un recalcul, cherchez la ligne :

```
[INFO] 🔧 Engine selected: <engine_name>
```

Valeurs possibles :

- `ml_random_forest_v1` → Modèle ML actif ✅
- `rules_v1` → Moteur de règles utilisé

### Méthode 2 : Base de Données

Consultez la table `PredictionRun` :

```python
from future_skills.models import PredictionRun

latest_run = PredictionRun.objects.order_by('-created_at').first()
print(latest_run.parameters)
# {'engine': 'ml_random_forest_v1', 'model_version': 'ml_random_forest_v1', ...}
```

Le champ `parameters['engine']` contient toujours le moteur réellement utilisé.

### Méthode 3 : API

```bash
GET /api/predictions/runs/
```

Le dernier run contient :

```json
{
  "id": 42,
  "description": "Recalcul des prédictions à horizon 5 ans (ml_random_forest_v1).",
  "parameters": {
    "engine": "ml_random_forest_v1",
    "model_version": "ml_random_forest_v1"
  }
}
```

---

## ⚠️ Messages Importants à Surveiller

### 1. Fallback ML → Rules (WARNING)

```
[WARNING] ⚠️  FUTURE_SKILLS_USE_ML=True but ML model is not available.
```

**Action requise :**

1. Vérifier l'existence du fichier modèle
2. Entraîner le modèle si nécessaire
3. Vérifier `FUTURE_SKILLS_MODEL_PATH` dans settings

### 2. Fallback Recommendations (WARNING)

```
[WARNING] ⚠️  No HIGH predictions found for horizon=5 years
```

**Action requise :**

- Si dataset réel : investiguer pourquoi aucune compétence n'est critique
- Si démo : comportement normal

### 3. Échec Silencieux (pas de logs)

Si vous ne voyez **aucun log** pendant un recalcul :

- Vérifier que `LOGGING` est bien configuré dans `settings.py`
- Vérifier que le logger `future_skills` est actif
- Créer le dossier `logs/` à la racine du projet

---

## 🧪 Scénarios de Test

### Test 1 : Mode Rules Uniquement

```python
# config/settings.py
FUTURE_SKILLS_USE_ML = False
```

```bash
python manage.py recalculate_future_skills --horizon 5
```

**Log attendu :**

```
[INFO] Configuration: FUTURE_SKILLS_USE_ML=False
[INFO] Using rule-based engine as per configuration
[INFO] 🔧 Engine selected: rules_v1
```

### Test 2 : Mode ML avec Modèle Disponible

```python
# config/settings.py
FUTURE_SKILLS_USE_ML = True
```

```bash
# S'assurer que le modèle existe
python ml/train_future_skills_model.py
python manage.py recalculate_future_skills --horizon 5
```

**Log attendu :**

```
[INFO] Configuration: FUTURE_SKILLS_USE_ML=True
[INFO] ✅ ML model loaded and available for predictions
[INFO] 🔧 Engine selected: ml_random_forest_v1
```

### Test 3 : Mode ML sans Modèle (Fallback)

```python
# config/settings.py
FUTURE_SKILLS_USE_ML = True
```

```bash
# Renommer temporairement le modèle
mv ml/future_skills_model.pkl ml/future_skills_model.pkl.backup
python manage.py recalculate_future_skills --horizon 5
```

**Log attendu :**

```
[WARNING] ⚠️  FUTURE_SKILLS_USE_ML=True but ML model is not available.
[WARNING] Falling back to rule-based engine (rules_v1).
[INFO] 🔧 Engine selected: rules_v1
```

---

## 📂 Fichier de Logs Persistant

### Activation

Le fichier `logs/future_skills.log` enregistre tous les logs INFO et supérieurs.

**Créer le dossier si nécessaire :**

```bash
mkdir -p logs
```

### Consultation

```bash
# Voir les derniers logs
tail -f logs/future_skills.log

# Chercher les runs de prédictions
grep "Engine selected" logs/future_skills.log

# Chercher les warnings
grep WARNING logs/future_skills.log
```

### Rotation (Production)

Pour la production, configurez une rotation automatique :

```python
# config/settings.py
'file': {
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': BASE_DIR / 'logs' / 'future_skills.log',
    'maxBytes': 10485760,  # 10 MB
    'backupCount': 5,
    'formatter': 'verbose',
}
```

---

## 🎯 Checklist Quotidienne (Production)

### Avant un Recalcul Majeur

- [ ] Vérifier `FUTURE_SKILLS_USE_ML` dans settings
- [ ] Vérifier que `ml/future_skills_model.pkl` existe (si ML=True)
- [ ] Consulter le dernier `PredictionRun` pour connaître l'état précédent

### Après un Recalcul

- [ ] Vérifier les logs : aucun WARNING inattendu
- [ ] Vérifier `Engine selected` correspond à l'intention
- [ ] Vérifier `Total predictions` correspond au dataset
- [ ] Vérifier les distributions de priorités/actions sont cohérentes

### Monitoring Hebdomadaire

- [ ] Analyser les logs pour repérer les patterns de fallback
- [ ] Vérifier la taille du fichier `logs/future_skills.log`
- [ ] Comparer les performances ML vs rules (via PredictionRun.parameters)

---

## 🚨 Dépannage Rapide

### Problème : Pas de logs visibles

**Solutions :**

1. Créer `mkdir logs/`
2. Vérifier `LOGGING` dans `settings.py`
3. Redémarrer le serveur Django

### Problème : Toujours en mode rules_v1 alors que ML=True

**Solutions :**

1. Vérifier `ls ml/future_skills_model.pkl`
2. Entraîner le modèle : `python ml/train_future_skills_model.py`
3. Vérifier `FUTURE_SKILLS_MODEL_PATH` dans settings
4. Chercher WARNING dans les logs

### Problème : Aucune recommandation générée

**Solutions :**

1. Vérifier qu'il y a des prédictions : `FutureSkillPrediction.objects.count()`
2. Regarder les logs de `recommendation_engine`
3. Vérifier le mode fallback (normal sur petits datasets)

---

## 📞 Support

Pour toute question sur les logs ou le monitoring :

1. Consulter ce document
2. Analyser les logs avec les exemples ci-dessus
3. Vérifier les `PredictionRun` dans la base de données

**Bonnes pratiques :**

- Toujours consulter les logs avant de signaler un problème
- Inclure les messages de logs pertinents dans les rapports de bug
- Garder un historique des `PredictionRun` pour tracer les changements

### Dépendances Machine Learning (Phase 2)

Pour la phase Machine Learning du Module 3, les bibliothèques Python suivantes sont utilisées :

- `pandas` : chargement et manipulation du dataset CSV
- `scikit-learn` : entraînement du modèle de classification (RandomForest, etc.)
- `joblib` : sérialisation du pipeline (encoders + modèle) vers un fichier `.pkl`

Installation recommandée :

```bash
pip install -r requirements_ml.txt
```

---

## Modèle de Machine Learning — Module 3 (Future Skills)

### 1. Jeu de données (future_skills_dataset.csv)

Le dataset utilisé pour l'entraînement du modèle est généré via la commande Django :

```bash
python manage.py export_future_skills_dataset
```

**Source des données :**

- Export depuis la base de données Django (tables `JobRole`, `Skill`, `MarketTrend`)
- Enrichissement avec des métriques calculées : `internal_usage`, `training_requests`, `scarcity_index`
- Les données sont partiellement simulées pour la phase de démonstration

**Structure du CSV :**

| Colonne             | Type   | Description                                                       |
| ------------------- | ------ | ----------------------------------------------------------------- |
| `job_role_name`     | string | Nom du poste/métier (ex: "Data Engineer", "Responsable RH")       |
| `skill_name`        | string | Nom de la compétence (ex: "Python", "Gestion de projet")          |
| `trend_score`       | float  | Score de tendance marché [0, 1] basé sur `MarketTrend`            |
| `internal_usage`    | float  | Estimation de l'utilisation interne de la compétence [0, 1]       |
| `training_requests` | float  | Nombre estimé de demandes de formation pour cette compétence      |
| `scarcity_index`    | float  | Indice de rareté de la compétence [0, 1] (1 = rare, 0 = commune)  |
| `future_need_level` | string | **Variable cible** : niveau de besoin futur ∈ {LOW, MEDIUM, HIGH} |

**Alignement avec le modèle :** La variable cible `future_need_level` est strictement alignée avec les valeurs du champ `FutureSkillPrediction.level` (LOW / MEDIUM / HIGH).

---

### 2. Features utilisées

Le modèle utilise 6 features réparties en deux catégories :

**Variables catégorielles (encodées avec OneHotEncoder) :**

- `job_role_name` : identifie le contexte métier de la prédiction
- `skill_name` : identifie la compétence cible

**Variables numériques (normalisées avec StandardScaler) :**

- `trend_score` : reflète la tendance marché captée depuis les sources externes
- `internal_usage` : reflète l'utilisation actuelle de la compétence en interne
- `training_requests` : mesure la demande en formation
- `scarcity_index` : indique la rareté de la compétence (inversement proportionnel à `internal_usage`)

**Stratégie de preprocessing :**

- **OneHotEncoder** : transforme les variables catégorielles en vecteurs binaires, avec gestion des valeurs inconnues (`handle_unknown="ignore"`)
- **StandardScaler** : normalise les features numériques à moyenne 0 et écart-type 1

---

### 3. Pipeline et modèle

Le modèle est construit sous forme d'un **Pipeline scikit-learn** qui encapsule :

1. **Preprocessing** : `ColumnTransformer` appliquant OneHotEncoder et StandardScaler
2. **Classifier** : `RandomForestClassifier` avec 200 arbres

**Configuration du modèle :**

```python
RandomForestClassifier(
    n_estimators=200,
    random_state=42,
    class_weight="balanced",  # gère le déséquilibre des classes
    n_jobs=-1                 # parallélisation
)
```

**Fichier de sortie :** Le pipeline complet (preprocessing + modèle) est sérialisé via `joblib` dans :

```
ml/future_skills_model.pkl
```

**Méthode d'inférence :** La classe `FutureSkillsModel` (dans `future_skills/ml_model.py`) encapsule le modèle et expose la méthode :

```python
predict_level(
    job_role_name: str,
    skill_name: str,
    trend_score: float,
    internal_usage: float,
    training_requests: float,
    scarcity_index: float
) -> Tuple[str, float]
```

**Retour :**

- `level` ∈ {LOW, MEDIUM, HIGH} : niveau de besoin futur prédit
- `score_0_100` : score de confiance basé sur `predict_proba()`, exprimé en pourcentage [0, 100]

---

### 4. Intégration dans le moteur de prédiction

Le modèle ML est intégré de manière optionnelle et transparente dans le système de prédiction.

**Flag de contrôle dans `settings.py` :**

```python
FUTURE_SKILLS_USE_ML = True  # Active l'utilisation du modèle ML
```

**Logique de sélection du moteur :**

| Condition                                 | Moteur utilisé   | Label dans `PredictionRun` |
| ----------------------------------------- | ---------------- | -------------------------- |
| `FUTURE_SKILLS_USE_ML = False`            | Moteur de règles | `"rules_v1"`               |
| `FUTURE_SKILLS_USE_ML = True` + modèle OK | Modèle ML        | `"ml_random_forest_v1"`    |
| `FUTURE_SKILLS_USE_ML = True` + modèle KO | Fallback règles  | `"rules_v1"`               |

**Fallback automatique :**
Si le fichier `.pkl` est introuvable ou invalide, le système bascule automatiquement sur le moteur de règles heuristique (`calculate_level`) sans interruption du service. Un log d'avertissement est émis.

**Alignement des labels :**
Les deux moteurs (règles et ML) retournent des labels strictement identiques : `LOW` / `MEDIUM` / `HIGH`, garantissant l'interopérabilité et la cohérence des prédictions.

---

### 5. Limitations et perspectives

**Limitations actuelles :**

1. **Dataset simulé :** Les données d'entraînement sont en partie synthétiques et ne reflètent pas forcément la diversité et la complexité des besoins réels en compétences.

2. **Features limitées :** Le modèle n'utilise que 6 features. Des enrichissements possibles :

   - Historique temporel des tendances (séries temporelles)
   - Données sectorielles plus fines
   - Données salariales et démographiques
   - Feedback des managers sur les compétences critiques

3. **Absence de calibration :** Les scores de confiance (`predict_proba`) ne sont pas calibrés, ce qui peut affecter l'interprétabilité des probabilités.

4. **Pas de réentraînement automatique :** Le modèle doit être réentraîné manuellement via le script `ml/train_future_skills_model.py`.

**Perspectives d'amélioration :**

- **Collecte de données réelles** : intégrer des données provenant de systèmes RH réels (SIRH, plateformes de formation)
- **Enrichissement du dataset** : ajouter des features temporelles, économiques, géographiques
- **Exploration d'autres algorithmes** : tester XGBoost, LightGBM, ou des modèles de deep learning
- **Calibration des scores** : utiliser des techniques comme Platt Scaling ou Isotonic Regression
- **Pipeline MLOps** : automatiser le réentraînement, le versioning des modèles, et le monitoring de la performance
- **Explainability** : intégrer SHAP ou LIME pour expliquer les prédictions individuelles aux utilisateurs RH

---

## Traçabilité et Contrôle du Moteur ML — Module 3

### 1. Configuration dans settings.py

Le Module 3 expose trois paramètres de configuration dans `config/settings.py` pour contrôler le comportement du moteur de prédiction :

```python
# --- Module 3 : Future Skills / Machine Learning ---

# Active ou désactive l'utilisation du modèle ML
FUTURE_SKILLS_USE_ML = True

# Chemin vers le fichier pickle contenant le pipeline ML entraîné
FUTURE_SKILLS_MODEL_PATH = BASE_DIR / "ml" / "future_skills_model.pkl"

# Version logique du modèle (pour traçabilité dans PredictionRun)
FUTURE_SKILLS_MODEL_VERSION = "ml_random_forest_v1"
```

**Détails des paramètres :**

| Paramètre                     | Type | Description                                                                                    |
| ----------------------------- | ---- | ---------------------------------------------------------------------------------------------- |
| `FUTURE_SKILLS_USE_ML`        | bool | Si `False` : utilise systématiquement le moteur de règles. Si `True` : tente d'utiliser le ML. |
| `FUTURE_SKILLS_MODEL_PATH`    | Path | Chemin absolu vers le fichier `.pkl` contenant le pipeline scikit-learn.                       |
| `FUTURE_SKILLS_MODEL_VERSION` | str  | Identifiant de version du modèle (ex: `"ml_random_forest_v1"`), stocké dans `PredictionRun`.   |

---

### 2. Classe FutureSkillsModel : chargement et disponibilité

La classe `FutureSkillsModel` (dans `future_skills/ml_model.py`) encapsule le modèle ML et gère son cycle de vie.

**Pattern Singleton :**
Le modèle est chargé une seule fois au premier appel via :

```python
model = FutureSkillsModel.instance()
```

**Chargement du pipeline :**

- Le fichier `.pkl` est chargé via `joblib.load()` lors de l'initialisation.
- Si le fichier est **introuvable** ou **invalide**, le pipeline reste `None` et un log d'avertissement est émis.

**Méthode `is_available()` :**

```python
def is_available(self) -> bool:
    return self._loaded and self.pipeline is not None
```

Cette méthode retourne `True` uniquement si le pipeline a été chargé avec succès. Elle est utilisée par le moteur de prédiction pour décider du fallback.

**Comportement en cas d'absence du fichier `.pkl` :**

1. Log d'avertissement :

   ```
   FutureSkillsModel: fichier modèle introuvable à /path/to/future_skills_model.pkl.
   Fallback sur le moteur de règles.
   ```

2. `is_available()` retourne `False`

3. Le moteur de prédiction bascule automatiquement sur `calculate_level()` (moteur de règles)

4. Aucune exception n'est levée → le service continue sans interruption

---

### 3. Traçabilité via PredictionRun

Chaque exécution du moteur de prédiction crée un objet `PredictionRun` qui documente :

**Champs du modèle `PredictionRun` :**

| Champ               | Type       | Description                                               |
| ------------------- | ---------- | --------------------------------------------------------- |
| `run_date`          | DateTime   | Date/heure de l'exécution                                 |
| `description`       | TextField  | Description textuelle (ex: "Recalcul à horizon 5 ans")    |
| `total_predictions` | Integer    | Nombre de prédictions créées/mises à jour                 |
| `run_by`            | ForeignKey | Utilisateur ayant déclenché le run (null si commande CLI) |
| `parameters`        | JSONField  | **Paramètres structurés de l'exécution**                  |

**Structure du champ `parameters` (JSON) :**

Le champ `parameters` contient des métadonnées clés pour l'audit et la traçabilité.

**Exemple 1 : Moteur de règles (fallback ou flag désactivé)**

```json
{
  "trigger": "management_command",
  "engine": "rules_v1",
  "horizon_years": 5
}
```

**Exemple 2 : Modèle ML actif**

```json
{
  "trigger": "api",
  "engine": "ml_random_forest_v1",
  "horizon_years": 5,
  "model_version": "ml_random_forest_v1"
}
```

**Clés dans `parameters` :**

| Clé             | Valeurs possibles                     | Description                                           |
| --------------- | ------------------------------------- | ----------------------------------------------------- |
| `trigger`       | `"api"`, `"management_command"`       | Source du déclenchement                               |
| `engine`        | `"rules_v1"`, `"ml_random_forest_v1"` | Moteur réellement utilisé pour cette exécution        |
| `horizon_years` | int (ex: 3, 5, 10)                    | Horizon temporel de prédiction                        |
| `model_version` | str (ex: `"ml_random_forest_v1"`)     | Version du modèle ML (présent uniquement si ML actif) |

**Note importante :** Le champ `engine` reflète toujours le moteur **réellement utilisé**. Si le flag ML est activé mais que le modèle est indisponible, `engine` sera `"rules_v1"` (fallback).

---

### 4. Intégration avec l'API

L'endpoint API `POST /api/future-skills/recalculate/` permet de déclencher un recalcul des prédictions.

**Vue : `RecalculateFutureSkillsAPIView`**

```python
class RecalculateFutureSkillsAPIView(APIView):
    permission_classes = [IsDRHOrResponsableRH]

    def post(self, request):
        horizon_years = request.data.get("horizon_years", 5)

        total = recalculate_predictions(
            horizon_years=horizon_years,
            run_by=request.user,  # ← Traçabilité de l'utilisateur
            parameters={
                "trigger": "api",  # ← Distinction source
                "horizon_years": horizon_years,
            }
        )

        return Response({
            "total_predictions": total,
            "horizon_years": horizon_years,
        })
```

**Flux de traçabilité :**

1. L'utilisateur authentifié appelle l'API avec un token ou session
2. La vue passe `run_by=request.user` à `recalculate_predictions()`
3. Le moteur de prédiction :
   - Détermine quel moteur utiliser (ML ou règles)
   - Enrichit `parameters` avec `engine` et optionnellement `model_version`
4. Un `PredictionRun` est créé avec toutes ces métadonnées
5. L'admin Django permet de consulter l'historique complet des exécutions

**Exemple de consultation dans l'admin :**

| Run Date            | Run By     | Total | Engine              | Trigger            |
| ------------------- | ---------- | ----- | ------------------- | ------------------ |
| 2025-11-26 14:30:00 | drh_user   | 12    | ml_random_forest_v1 | api                |
| 2025-11-25 09:15:00 | None       | 12    | rules_v1            | management_command |
| 2025-11-24 16:45:00 | admin_user | 12    | rules_v1            | api                |

---

### 5. Workflow décisionnel du moteur de prédiction

Voici le schéma de décision utilisé par `recalculate_predictions()` :

```
┌─────────────────────────────────┐
│ settings.FUTURE_SKILLS_USE_ML ? │
└──────────────┬──────────────────┘
               │
       ┌───────┴───────┐
       │               │
     False           True
       │               │
       ▼               ▼
  ┌────────┐   ┌──────────────────┐
  │ Règles │   │ FutureSkillsModel│
  │        │   │  .is_available() ?│
  └────────┘   └────────┬──────────┘
                        │
                ┌───────┴────────┐
                │                │
              True             False
                │                │
                ▼                ▼
           ┌────────┐      ┌────────┐
           │   ML   │      │ Règles │
           │        │      │(fallback)│
           └────────┘      └────────┘
```

**Résultat :** Le champ `engine` dans `PredictionRun.parameters` documente toujours le moteur finalement utilisé.

---

### 6. Logs et observabilité

Le système émet des logs structurés pour faciliter le debugging et l'audit :

**Logs lors du chargement du modèle :**

```
[INFO] FutureSkillsModel: modèle ML chargé depuis /path/to/future_skills_model.pkl
```

ou

```
[WARNING] FutureSkillsModel: fichier modèle introuvable à /path/to/future_skills_model.pkl.
Fallback sur le moteur de règles.
```

**Logs lors du recalcul :**

```
[WARNING] recalculate_predictions: FUTURE_SKILLS_USE_ML=True mais le modèle ML
n'est pas disponible. Fallback sur le moteur de règles.
```

Ces logs permettent aux équipes DevOps et Data de diagnostiquer rapidement les problèmes de configuration ou de déploiement du modèle.

---

### 7. Résumé des garanties de traçabilité

| Aspect                         | Mécanisme                                   |
| ------------------------------ | ------------------------------------------- |
| **Qui** a lancé le recalcul ?  | Champ `run_by` dans `PredictionRun`         |
| **Quand** ?                    | Champ `run_date` automatique                |
| **Quel moteur** utilisé ?      | Champ `parameters["engine"]`                |
| **Quelle version** du modèle ? | Champ `parameters["model_version"]` (si ML) |
| **Comment** déclenché ?        | Champ `parameters["trigger"]` (api / CLI)   |
| **Combien** de prédictions ?   | Champ `total_predictions`                   |

Cette traçabilité complète permet :

- Un **audit** précis des calculs effectués
- Une **reproductibilité** des analyses
- Une **comparaison** des performances entre moteurs de règles et ML
- Une **conformité** avec les exigences de transparence des systèmes RH

---

# Module 3 : Future Skills — Récapitulatif Global

## 📋 Vue d'ensemble

Le **Module 3 : Future Skills** est un système de prédiction et de recommandations RH permettant d'anticiper les besoins en compétences futures et de proposer des investissements stratégiques en formation.

**Date de mise à jour** : 26/11/2025

---

## 🎯 Objectifs réalisés

### 1. Architecture & Design

- ✅ Architecture Django REST Framework complète
- ✅ Séparation claire des responsabilités (Models, Services, Views, Serializers)
- ✅ Système de permissions granulaires basé sur les rôles utilisateurs
- ✅ API RESTful documentée (Postman Collection)

### 2. Fonctionnalités principales

#### 2.1 Prédiction des compétences futures

- **Moteur de prédiction** : `prediction_engine.py`
- Algorithmes de prédiction des tendances de compétences
- Analyse des données économiques et RH
- Génération de scores de pertinence et criticité

#### 2.2 Recommandations d'investissement RH

- **Moteur de recommandations** : `recommendation_engine.py`
- Calcul du ROI prévisionnel des formations
- Priorisation des investissements
- Suggestions personnalisées par secteur/métier

#### 2.3 API REST complète

Endpoints disponibles :

- `GET /api/future-skills/predictions/` - Liste des prédictions
- `POST /api/future-skills/predictions/` - Créer une nouvelle prédiction
- `GET /api/future-skills/predictions/{id}/` - Détail d'une prédiction
- `POST /api/future-skills/predictions/run/` - Lancer une nouvelle analyse
- `GET /api/future-skills/recommendations/` - Liste des recommandations
- `POST /api/future-skills/recommendations/generate/` - Générer des recommandations
- `GET /api/future-skills/reports/economic/` - Rapports économiques

### 3. Modèles de données

| Modèle                       | Description                | Champs clés                                |
| ---------------------------- | -------------------------- | ------------------------------------------ |
| `FutureSkillPrediction`      | Prédictions de compétences | skill_name, relevance_score, predicted_for |
| `PredictionRun`              | Historique des analyses    | run_date, parameters, status               |
| `HRInvestmentRecommendation` | Recommandations RH         | skill, priority, estimated_roi             |
| `EconomicReport`             | Rapports économiques       | sector, indicators, published_date         |

---

## 🧪 Tests & Qualité

### Couverture des tests

- **Couverture globale** : **78 %**
- **Tests exécutés** : 12 tests (100% de réussite)
- **Temps d'exécution** : ~4 secondes

### Détails par composant

| Composant                        | Couverture | Statut        |
| -------------------------------- | ---------- | ------------- |
| Serializers                      | 100%       | ✅ Excellent  |
| Services (recommendation_engine) | 100%       | ✅ Excellent  |
| Services (prediction_engine)     | 91%        | ✅ Excellent  |
| Models                           | 92%        | ✅ Excellent  |
| Permissions                      | 90%        | ✅ Excellent  |
| Admin                            | 81%        | ✅ Bon        |
| Views                            | 55%        | ⚠️ Acceptable |

**Outils utilisés** :

- `pytest` / Django TestCase
- `coverage.py` pour la mesure de couverture
- Configuration `.coveragerc` optimisée

**Documentation** : Voir `TESTING.md` pour les détails complets.

---

## 🔐 Sécurité & Permissions

### Système de permissions personnalisées

- `IsAdminUserOrReadOnly` - Lecture pour tous, modification admin uniquement
- `IsOwnerOrReadOnly` - Propriétaire ou lecture seule
- `IsHRManager` - Gestionnaire RH
- `IsExecutive` - Niveau exécutif

### Gestion des utilisateurs

Documentation complète dans `USERS_PERMISSIONS_DOCUMENTATION.md`

---

## 📊 Données & Fixtures

### Données de démonstration

- Fichier : `future_skills/fixtures/future_skills_demo.json`
- Contenu : Exemples de prédictions, recommandations, et rapports économiques
- Chargement : `python manage.py loaddata future_skills_demo`

### Commandes de gestion

| Commande                    | Description                    |
| --------------------------- | ------------------------------ |
| `seed_future_skills`        | Initialise les données de démo |
| `recalculate_future_skills` | Recalcule les prédictions      |

---

## 📁 Structure du projet

```
future_skills/
├── models.py               # Modèles de données
├── views.py                # Vues API REST
├── serializers.py          # Sérialiseurs DRF
├── permissions.py          # Permissions personnalisées
├── urls.py                 # Routage des endpoints
├── admin.py                # Interface d'administration
├── services/
│   ├── prediction_engine.py       # Moteur de prédiction
│   └── recommendation_engine.py   # Moteur de recommandations
├── tests/
│   ├── test_api.py                # Tests d'API
│   ├── test_prediction_engine.py  # Tests unitaires prédictions
│   └── test_recommendations.py    # Tests recommandations
├── management/commands/
│   ├── seed_future_skills.py
│   └── recalculate_future_skills.py
└── fixtures/
    └── future_skills_demo.json
```

---

## 🚀 Déploiement & Configuration

### Prérequis

- Python 3.14+
- Django 5.1+
- Django REST Framework 3.15+
- SQLite (dev) / PostgreSQL (prod)

### Installation

```bash
# Cloner le repository
git clone <repo-url>

# Créer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou .venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Migrations
python manage.py migrate

# Charger les données de démo
python manage.py loaddata future_skills_demo

# Lancer le serveur
python manage.py runserver
```

### Variables d'environnement

- `DEBUG` - Mode debug (True/False)
- `SECRET_KEY` - Clé secrète Django
- `DATABASE_URL` - URL de connexion à la base de données
- `ALLOWED_HOSTS` - Hôtes autorisés

---

## 📖 Documentation disponible

| Document                                             | Description                          |
| ---------------------------------------------------- | ------------------------------------ |
| `README.md`                                          | Documentation principale du projet   |
| `TESTING.md`                                         | Tests et couverture détaillés        |
| `USERS_PERMISSIONS_DOCUMENTATION.md`                 | Guide des permissions                |
| `SmartHR360_M3_FutureSkills.postman_collection.json` | Collection Postman pour tester l'API |

---

## 🔄 Prochaines étapes (Phase ML)

### Objectifs

1. **Intégration de vrais modèles ML**

   - Remplacer les algorithmes simulés par des modèles ML réels
   - Utiliser scikit-learn, TensorFlow ou PyTorch
   - Entraîner sur des données réelles

2. **Amélioration des prédictions**

   - Intégrer des sources de données externes (LinkedIn, Indeed, etc.)
   - Analyse de tendances historiques
   - Modèles de séries temporelles

3. **Optimisation des recommandations**
   - Système de recommandation avancé
   - Calcul ROI plus précis
   - Personnalisation par entreprise

### Technologies envisagées

- scikit-learn pour les modèles de base
- pandas pour l'analyse de données
- numpy pour les calculs numériques
- joblib pour la persistance des modèles

---

## 📈 Métriques de qualité

| Métrique                | Valeur       | Objectif    |
| ----------------------- | ------------ | ----------- |
| Tests réussis           | 12/12 (100%) | ✅ Atteint  |
| Couverture code         | 78%          | ✅ > 70%    |
| Couverture services     | 91-100%      | ✅ > 90%    |
| Temps d'exécution tests | ~4s          | ✅ < 10s    |
| Endpoints API           | 7            | ✅ Complet  |
| Documentation           | 4 fichiers   | ✅ Complète |

---

## 🎓 Conclusion

Le **Module 3 : Future Skills** constitue une base solide pour un système de prédiction et recommandations RH en production :

### Points forts

- 🎯 Architecture propre et maintenable
- 🎯 API REST complète et testée
- 🎯 Couverture de tests excellente sur les composants critiques
- 🎯 Documentation exhaustive
- 🎯 Système de permissions robuste
- 🎯 Prêt pour l'intégration ML réelle

### Démarche professionnelle

- ✅ Tests unitaires et d'intégration
- ✅ Mesure de couverture avec coverage.py
- ✅ Documentation technique complète
- ✅ API documentée (Postman)
- ✅ Code versionné (Git)
- ✅ Respect des bonnes pratiques Django/DRF

**Le module est prêt pour la phase d'intégration ML et la mise en production.**

---

_Document généré le 26/11/2025_

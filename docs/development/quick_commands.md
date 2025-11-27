# Commandes Utiles — Module 3 : Future Skills

## 🚀 Démarrage rapide

```bash
# Activer l'environnement virtuel
source .venv/bin/activate  # Mac/Linux
# ou
.venv\Scripts\activate  # Windows

# Configuration automatique (nouvelle installation)
make setup
# ou
./scripts/setup_dev.sh

# Lancer le serveur
make serve
# ou
python manage.py runserver --settings=config.settings.development
```

## 📦 Installation

```bash
# Installer les dépendances de production
make install

# Installer les dépendances de développement
make install-dev

# Installer les dépendances ML
make install-ml

# Configuration complète de l'environnement de développement
make setup
```

## 🧪 Tests

```bash
# Tous les tests avec couverture
make test

# Tests unitaires uniquement
make test-unit

# Tests d'intégration
make test-integration

# Tests end-to-end
make test-e2e

# Tests rapides (exclure les tests lents)
make test-fast

# Tests ML spécifiques
make test-ml

# Tests API
make test-api

# Ré-exécuter les tests échoués
make test-failed

# Rapport de couverture détaillé
make coverage

# Avec les scripts utilitaires
./scripts/run_tests.sh all          # Tous les tests
./scripts/run_tests.sh unit         # Tests unitaires
./scripts/run_tests.sh integration  # Tests d'intégration
./scripts/run_tests.sh fast         # Tests rapides
```

## 🎨 Qualité du code

```bash
# Vérifier le formatage et la qualité
make lint

# Formater automatiquement le code
make format

# Vérifications système Django
make check

# Exécuter les hooks pre-commit
make pre-commit
# ou
pre-commit run --all-files

# Vérification rapide avant commit
make quick-check  # format + lint + tests rapides
```

## 🗄️ Base de données

```bash
# Créer les migrations
make makemigrations
# ou
python manage.py makemigrations --settings=config.settings.development

# Appliquer les migrations
make migrate
# ou
python manage.py migrate --settings=config.settings.development

# Charger les données de démonstration
make seed-data
# ou
python manage.py seed_future_skills --settings=config.settings.development

# Recalculer les prédictions
make recalculate
# ou
python manage.py recalculate_future_skills --settings=config.settings.development

# Créer un superutilisateur
make createsuperuser
# ou
python manage.py createsuperuser --settings=config.settings.development

# Shell Django
make shell
# ou
python manage.py shell --settings=config.settings.development
```

## 🐳 Docker

```bash
# Construire les images Docker
make docker-build

# Démarrer l'environnement de développement
make docker-up

# Arrêter les conteneurs
make docker-down

# Démarrer l'environnement de production
make docker-prod

# Voir les logs
make docker-logs
# ou
./scripts/docker_build.sh logs web

# Ouvrir un shell dans le conteneur web
make docker-shell
# ou
./scripts/docker_build.sh shell

# Exécuter les tests dans Docker
make docker-test

# Nettoyer les ressources Docker
make docker-clean
# ou
./scripts/docker_build.sh clean

# Avec les scripts utilitaires
./scripts/docker_build.sh dev     # Démarrer dev
./scripts/docker_build.sh prod    # Démarrer prod
./scripts/docker_build.sh status  # Statut des conteneurs
```

## 🤖 Machine Learning

```bash
# Préparer le dataset
make ml-prepare
# ou
./scripts/ml_train.sh prepare

# Exécuter les expériences de modèles
make ml-experiment
# ou
./scripts/ml_train.sh experiment

# Évaluer les modèles entraînés
make ml-evaluate
# ou
./scripts/ml_train.sh evaluate

# Entraîner un modèle spécifique
make ml-train MODEL_VERSION=v2
# ou
./scripts/ml_train.sh train random_forest

# Comparer les performances des modèles
make ml-compare
# ou
./scripts/ml_train.sh compare

# Pipeline complet de réentraînement
make ml-retrain
# ou
./scripts/ml_train.sh retrain

# Analyse d'explicabilité
make ml-explainability
# ou
./scripts/ml_train.sh explainability

# Générer des prédictions pour un employé
./scripts/ml_train.sh predict <employee_id>

# Surveiller les performances
./scripts/ml_train.sh monitor
```

## 🧹 Nettoyage

```bash
# Nettoyer les fichiers temporaires
make clean

# Nettoyer les fichiers cache Python
make clean-pyc

# Nettoyer les artefacts de tests
make clean-test

# Nettoyer les fichiers de modèles ML (attention!)
make clean-models

# Nettoyage complet
make clean-all
```

## 🔄 Workflows rapides

```bash
# Vérification rapide avant commit
make quick-check  # format + lint + tests rapides

# Simulation complète du CI
make ci  # install + migrate + lint + test

# Cycle de développement
make dev  # migrate + seed-data + serve

# Vérifications avant déploiement en production
make prod-check  # lint + test + docker-build
```

## 📚 Documentation et ressources

```bash
# Afficher l'aide du Makefile
make help

# Documentation des scripts
cat scripts/README.md

# Documentation des tests
cat tests/README.md

# Documentation ML
cat ml/README.md
cat ml/docs/quick_reference.md

# Architecture du projet
cat docs/architecture/
```

## 🔗 Liens utiles

### Documentation

- [Guide de développement](../README.md)
- [Documentation de l'architecture](../architecture/)
- [Documentation de l'API](../api/)
- [Guide de déploiement](../deployment/)
- [Documentation ML](../../ml/README.md)
- [Guide des tests](../../tests/README.md)
- [Guide des scripts](../../scripts/README.md)

### Accès web

- **Application**: http://localhost:8000/
- **Admin Django**: http://localhost:8000/admin/
- **API**: http://localhost:8000/api/
- **Documentation API**: http://localhost:8000/api/docs/

### Commandes avancées

```bash
# Utiliser un settings spécifique
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check

# Exécuter des tests spécifiques
pytest tests/integration/test_prediction_flow.py::TestPredictionFlow::test_complete_prediction_flow -v

# Générer un rapport de couverture spécifique
pytest --cov=future_skills/services --cov-report=html

# Pre-commit pour des fichiers spécifiques
pre-commit run black --files future_skills/models.py

# Jupyter notebooks
jupyter notebook ml/notebooks/dataset_analysis.ipynb
jupyter notebook ml/notebooks/explainability_analysis.ipynb
```

# Installer les dépendances

pip install -r requirements.txt

# Mettre à jour les dépendances

pip list --outdated

# Geler les dépendances actuelles

pip freeze > requirements.txt

````

## 🔍 Vérifications

```bash
# Vérifier les problèmes du projet
python manage.py check

# Vérifier les migrations manquantes
python manage.py makemigrations --dry-run --verbosity 3

# Afficher les migrations appliquées
python manage.py showmigrations
````

## 🌐 API Testing

```bash
# Tester les endpoints avec curl

# Liste des prédictions
curl http://localhost:8000/api/future-skills/predictions/

# Créer une nouvelle prédiction (nécessite authentification)
curl -X POST http://localhost:8000/api/future-skills/predictions/run/ \
  -H "Content-Type: application/json" \
  -d '{"parameters": {}}'

# Générer des recommandations
curl -X POST http://localhost:8000/api/future-skills/recommendations/generate/ \
  -H "Content-Type: application/json"
```

## 📝 Documentation

```bash
# Générer la documentation des modèles
python manage.py graph_models future_skills -o docs/models.png

# Lister toutes les URLs
python manage.py show_urls
```

## 🐳 Docker (si configuré)

```bash
# Build de l'image
docker build -t smarthr360-m3 .

# Lancer le conteneur
docker run -p 8000:8000 smarthr360-m3

# Docker Compose
docker-compose up
docker-compose down
```

## 📊 Statistiques du projet

```bash
# Compter les lignes de code
find . -name "*.py" -not -path "*/migrations/*" -not -path "*/__pycache__/*" -not -path "*/venv/*" -not -path "*/.venv/*" | xargs wc -l

# Nombre de tests
grep -r "def test_" future_skills/tests/ | wc -l

# Nombre de modèles
grep -r "class.*models.Model" future_skills/models.py | wc -l
```

## 🔐 Variables d'environnement

```bash
# Créer un fichier .env (à la racine)
cat > .env << EOF
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
EOF

# Charger les variables d'environnement
export $(cat .env | xargs)
```

## 📤 Git

```bash
# Statut
git status

# Ajouter tous les changements
git add .

# Commit
git commit -m "Message descriptif"

# Push
git push origin main

# Créer une branche
git checkout -b feature/nouvelle-fonctionnalite

# Voir l'historique
git log --oneline --graph
```

---

**Astuce** : Créer des alias dans votre shell pour les commandes fréquentes :

```bash
# Ajouter à ~/.bashrc ou ~/.zshrc
alias dj="python manage.py"
alias djrun="python manage.py runserver"
alias djtest="python manage.py test"
alias djmig="python manage.py makemigrations && python manage.py migrate"
alias covtest="coverage run manage.py test && coverage report"
```

Puis recharger : `source ~/.bashrc` ou `source ~/.zshrc`

Usage : `dj runserver`, `djtest future_skills`, etc.

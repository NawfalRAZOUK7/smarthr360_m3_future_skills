# Commandes Utiles — Module 3 : Future Skills

## 🚀 Démarrage rapide

```bash
# Activer l'environnement virtuel
source .venv/bin/activate  # Mac/Linux
# ou
.venv\Scripts\activate  # Windows

# Lancer le serveur
python manage.py runserver
```

## 🧪 Tests

```bash
# Exécuter tous les tests du module
python manage.py test future_skills

# Tests avec couverture
coverage run manage.py test future_skills
coverage report
coverage html  # Génère htmlcov/index.html

# Ouvrir le rapport HTML
open htmlcov/index.html  # Mac
# ou
xdg-open htmlcov/index.html  # Linux
# ou
start htmlcov/index.html  # Windows
```

## 🗄️ Base de données

```bash
# Créer/Appliquer les migrations
python manage.py makemigrations
python manage.py migrate

# Charger les données de démonstration
python manage.py loaddata future_skills_demo

# Créer un superutilisateur
python manage.py createsuperuser

# Shell Django
python manage.py shell
```

## 🔧 Commandes personnalisées

```bash
# Initialiser les données de démo
python manage.py seed_future_skills

# Recalculer les prédictions
python manage.py recalculate_future_skills

# Exporter le dataset pour l'entraînement ML
python manage.py export_future_skills_dataset
```

## 🤖 Machine Learning

```bash
# Entraîner le modèle ML
python ml/train_future_skills_model.py

# Avec paramètres personnalisés
python ml/train_future_skills_model.py \
  --dataset ml/future_skills_dataset.csv \
  --output ml/future_skills_model.pkl \
  --test-size 0.2

# Évaluer et comparer les performances (ML vs Règles)
python ml/evaluate_future_skills_models.py

# Avec paramètres personnalisés
python ml/evaluate_future_skills_models.py \
  --dataset ml/future_skills_dataset.csv \
  --model ml/future_skills_model.pkl \
  --output docs/COMPARISON_REPORT.md \
  --json-output ml/evaluation_results.json

# Workflow complet ML
python manage.py export_future_skills_dataset && \
python ml/train_future_skills_model.py && \
python ml/evaluate_future_skills_models.py
```

## 📊 Administration

```bash
# Accéder à l'admin Django
# URL : http://localhost:8000/admin/
```

## 🧹 Nettoyage

```bash
# Supprimer les fichiers de migration (attention !)
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# Supprimer la base de données SQLite (réinitialisation complète)
rm db.sqlite3

# Supprimer les fichiers de cache Python
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Supprimer les rapports de couverture
rm -rf htmlcov .coverage
```

## 📦 Dépendances

```bash
# Installer les dépendances
pip install -r requirements.txt

# Mettre à jour les dépendances
pip list --outdated

# Geler les dépendances actuelles
pip freeze > requirements.txt
```

## 🔍 Vérifications

```bash
# Vérifier les problèmes du projet
python manage.py check

# Vérifier les migrations manquantes
python manage.py makemigrations --dry-run --verbosity 3

# Afficher les migrations appliquées
python manage.py showmigrations
```

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

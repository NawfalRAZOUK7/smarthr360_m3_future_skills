# 🔬 Comparaison des Modèles - Future Skills Prediction

**Date de l'expérimentation** : 2025-11-27 11:52

---

## 📊 Tableau Comparatif Global

| Rang | Modèle | Accuracy | Precision | Recall | F1-Score | CV F1 (±std) | Temps (s) |
|------|--------|----------|-----------|--------|----------|--------------|----------|
| 🥇 | **LogisticRegression** | 0.9861 | 0.9867 | 0.9861 | 0.9862 | 0.9965 (±0.0071) | 0.02 |
| 🥈 | **RandomForest** | 0.9861 | 0.9864 | 0.9861 | 0.9860 | 0.9929 (±0.0087) | 0.19 |
| 🥉 | **RandomForest_tuned** | 0.9861 | 0.9864 | 0.9861 | 0.9860 | 0.9929 (±0.0087) | 0.31 |

### 🏆 Meilleur Modèle : LogisticRegression

- **F1-Score** : 0.9862
- **Accuracy** : 0.9861
- **Description** : Modèle linéaire régularisé - Simple et rapide
- **Temps d'entraînement** : 0.02s

---

## 📈 Performance par Classe

### Classe : HIGH

| Modèle | Accuracy | Support |
|--------|----------|----------|
| LogisticRegression | 100.00% | 24 |
| RandomForest | 95.83% | 24 |
| RandomForest_tuned | 95.83% | 24 |

### Classe : MEDIUM

| Modèle | Accuracy | Support |
|--------|----------|----------|
| LogisticRegression | 97.92% | 48 |
| RandomForest | 100.00% | 48 |
| RandomForest_tuned | 100.00% | 48 |

---

## ⚙️ Configurations des Modèles

### LogisticRegression

**Description** : Modèle linéaire régularisé - Simple et rapide

**Hyperparamètres** :
- `C` = 1.0
- `max_iter` = 1000
- `class_weight` = balanced
- `multi_class` = multinomial

### RandomForest

**Description** : Baseline actuelle - Ensemble d'arbres de décision

**Hyperparamètres** :
- `n_estimators` = 200
- `max_depth` = None
- `class_weight` = balanced

### RandomForest_tuned

**Description** : RandomForest avec hyperparamètres ajustés

**Hyperparamètres** :
- `n_estimators` = 300
- `max_depth` = 20
- `min_samples_split` = 5
- `min_samples_leaf` = 2
- `class_weight` = balanced

---

## 💡 Recommandations

### Choix du Modèle en Production

**Baseline (RandomForest)** : F1-score = 0.9860

**Meilleure alternative** : LogisticRegression (amélioration de +0.02%)

### Critères de Sélection

1. **Performance** : F1-score pondéré (objectif principal)
2. **Stabilité** : Variance du cross-validation (CV std faible préféré)
3. **Interprétabilité** : Capacité à expliquer les prédictions (important pour l'audit)
4. **Temps d'entraînement** : Contraintes de réentraînement régulier
5. **Maintenance** : Simplicité de mise à jour et de déploiement

### Politique de Choix de Modèle

**Le modèle RandomForest est actuellement retenu pour les raisons suivantes** :

- ✅ **Stabilité** : Performance robuste sur différents ensembles de validation
- ✅ **Simplicité** : Pas de dépendances complexes (pure scikit-learn)
- ✅ **Interprétabilité** : Feature importance facilement calculable
- ✅ **Maintenance** : Entraînement et déploiement simples
- ✅ **Pas de sur-apprentissage** : Bonne généralisation grâce à l'ensemble d'arbres

**Architecture extensible** :

L'architecture de la pipeline supporte le remplacement par un autre modèle tant que l'interface de prédiction `(level: LOW/MEDIUM/HIGH, score: 0-100)` reste identique.

Pour changer de modèle, il suffit de :
1. Remplacer l'estimateur dans `ml/train_future_skills_model.py`
2. Réentraîner avec `python ml/train_future_skills_model.py`
3. Recharger le nouveau modèle dans `future_skills/ml_model.py`
4. Aucun changement nécessaire dans les APIs ou la logique métier

---

## 🔄 Prochaines Étapes

- [ ] Tester l'hyperparameter tuning (GridSearch/RandomSearch)
- [ ] Évaluer l'impact de features additionnelles
- [ ] Monitorer les performances en production
- [ ] Définir un seuil de dégradation pour déclencher un réentraînement

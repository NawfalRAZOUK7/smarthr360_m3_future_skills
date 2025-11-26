# USERS_PERMISSIONS_DOCUMENTATION — Module 3 : Prédiction des compétences futures

Ce document décrit les droits d’accès au **Module 3 — Future Skills Prediction**
dans le cadre du projet SmartHR360.

## 1. Rôles (Groupes Django)

Les rôles sont représentés par des **Groupes Django** :

- `DRH`
- `RESPONSABLE_RH`
- `MANAGER`

Un utilisateur peut appartenir à plusieurs groupes.  
Le compte `superuser` (admin Django) dispose de tous les droits par défaut.

## 2. Permissions DRF (future_skills/permissions.py)

Deux classes de permissions spécifiques sont définies :

### 2.1. IsHRStaff

- Fichier : `future_skills/permissions.py`
- Groupes autorisés :
  - `DRH`
  - `RESPONSABLE_RH`
- Description :
  - Permet l’accès uniquement aux membres du **staff RH**.

Utilisation principale :
- Endpoint de recalcul des prédictions (action critique).

### 2.2. IsHRStaffOrManager

- Fichier : `future_skills/permissions.py`
- Groupes autorisés :
  - `DRH`
  - `RESPONSABLE_RH`
  - `MANAGER`
- Description :
  - Permet l’accès aux membres du staff RH et aux managers opérationnels.

Utilisation principale :
- Consultation des prédictions et des tendances marché.

## 3. Endpoints du Module 3 et droits d’accès

Les endpoints sont exposés via `future_skills/urls.py`
et inclus sous le préfixe `/api/` dans `config/urls.py`.

### 3.1. GET /api/future-skills/

- Vue : `FutureSkillPredictionListAPIView`
- Permissions : `IsHRStaffOrManager`
- Rôles autorisés :
  - DRH
  - Responsable RH
  - Manager
- Description :
  - Permet de **consulter les prédictions** de compétences futures.
- Filtres :
  - `job_role_id` (int)
  - `horizon_years` (int)

### 3.2. POST /api/future-skills/recalculate/

- Vue : `RecalculateFutureSkillsAPIView`
- Permissions : `IsHRStaff`
- Rôles autorisés :
  - DRH
  - Responsable RH
- Corps JSON (optionnel) :
  - `{"horizon_years": 5}`
- Description :
  - Lance le **recalcul de toutes les prédictions** avec le moteur de règles.
  - Crée un enregistrement `PredictionRun` pour audit.

### 3.3. GET /api/market-trends/

- Vue : `MarketTrendListAPIView`
- Permissions : `IsHRStaffOrManager`
- Rôles autorisés :
  - DRH
  - Responsable RH
  - Manager
- Filtres :
  - `year` (int)
  - `sector` (string)
- Description :
  - Permet de **consulter les tendances marché** utilisées comme input
    pour la prédiction des compétences futures.

## 4. Résumé pour la soutenance

- Les **droits fonctionnels** sont alignés avec la réalité métier :
  - Seuls les rôles RH (DRH / Responsable RH) peuvent **recalculer** les prédictions.
  - Les managers peuvent **consulter** les résultats pour leur périmètre.
- Les permissions sont implémentées au niveau :
  - des **Groupes Django** (rôles),
  - des **permissions DRF** (`IsHRStaff`, `IsHRStaffOrManager`),
  - des **vues API** (Module 3).

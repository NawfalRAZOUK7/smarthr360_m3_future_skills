# Prediction Skills Migration & Alignment Notes

Objectif: documenter les changements a mener pour aligner l'authentification entre `prediction_skills` (source actuelle) et `auth` (base avancee), et preparer une implementation commune (email-first, roles unifies, securite renforcee, conventions de reponse).

## 1) Modele utilisateur (source commune)
- Reference prediction_skills: Django `auth_user` (username requis), roles via groupes DRH/RESPONSABLE_RH/MANAGER.
- Reference auth: `auth/accounts/models.py` (`accounts.User` email-first, roles enum EMPLOYEE/MANAGER/HR/ADMIN, is_email_verified, LoginAttempt, LoginActivity).
- Decision cible: email = identifiant unique. Converger vers `accounts.User` (ou alias `username=email` en transition).
- A prevoir: migration data (username -> email si vide, unicite email, recreation comptes service/test).
- Statut (prediction_skills): username login, email optionnel, pas de role enum, groupes DRH/RESPONSABLE_RH/MANAGER.

## 2) Roles / groupes / permissions
- Groupes prediction_skills: DRH, RESPONSABLE_RH, MANAGER.
- Permissions DRF: `IsHRStaff`, `IsHRStaffOrManager` basees sur groupes.
- Cible: role = source de verite, groupes synchronises pour compat.
- Mapping attendu: DRH/RESPONSABLE_RH -> role HR, MANAGER -> role MANAGER, aucun groupe -> EMPLOYEE.

## 3) Flux d'authentification
- Prediction_skills: JWT obtain/refresh/logout via `config/jwt_auth.py`, login par username.
- Auth: register/login/refresh/logout/me/reset/verif email + enveloppe reponse.
- Actions prevues: accepter email + username, ajouter register/reset/verif si besoin cote prediction_skills, harmoniser logs/monitoring.
- Statut (prediction_skills): endpoints JWT actifs, pas de register/reset/verif email cote API.

## 4) Securite / verrouillage
- Prediction_skills: middleware logging/monitoring, pas de lockout explicite.
- Auth: django-axes + LoginAttempt/Activity.
- Reco: aligner sur django-axes + regles lockout communes.

## 5) JWT / sessions
- Prediction_skills: SimpleJWT settings en `config/jwt_auth.py` (access 30m, refresh 7j, rotation, issuer smarthr360).
- Auth: SimpleJWT dans settings base, claims explicites, blacklist activee.
- Cible: memes durees/issuer/claims, login email-first, rotation/blacklist alignee.

## 6) Structure des reponses API
- Prediction_skills: reponses DRF brutes.
- Auth: enveloppe standard `{"data": ..., "meta": {"success": true}}`.
- Decision: adopter l'enveloppe commune ou documenter l'exception.

## 7) Etapes techniques proposees (prediction_skills)
1) Aligner le modele user: preparer la transition vers `accounts.User` (email unique, username compat).
2) Harmoniser roles/groupes: mapper DRH/RESPONSABLE_RH/MANAGER vers roles communs.
3) Aligner permissions DRF: utiliser roles ou groupes synchronises.
4) Unifier flux JWT (login email + username) et ajouter register/reset/verif si requis.
5) Securite: activer lockout (django-axes) si on garde l'auth local.
6) Standardiser les reponses API ou documenter les exceptions.
7) Tests: adapter tests auth/permissions + verifs de non-regression.

Statut (prediction_skills):
- [ ] 1) Modele user aligne (email-first + compat username).
- [ ] 2) Mapping roles/groupes + sync.
- [ ] 3) Permissions DRF alignees.
- [ ] 4) Flux auth (login/register/reset/verif) aligne.
- [ ] 5) Securite/lockout alignee.
- [ ] 6) Reponses API standardisees.
- [ ] 7) Tests adaptes.

## 8) Points de migration / data
- Verifier unicite email (case-insensitive).
- Completer les emails manquants avant bascule.
- Conserver hash passwords si memes algo Django.
- Verifier mapping role/groupe avant migration finale.
- Nettoyer tokens de test et forcer un logout global si besoin.

### Checklist data (prediction_skills -> auth)
1) **Inventaire source**
   - Tables: `auth_user`, `auth_group`, `auth_user_groups`.
   - Champs minimaux: `id, username, email, first_name, last_name, is_active, is_staff, is_superuser, last_login, date_joined`.
2) **Mapping roles**
   - DRH/RESPONSABLE_RH -> role HR.
   - MANAGER -> role MANAGER.
   - Aucun groupe -> EMPLOYEE.
   - is_superuser -> ADMIN.
3) **Email / username**
   - Normaliser email (lowercase/trim).
   - Si email manquant -> placeholder + liste a corriger.
   - Username requis cote auth: conserver si unique, sinon email + suffix.
4) **Validation post-migration**
   - Comparer counts, tester login email + username, verifier groups sync.

## 9) Rollout conseille
- Phase 1 (dev): documenter l'alignement et stabiliser permissions.
- Phase 2 (integration): basculer prediction_skills vers auth unifie.
- Phase 3 (prod): migration data + surveillance lockouts/logs.

## 10) Questions en suspens
- Role ADMIN reserve au staff technique ou aussi DRH ?
- Enveloppe reponse: generalisation a toutes les APIs ou exception ?
- Duree de retro-compat (accepter username + email).

## Rappel post-migration
- Ajouter les vraies adresses email des comptes placeholder et mettre a jour `auth/db.sqlite3` apres finalisation de prediction_skills.

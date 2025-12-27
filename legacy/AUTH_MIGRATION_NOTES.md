# Prediction Skills Migration & Alignment Notes

Objectif: documenter les changements a mener pour aligner l'authentification entre `prediction_skills` (source actuelle) et `auth` (base avancee), et preparer une implementation commune (email-first, roles unifies, securite renforcee, conventions de reponse).

## 1) Modele utilisateur (source commune)
- Reference auth: `auth/accounts/models.py` (`accounts.User` email-first, roles enum EMPLOYEE/MANAGER/HR/ADMIN, is_email_verified, LoginAttempt, LoginActivity).
- Reference prediction_skills: Django `auth_user` (username requis), roles via groupes DRH/RESPONSABLE_RH/MANAGER.
- Decision cible: email = identifiant unique. Converger vers `accounts.User` (ou alias `username=email` en transition). Garder `role` enum comme source d'autorite.
- Statut (auth): compat `username` ajoute, normalisation email + contrainte unique case-insensitive, `email_verified_at`, index sur `role`.
- Statut (prediction_skills): `accounts.User` ajoute (email-first, role enum, username compat, email_verified_at, contrainte email CI).

## 2) Roles / groupes / permissions
- Roles auth: EMPLOYEE, MANAGER, HR, ADMIN (ADMIN = admin general/technique).
- Groupes auth: HR, HR_ADMIN, MANAGER, MANAGER_ADMIN, EMPLOYEE, EMPLOYEE_ADMIN, AUDITOR, SECURITY_ADMIN, SUPPORT.
- Strategie auth: role = source de verite, groupes synchronises (base) pour compat. Les groupes "*_ADMIN" sont geres manuellement. ADMIN bypass toutes permissions.
- Permissions auth: `IsAuditorReadOnly`, `IsSecurityAdmin`, `IsSupport` + helpers d'acces (roles + groupes).
- Statut auth: HR a acces aux endpoints manager via `IsManagerOrAbove`. AUDITOR en lecture seule sur HR/Reviews/Wellbeing; SUPPORT autorise sur `/api/auth/users/`.
- Prediction_skills: groupes DRH/RESPONSABLE_RH/MANAGER uniquement, permissions `IsHRStaff`, `IsHRStaffOrManager`.
- Cible prediction_skills: mapper DRH/RESPONSABLE_RH -> role HR, MANAGER -> role MANAGER, aucun groupe -> EMPLOYEE, superuser -> ADMIN.

## 3) Flux d'authentification
- Auth: register, login (email ou username), refresh, logout (blacklist), me, reset mot de passe, verification email, suivi login, lockout.
- Prediction_skills: JWT obtain/refresh/logout via `config/jwt_auth.py`, login par username.
- Actions prevues: accepter email + username, ajouter register/reset/verify si besoin cote prediction_skills, harmoniser logs/monitoring.
- Statut (auth): login accepte email ou username; username requis a l'inscription.
- Statut (prediction_skills): endpoints JWT actifs, pas de register/reset/verify cote API.

## 4) Securite / verrouillage
- Auth: django-axes + LoginAttempt/Activity. Seuils aligns sur `LOGIN_MAX_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES` (par defaut 5 / 30 min).
- Prediction_skills: middleware logging/monitoring, pas de lockout explicite.
- Reco: aligner prediction_skills sur django-axes si l'auth locale reste active.

## 5) JWT / sessions
- Prediction_skills: SimpleJWT settings en `config/jwt_auth.py` (access 30m, refresh 7j, rotation, issuer smarthr360).
- Auth: SimpleJWT dans settings base, claims explicites, blacklist activee.
- Cible: memes durees/issuer/claims, login email-first, rotation/blacklist alignee.

## 6) Structure des reponses API
- Auth: enveloppe standard `{"data": ..., "meta": {"success": true}}` via `ApiResponseMixin`.
- Prediction_skills: reponses DRF brutes.
- Decision: adopter l'enveloppe commune ou documenter l'exception.

## 7) Etapes techniques proposees (prediction_skills)
1) Aligner le modele user: preparer la transition vers `accounts.User` (email unique, username compat).
2) Harmoniser roles/groupes: mapper DRH/RESPONSABLE_RH/MANAGER vers roles communs + sync groupes de base.
3) Aligner permissions DRF: utiliser roles ou groupes synchronises (incl. AUDITOR/SECURITY_ADMIN/SUPPORT si necessaire).
4) Unifier flux JWT (login email + username) et ajouter register/reset/verify si requis.
5) Securite: activer lockout (django-axes) si on garde l'auth locale.
6) Standardiser les reponses API ou documenter les exceptions.
7) Tests: adapter tests auth/permissions + verifs de non-regression.

Statut (prediction_skills):
- [x] 1) Modele user aligne (email-first + compat username).
- [ ] 2) Mapping roles/groupes + sync.
- [ ] 3) Permissions DRF alignees.
- [ ] 4) Flux auth (login/register/reset/verify) aligne.
- [ ] 5) Securite/lockout alignee.
- [ ] 6) Reponses API standardisees.
- [ ] 7) Tests adaptes.

Statut (auth):
- [x] 1) django-axes active + lockout aligne.
- [x] 2) `accounts.User` en place; commande `migrate_prediction_users` disponible.
- [x] 3) Sync role <-> groupes + permissions DRF alignees.
- [x] 4) Endpoints auth + enveloppe standard + docs/Postman a jour.
- [x] 5) Securite/lockout/headers alignes.
- [x] 6) Tests auth couvrant login/lockout/reset/verify/permissions.
- [x] 7) Warnings pagination corriges + `auth/staticfiles/`.

## 8) Points de migration / data
- Verifier unicite email (case-insensitive).
- Completer les emails manquants avant bascule.
- Conserver hash passwords si memes algo Django.
- Verifier mapping role/groupe avant migration finale.
- Nettoyer tokens de test et forcer un logout global si besoin.

### Script de migration (depuis auth)
- Commande: `python manage.py migrate_prediction_users --source-url <DB_URL>`
- Par defaut: dry-run. Utiliser `--apply` pour ecrire.
- Options utiles: `--update-existing`, `--match-username`, `--mark-verified`, `--default-email-domain`, `--limit`.

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
4) **Dedoublonnage**
   - Detecter doublons email (case-insensitive).
   - Garder is_active True / last_login le plus recent.
5) **Validation post-migration**
   - Comparer counts, tester login email + username, verifier groups sync.

## 9) Rollout conseille
- Phase 1 (dev): documenter l'alignement et stabiliser permissions.
- Phase 2 (integration): basculer prediction_skills vers auth unifie (login email, permissions mappees).
- Phase 3 (prod): migration data + surveillance lockouts/logs.

## 10) Questions en suspens
- Role ADMIN reserve au staff technique ou aussi DRH ?
- Enveloppe reponse: generalisation a toutes les APIs ou exception ?
- Duree de retro-compat (accepter username + email).

## Rappel post-migration
- Ajouter les vraies adresses email des comptes placeholder et mettre a jour `auth/db.sqlite3` apres finalisation de prediction_skills.

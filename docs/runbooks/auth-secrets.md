# Runbook: Auth & Secrets

Goal: rotate secrets and resolve auth issues safely.

1) Inventory
- Identify secrets in use: `SECRET_KEY`, JWT keys/settings, DB/cache/broker creds.

2) Rotate
- Generate new values; update env/secret store and restart services.
- For JWT, consider token invalidation/blacklist if supported.

3) Verify
- Login/auth flows succeed; protected endpoints return 200/201 where expected.
- Unauthorized/forbidden flows still return 401/403.

4) Rollback
- Revert to prior secrets if rotation fails (keep short-lived overlap window if possible).

Notes
- Tests set deterministic SECRET_KEY; production must not rely on test defaults.
- Ensure HTTPS/secure cookies enabled outside test settings; tighten CORS/ALLOWED_HOSTS in prod configs.

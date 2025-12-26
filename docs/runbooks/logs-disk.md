# Runbook: Logs & Disk Pressure

Goal: reclaim space and keep logging healthy.

1) Locate logs/artifacts
- Primary logs under `logs/` and `var/`.
- ML artifacts and runs under `artifacts/` and `mlruns/`.

2) Clean/rotate
- Rotate or truncate large log files (ensure correct permissions).
- Remove stale test artifacts: `make clean-test` (locally). Avoid deleting needed artifacts in prod without backup.

3) Verify
- Ensure services can still write to log directories.
- Check disk free space and restart any components if needed.

4) Preventive
- Configure log rotation in production environment.
- Keep `mlruns/` and large artifacts off the root disk if possible.

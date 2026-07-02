# Module 3 – Combined Execution Checklist (Ordered)

This merges the pending items from `module3_catalog_upgrade_todo.md` and `module3_taxonomy_matrix_plan.md` in the order you should execute.

## 1) Validation & Logging (code)
- [x] Enforce trends/reports to reference a valid `industry_id`.
- [x] Ensure prediction logging includes `industry_id`, `function_id`, and `domain_id` in audit payloads.

## 2) Data Load
- [x] Run migrations (if any pending) and load catalogs (dry-run first, then load).

## 3) Rebuild Derived Data
- [x] Regenerate snapshots with the target cadence (monthly/weekly) and re-run the professional drift pipeline.
  - Note: current run still shows alert-level drift (PSI/KS high). To get a “healthy” baseline (PSI near 0), dampen variability further (e.g., snapshot gen with `--drift-scale 0.0 --seasonal-scale 0.0 --noise-scale 0.0` or lower `apply_time_drift` noise) and rerun.

## 4) Tests
- [x] Add loader validation tests (missing parent IDs, duplicates).
- [x] Add FK lookup tests (trend + economic lookup).
- [x] Add a snapshot variability test (by industry/domain).

## 5) Reporting & Artifacts
- [x] Update Module 3 report with the matrix taxonomy + drift notes.
- [x] Add taxonomy diagram (Industry → Function → Domain → JobRole; Skill ↔ Domain weights).
- [x] Add a table of sample Industries/Functions/Domains used in the dataset.

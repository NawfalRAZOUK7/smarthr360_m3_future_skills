# Module 3 Catalog Upgrade - Mini TODO

Goal: upgrade the multi-file catalogs for Industry x Function with multi-industry coverage,
multi-year signals, multilingual labels, and weighted domain mappings.

- [x] Confirm taxonomy decisions (multi-industry; add function "people-management"; keep IDs in English).
- [x] Decide multilingual storage approach for names/descriptions (use JSON fields on models).
- [x] Update models to support multilingual labels (if needed) and create migration plan.
- [x] Update catalog schema to carry multilingual labels (name_i18n/description_i18n) and weights.
- [x] Expand industries.json and functions.json to final lists (multi-industry).
- [x] Add people-management function and move leadership-management domain under it.
- [x] Assign industry_id for each job role (multi-industry mapping).
- [x] Expand market_trends.json to 2018-2026 for each industry.
- [x] Expand economic_reports.json to 2018-2026 for each industry.
- [x] Update skills.json to use weighted domain mappings for soft skills (cross-domain).
- [x] Update loader to accept weighted mappings and multilingual fields (with backward compatibility).

## Remaining (Ordered)

- [x] Run migrations and load catalogs (dry-run then load).
- [x] Regenerate snapshots and re-run professional drift pipeline.

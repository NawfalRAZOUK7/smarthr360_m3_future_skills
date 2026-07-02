# Module 3 Taxonomy (Industry x Function) - Implementation Plan

Goal: Move to a professional matrix taxonomy (Industry x Function) that is coherent with
Module 3 (market + macro signals + emerging skills) while keeping scope minimal and stable.

## TODO (Short Checklist - Ordered)

- [x] Confirm taxonomy lists: Industries, Functions, Domains per Function.
- [x] Create catalog files under `prediction_skills/data/catalogs/` with IDs and relationships.
- [x] Add models: Industry, Function, Domain, SkillDomainMap (FKs).
- [x] Update JobRole with domain FK (+ optional industry FK).
- [x] Update MarketTrend with industry FK (+ optional function/domain FK).
- [x] Update EconomicReport with industry FK.
- [x] Create loader command to import catalogs with update_or_create and validation.
- [x] Update seeds to call the loader instead of hard-coded lists.
- [x] Update trend/economic lookup functions to use FKs, with legacy fallback.
- [x] Validate trends/reports reference a valid industry_id.
- [x] Ensure prediction logging includes industry/function/domain identifiers in audit payloads.
- [x] Run migrations and load catalogs (dry-run then load).
- [x] Regenerate snapshots and re-run professional drift pipeline.
- [x] Add basic tests for loader validation and FK lookups.
- [x] Update Module 3 report + taxonomy diagram.
- [x] Add a table with sample Industries/Functions/Domains used in the dataset.

## Scope (Target Model)

- [x] Industry dimension (e.g., Banking, Healthcare, Retail, Manufacturing, Tech Services).
- [x] Function dimension (e.g., Technology, HR, Finance, Marketing, Operations, People Management).
- [x] Domain under Function (e.g., Data & AI, Cybersecurity, Cloud/DevOps, IT Ops, Leadership & Management).
- [x] JobRole linked to Domain, with optional Industry link if the role is industry-specific.
- [x] MarketTrend linked to Industry, optional Function/Domain for more precision.
- [x] EconomicReport linked to Industry (stable macro signals).
- [x] Skill remains global; add SkillDomainMap for Skill x Domain mapping with weights.

## Catalog Design (Multi-File Taxonomy)

Create catalog files under `prediction_skills/data/catalogs/`:

- [x] `industries.json` (id, name, description, name_i18n, description_i18n)
- [x] `functions.json` (id, name, description, name_i18n, description_i18n)
- [x] `domains.json` (id, name, function_id, description, name_i18n, description_i18n)
- [x] `skills.json` (name, category, description, domain_weights[] or domain_ids[])
- [x] `job_roles.json` (name, description, domain_id, industry_id?, name_i18n, description_i18n)
- [x] `market_trends.json` (title, year, trend_score, source_name, industry_id, function_id?, domain_id?, title_i18n, description_i18n)
- [x] `economic_reports.json` (title, year, indicator, value, source_name, industry_id, title_i18n, indicator_i18n)
- [x] Multi-year coverage for trends/reports (2018-2026).

Validation rules:
- [x] Domains must reference a valid function_id.
- [x] Job roles must reference a valid domain_id.
- [ ] Trends/reports must reference a valid industry_id.
- [x] SkillDomainMap weights must be 0.0–1.0.

## Models & Migrations (Minimal)

- [x] Add models: Industry, Function, Domain, SkillDomainMap.
- [x] Update JobRole to include domain FK (and optional industry FK).
- [x] Update MarketTrend to include industry FK (and optional function/domain FK).
- [x] Update EconomicReport to include industry FK.
- [x] Add i18n JSON fields for labels (name_i18n, description_i18n, title_i18n, indicator_i18n).
- [x] Keep legacy string fields (department/category/sector) for backward compatibility.

## Services & ML Alignment

- [x] Update `get_market_trend_for_context` to use industry + function/domain FKs.
- [x] Update `get_economic_indicator` to use industry FK.
- [x] Ensure snapshot generation uses new FK fields when present; fall back to legacy fields.
- [x] Ensure prediction logging includes industry/function/domain identifiers in audit payloads.

## Data Seeding & Loader

- [x] Create loader command (idempotent) that reads catalogs and uses update_or_create.
- [x] Update seeds to call the loader instead of hard-coded lists.
- [x] Add a validation step that fails fast on missing parent IDs.

## Reporting & Documentation

- [x] Update Module 3 report to explain the matrix (Industry x Function) taxonomy.
- [x] Add a simple diagram of taxonomy relationships (Industry -> Function -> Domain -> JobRole; Skill -> Domain).
- [x] Add a table with sample Industries/Functions/Domains used in the dataset.

## Testing

- [x] Add unit tests for loader validation (missing parent IDs, duplicate IDs).
- [x] Add tests for trend/economic lookup with FK-based taxonomy.
- [x] Add a snapshot-generation test to confirm variability by industry/domain.

## Risk (last step)

- [ ] Risk: Over-modeling too early can slow delivery and require constant maintenance if the
      taxonomy is not yet stable. Mitigation: implement only the minimal tables now, keep
      the UI simple, and extend once the taxonomy is validated by real data usage.

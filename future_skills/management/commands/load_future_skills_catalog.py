"""Load Future Skills taxonomy catalogs (Industry x Function) into the database."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from future_skills.models import (
    Domain,
    EconomicReport,
    Function,
    Industry,
    JobRole,
    MarketTrend,
    Skill,
    SkillDomainMap,
)


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _require_id(item: dict, label: str) -> str:
    item_id = item.get("id")
    if not item_id:
        raise CommandError(f"Missing id for {label} entry: {item}")
    return item_id


def _ensure_unique(items: list[dict], key: str, label: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        value = item.get(key)
        if not value:
            continue
        value = str(value)
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    if duplicates:
        dup_list = ", ".join(sorted(duplicates))
        raise CommandError(f"Duplicate {label} {key} values: {dup_list}")


def _ensure_unique_by(items: list[dict], key_fn, label: str) -> None:
    seen: set[tuple] = set()
    duplicates: set[tuple] = set()
    for item in items:
        value = key_fn(item)
        if not value:
            continue
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    if duplicates:
        dup_list = ", ".join(sorted(str(value) for value in duplicates))
        raise CommandError(f"Duplicate {label} entries: {dup_list}")


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _select_label(item: dict, primary_key: str, i18n_key: str, fallback: str) -> str:
    primary = item.get(primary_key)
    if primary:
        return primary
    i18n = item.get(i18n_key) or {}
    return i18n.get("en") or i18n.get("fr") or fallback


class Command(BaseCommand):
    """Load taxonomy catalogs for Future Skills."""

    help = "Load multi-file taxonomy catalogs for Future Skills (Industry x Function)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--catalog-dir",
            type=str,
            default=None,
            help="Catalog directory (defaults to BASE_DIR/data/catalogs).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate catalogs without writing to the database.",
        )

    def handle(self, *args, **options):
        catalog_dir = Path(options["catalog_dir"] or (settings.BASE_DIR / "data" / "catalogs"))
        dry_run = options["dry_run"]

        industries_data = _load_json(catalog_dir / "industries.json")
        functions_data = _load_json(catalog_dir / "functions.json")
        domains_data = _load_json(catalog_dir / "domains.json")
        skills_data = _load_json(catalog_dir / "skills.json")
        roles_data = _load_json(catalog_dir / "job_roles.json")
        trends_data = _load_json(catalog_dir / "market_trends.json")
        reports_data = _load_json(catalog_dir / "economic_reports.json")

        if not any(
            [industries_data, functions_data, domains_data, skills_data, roles_data, trends_data, reports_data]
        ):
            raise CommandError(f"No catalogs found in {catalog_dir}")

        _ensure_unique(industries_data, "id", "industry")
        _ensure_unique(functions_data, "id", "function")
        _ensure_unique(domains_data, "id", "domain")
        _ensure_unique(skills_data, "name", "skill")
        _ensure_unique(roles_data, "name", "job role")
        _ensure_unique_by(trends_data, lambda item: (item.get("title"), item.get("year")), "market trend")
        _ensure_unique_by(
            reports_data,
            lambda item: (item.get("title"), item.get("year"), item.get("indicator")),
            "economic report",
        )

        industries_by_id: dict[str, Industry] = {}
        functions_by_id: dict[str, Function] = {}
        domains_by_id: dict[str, Domain] = {}

        self.stdout.write(self.style.WARNING("Loading Industry catalog..."))
        for item in industries_data:
            item_id = _require_id(item, "industry")
            name_i18n = item.get("name_i18n") or {}
            description_i18n = item.get("description_i18n") or {}
            defaults = {
                "name": _select_label(item, "name", "name_i18n", item_id),
                "description": _select_label(item, "description", "description_i18n", None),
                "name_i18n": name_i18n,
                "description_i18n": description_i18n,
            }
            if dry_run:
                industries_by_id[item_id] = Industry(code=item_id, **defaults)
                continue
            industry, _ = Industry.objects.update_or_create(code=item_id, defaults=defaults)
            industries_by_id[item_id] = industry

        self.stdout.write(self.style.WARNING("Loading Function catalog..."))
        for item in functions_data:
            item_id = _require_id(item, "function")
            name_i18n = item.get("name_i18n") or {}
            description_i18n = item.get("description_i18n") or {}
            defaults = {
                "name": _select_label(item, "name", "name_i18n", item_id),
                "description": _select_label(item, "description", "description_i18n", None),
                "name_i18n": name_i18n,
                "description_i18n": description_i18n,
            }
            if dry_run:
                functions_by_id[item_id] = Function(code=item_id, **defaults)
                continue
            function, _ = Function.objects.update_or_create(code=item_id, defaults=defaults)
            functions_by_id[item_id] = function

        self.stdout.write(self.style.WARNING("Loading Domain catalog..."))
        for item in domains_data:
            item_id = _require_id(item, "domain")
            function_id = item.get("function_id")
            if not function_id or function_id not in functions_by_id:
                raise CommandError(f"Domain {item_id} references unknown function_id: {function_id}")
            name_i18n = item.get("name_i18n") or {}
            description_i18n = item.get("description_i18n") or {}
            defaults = {
                "name": _select_label(item, "name", "name_i18n", item_id),
                "description": _select_label(item, "description", "description_i18n", None),
                "name_i18n": name_i18n,
                "description_i18n": description_i18n,
                "function": functions_by_id[function_id],
            }
            if dry_run:
                domains_by_id[item_id] = Domain(code=item_id, **defaults)
                continue
            domain, _ = Domain.objects.update_or_create(code=item_id, defaults=defaults)
            domains_by_id[item_id] = domain

        self.stdout.write(self.style.WARNING("Loading Skills catalog..."))
        for item in skills_data:
            name = item.get("name")
            if not name:
                raise CommandError(f"Skill entry missing name: {item}")
            name_i18n = item.get("name_i18n") or {}
            description_i18n = item.get("description_i18n") or {}
            defaults = {
                "category": item.get("category"),
                "description": _select_label(item, "description", "description_i18n", None),
                "name_i18n": name_i18n,
                "description_i18n": description_i18n,
            }
            if dry_run:
                skill = Skill(name=name, **defaults)
            else:
                skill, _ = Skill.objects.update_or_create(name=name, defaults=defaults)

            domain_weights = item.get("domain_weights")
            if domain_weights is None:
                domain_weights = [{"domain_id": domain_id, "weight": 1.0} for domain_id in (item.get("domain_ids") or [])]

            for mapping in domain_weights:
                domain_id = mapping.get("domain_id")
                weight = _clamp(float(mapping.get("weight", 1.0)), 0.0, 1.0)
                if domain_id not in domains_by_id:
                    raise CommandError(f"Skill {name} references unknown domain_id: {domain_id}")
                if dry_run:
                    continue
                SkillDomainMap.objects.update_or_create(
                    skill=skill,
                    domain=domains_by_id[domain_id],
                    defaults={"weight": weight},
                )

        self.stdout.write(self.style.WARNING("Loading Job Roles catalog..."))
        for item in roles_data:
            name = item.get("name")
            if not name:
                raise CommandError(f"Job role entry missing name: {item}")
            domain_id = item.get("domain_id")
            if not domain_id or domain_id not in domains_by_id:
                raise CommandError(f"Job role {name} references unknown domain_id: {domain_id}")

            industry_id = item.get("industry_id")
            industry = industries_by_id.get(industry_id) if industry_id else None
            domain = domains_by_id[domain_id]
            name_i18n = item.get("name_i18n") or {}
            description_i18n = item.get("description_i18n") or {}
            defaults = {
                "description": _select_label(item, "description", "description_i18n", None),
                "name_i18n": name_i18n,
                "description_i18n": description_i18n,
                "department": domain.function.name,
                "industry": industry,
                "domain": domain,
            }
            if dry_run:
                continue
            JobRole.objects.update_or_create(name=name, defaults=defaults)

        self.stdout.write(self.style.WARNING("Loading Market Trends catalog..."))
        for item in trends_data:
            title = item.get("title")
            year = item.get("year")
            if not title or not year:
                raise CommandError(f"Market trend entry missing title/year: {item}")
            industry_id = item.get("industry_id")
            if not industry_id or industry_id not in industries_by_id:
                raise CommandError(f"Market trend {title} ({year}) missing or invalid industry_id: {industry_id}")
            industry = industries_by_id[industry_id]
            function_id = item.get("function_id")
            function = functions_by_id.get(function_id) if function_id else None
            domain_id = item.get("domain_id")
            domain = domains_by_id.get(domain_id) if domain_id else None

            trend_score = item.get("trend_score", 0.5)
            trend_score = _clamp(float(trend_score), 0.0, 1.0)

            sector_value = None
            if function:
                sector_value = function.name
            else:
                sector_value = industry.name

            title_i18n = item.get("title_i18n") or {}
            description_i18n = item.get("description_i18n") or {}
            defaults = {
                "source_name": item.get("source_name", "Catalog"),
                "sector": sector_value,
                "trend_score": trend_score,
                "description": _select_label(item, "description", "description_i18n", None),
                "title_i18n": title_i18n,
                "description_i18n": description_i18n,
                "industry": industry,
                "function": function,
                "domain": domain,
            }
            if dry_run:
                continue
            MarketTrend.objects.update_or_create(title=title, year=year, defaults=defaults)

        self.stdout.write(self.style.WARNING("Loading Economic Reports catalog..."))
        for item in reports_data:
            title = item.get("title")
            year = item.get("year")
            indicator = item.get("indicator")
            if not title or not year or not indicator:
                raise CommandError(f"Economic report entry missing title/year/indicator: {item}")
            industry_id = item.get("industry_id")
            if not industry_id or industry_id not in industries_by_id:
                raise CommandError(f"Economic report {title} ({year}) missing or invalid industry_id: {industry_id}")
            industry = industries_by_id[industry_id]

            title_i18n = item.get("title_i18n") or {}
            indicator_i18n = item.get("indicator_i18n") or {}
            value = _clamp(float(item.get("value", 50.0)), 0.0, 100.0)
            defaults = {
                "source_name": item.get("source_name", "Catalog"),
                "value": value,
                "sector": industry.name if industry else None,
                "industry": industry,
                "title_i18n": title_i18n,
                "indicator_i18n": indicator_i18n,
            }
            if dry_run:
                continue
            EconomicReport.objects.update_or_create(
                title=title,
                year=year,
                indicator=indicator,
                defaults=defaults,
            )

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Catalog validation complete (dry run)."))
        else:
            self.stdout.write(self.style.SUCCESS("Catalog load complete."))

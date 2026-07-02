# future_skills/tests/test_catalog_loader.py

import json
import tempfile
from datetime import date
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from future_skills.models import (
    Domain,
    EconomicReport,
    Function,
    Industry,
    JobRole,
    MarketTrend,
    Skill,
    FutureSkillSnapshot,
)
from future_skills.services.snapshot_service import get_economic_indicator, get_market_trend_for_context


def _write_json(path: Path, payload: list[dict]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _base_catalogs() -> dict[str, list[dict]]:
    return {
        "industries": [{"id": "tech-services", "name": "Technology Services"}],
        "functions": [{"id": "technology", "name": "Technology"}],
        "domains": [
            {
                "id": "data-ai",
                "name": "Data & AI",
                "function_id": "technology",
            }
        ],
        "skills": [
            {
                "name": "Python",
                "category": "Tech",
                "domain_ids": ["data-ai"],
            }
        ],
        "job_roles": [
            {
                "name": "Data Engineer",
                "domain_id": "data-ai",
                "industry_id": "tech-services",
            }
        ],
        "market_trends": [
            {
                "title": "AI adoption",
                "year": 2024,
                "trend_score": 0.6,
                "industry_id": "tech-services",
            }
        ],
        "economic_reports": [
            {
                "title": "Tech outlook",
                "year": 2024,
                "indicator": "Sector Index",
                "value": 52.0,
                "industry_id": "tech-services",
            }
        ],
    }


class CatalogLoaderValidationTests(TestCase):
    def _write_catalog_dir(self, override: dict[str, list[dict]] | None = None) -> Path:
        catalogs = _base_catalogs()
        if override:
            catalogs.update(override)

        temp_dir = Path(tempfile.mkdtemp())
        _write_json(temp_dir / "industries.json", catalogs["industries"])
        _write_json(temp_dir / "functions.json", catalogs["functions"])
        _write_json(temp_dir / "domains.json", catalogs["domains"])
        _write_json(temp_dir / "skills.json", catalogs["skills"])
        _write_json(temp_dir / "job_roles.json", catalogs["job_roles"])
        _write_json(temp_dir / "market_trends.json", catalogs["market_trends"])
        _write_json(temp_dir / "economic_reports.json", catalogs["economic_reports"])
        return temp_dir

    def test_loader_rejects_duplicate_ids(self):
        temp_dir = self._write_catalog_dir(
            {
                "industries": [
                    {"id": "tech-services", "name": "Technology Services"},
                    {"id": "tech-services", "name": "Duplicate"},
                ]
            }
        )
        with self.assertRaises(CommandError):
            call_command("load_future_skills_catalog", catalog_dir=str(temp_dir))

    def test_loader_requires_industry_id_for_trends(self):
        temp_dir = self._write_catalog_dir(
            {
                "market_trends": [
                    {"title": "Missing industry", "year": 2024, "trend_score": 0.5}
                ]
            }
        )
        with self.assertRaises(CommandError):
            call_command("load_future_skills_catalog", catalog_dir=str(temp_dir))

    def test_loader_requires_industry_id_for_reports(self):
        temp_dir = self._write_catalog_dir(
            {
                "economic_reports": [
                    {
                        "title": "Missing industry",
                        "year": 2024,
                        "indicator": "Sector Index",
                        "value": 50.0,
                    }
                ]
            }
        )
        with self.assertRaises(CommandError):
            call_command("load_future_skills_catalog", catalog_dir=str(temp_dir))


class CatalogLookupTests(TestCase):
    def setUp(self):
        self.industry_banking = Industry.objects.create(code="banking", name="Banking")
        self.industry_tech = Industry.objects.create(code="tech-services", name="Technology Services")
        self.function = Function.objects.create(code="technology", name="Technology")
        self.domain = Domain.objects.create(code="data-ai", name="Data & AI", function=self.function)
        self.job_role = JobRole.objects.create(
            name="Risk Analyst",
            department="Tech",
            industry=self.industry_banking,
            domain=self.domain,
        )
        self.skill = Skill.objects.create(name="Risk Modeling", category="Finance")

        MarketTrend.objects.create(
            title="Banking trend",
            source_name="Test",
            year=2024,
            sector="Banking",
            trend_score=0.2,
            industry=self.industry_banking,
        )
        MarketTrend.objects.create(
            title="Tech trend",
            source_name="Test",
            year=2024,
            sector="Tech",
            trend_score=0.9,
            industry=self.industry_tech,
        )
        EconomicReport.objects.create(
            title="Banking outlook",
            source_name="Test",
            year=2024,
            indicator="Sector Index",
            value=40.0,
            sector="Banking",
            industry=self.industry_banking,
        )

    def test_get_market_trend_for_context_uses_industry(self):
        score = get_market_trend_for_context(self.job_role, self.skill, as_of_date=date(2024, 1, 1))
        self.assertAlmostEqual(score, 0.2, places=3)

    def test_get_economic_indicator_uses_industry(self):
        value = get_economic_indicator(self.job_role, as_of_date=date(2024, 1, 1))
        self.assertAlmostEqual(value, 0.4, places=3)


class SnapshotVariabilityTests(TestCase):
    def test_snapshot_trend_varies_by_industry(self):
        industry_a = Industry.objects.create(code="banking", name="Banking")
        industry_b = Industry.objects.create(code="retail", name="Retail")
        function = Function.objects.create(code="technology", name="Technology")
        domain = Domain.objects.create(code="data-ai", name="Data & AI", function=function)
        skill = Skill.objects.create(name="Data Engineering", category="Tech")

        job_a = JobRole.objects.create(
            name="Data Engineer Banking",
            department="Technology",
            industry=industry_a,
            domain=domain,
        )
        job_b = JobRole.objects.create(
            name="Data Engineer Retail",
            department="Technology",
            industry=industry_b,
            domain=domain,
        )

        MarketTrend.objects.create(
            title="Banking data trend",
            source_name="Test",
            year=2025,
            sector="Banking",
            trend_score=0.2,
            industry=industry_a,
        )
        MarketTrend.objects.create(
            title="Retail data trend",
            source_name="Test",
            year=2025,
            sector="Retail",
            trend_score=0.7,
            industry=industry_b,
        )

        call_command(
            "generate_future_skill_snapshots",
            as_of_date="2025-01-01",
            frequency="monthly",
            overwrite=True,
            drift_scale=0.0,
            seasonal_scale=0.0,
            noise_scale=0.0,
        )

        snap_a = FutureSkillSnapshot.objects.get(job_role=job_a, skill=skill, as_of_date=date(2025, 1, 1))
        snap_b = FutureSkillSnapshot.objects.get(job_role=job_b, skill=skill, as_of_date=date(2025, 1, 1))
        self.assertNotEqual(snap_a.trend_score, snap_b.trend_score)
        self.assertAlmostEqual(snap_a.trend_score, 0.2, places=3)
        self.assertAlmostEqual(snap_b.trend_score, 0.7, places=3)

"""Seed extended realistic data for the Future Skills module using the catalog loader."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Management command to seed extended realistic data via the catalog loader."""

    help = "Seeds extended realistic data for Future Skills module using the catalog loader."

    def add_arguments(self, parser):
        parser.add_argument(
            "--catalog-dir",
            type=str,
            default=None,
            help="Catalog directory (defaults to BASE_DIR/data/catalogs).",
        )

    def handle(self, *args, **options):
        """Seed extended data by delegating to load_future_skills_catalog."""
        catalog_dir = options.get("catalog_dir")
        self.stdout.write(self.style.WARNING("🌱 Seeding extended data from catalog..."))
        try:
            if catalog_dir:
                call_command("load_future_skills_catalog", catalog_dir=catalog_dir)
            else:
                call_command("load_future_skills_catalog")
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Erreur lors du chargement du catalogue : {exc}"))
            return

        self.stdout.write(self.style.SUCCESS("✨ Extended data seeding completed via catalog loader."))

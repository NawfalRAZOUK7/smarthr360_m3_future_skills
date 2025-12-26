"""Management command to seed future skills demo data."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Django management command to load future skills demo data."""

    help = "Insère des données de démonstration pour le module Future Skills."

    def handle(self, *args, **options):
        """Execute the command to load demo data."""
        self.stdout.write(self.style.WARNING("Chargement de la fixture 'future_skills_demo'..."))

        try:
            call_command("loaddata", "future_skills_demo")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Erreur lors du chargement de la fixture : {e}"))
            return

        self.stdout.write(self.style.SUCCESS("Données de démonstration Future Skills chargées avec succès."))

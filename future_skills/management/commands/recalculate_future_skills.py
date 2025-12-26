"""Recalculate FutureSkillPrediction entries from the CLI."""

from django.core.management.base import BaseCommand

from future_skills.services.prediction_engine import recalculate_predictions


class Command(BaseCommand):
    """Trigger a batch recalculation of predictions."""

    help = "Recalcule toutes les prédictions FutureSkillPrediction à partir du moteur de règles simple."

    def add_arguments(self, parser):
        """Add CLI arguments for the recalculation command."""
        parser.add_argument(
            "--horizon",
            type=int,
            default=5,
            help="Horizon de prédiction en années (par défaut: 5).",
        )

    def handle(self, *args, **options):
        """Run the recalculation and print progress to stdout."""
        horizon_years = options["horizon"]

        self.stdout.write(
            self.style.WARNING(
                f"Lancement du recalcul des prédictions à horizon {horizon_years} ans..." f"(via management command)..."
            )
        )

        total = recalculate_predictions(
            horizon_years=horizon_years,
            run_by=None,  # CLI → pas d'utilisateur
            parameters={
                "trigger": "management_command",
                # "horizon_years": horizon_years,
                # "engine": "rules_v1",
            },
        )

        self.stdout.write(self.style.SUCCESS(f"Recalcul terminé. {total} prédiction(s) créée(s)/mise(s) à jour."))

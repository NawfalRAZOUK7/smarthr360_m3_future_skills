# future_skills/management/commands/recalculate_future_skills.py

from django.core.management.base import BaseCommand

from future_skills.services.prediction_engine import recalculate_predictions


class Command(BaseCommand):
    help = "Recalcule toutes les prédictions FutureSkillPrediction à partir du moteur de règles simple."

    def add_arguments(self, parser):
        parser.add_argument(
            "--horizon",
            type=int,
            default=5,
            help="Horizon de prédiction en années (par défaut: 5).",
        )

    def handle(self, *args, **options):
        horizon_years = options["horizon"]

        self.stdout.write(
            self.style.WARNING(
                f"Lancement du recalcul des prédictions à horizon {horizon_years} ans..."
            )
        )

        total = recalculate_predictions(horizon_years=horizon_years)

        self.stdout.write(
            self.style.SUCCESS(
                f"Recalcul terminé. {total} prédiction(s) créée(s)/mise(s) à jour."
            )
        )

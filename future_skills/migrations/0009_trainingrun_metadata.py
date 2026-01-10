"""Add evaluation_metrics and dataset_metadata to TrainingRun."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Add metadata fields to TrainingRun."""

    dependencies = [
        ("future_skills", "0008_trainingrun_error_message_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="trainingrun",
            name="evaluation_metrics",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Additional evaluation metrics (kappa, brier, confusion matrix, etc.).",
            ),
        ),
        migrations.AddField(
            model_name="trainingrun",
            name="dataset_metadata",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Dataset metadata (label provenance, as_of_date range, time split usage).",
            ),
        ),
    ]

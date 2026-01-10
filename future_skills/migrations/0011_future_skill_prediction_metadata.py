"""Add metadata fields to FutureSkillPrediction."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Add output contract metadata fields to FutureSkillPrediction."""

    dependencies = [
        ("future_skills", "0010_alter_jobrole_options_alter_skill_options_and_more"),
        ("future_skills", "0009_trainingrun_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="futureskillprediction",
            name="horizon_months",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text="Horizon de prédiction en mois (ex : 12, 36, 60...).",
            ),
        ),
        migrations.AddField(
            model_name="futureskillprediction",
            name="probabilities",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Probabilités par classe (p_low, p_medium, p_high) si disponibles.",
            ),
        ),
        migrations.AddField(
            model_name="futureskillprediction",
            name="confidence",
            field=models.FloatField(
                blank=True,
                null=True,
                help_text="Confiance associée à la prédiction (0-1).",
            ),
        ),
        migrations.AddField(
            model_name="futureskillprediction",
            name="top_drivers",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Principaux facteurs qui expliquent la prédiction.",
            ),
        ),
        migrations.AddField(
            model_name="futureskillprediction",
            name="recommended_actions",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Actions recommandées (hire/train/upskill) avec justification.",
            ),
        ),
        migrations.AddField(
            model_name="futureskillprediction",
            name="label_provenance_used",
            field=models.CharField(
                blank=True,
                max_length=10,
                null=True,
                help_text="Provenance des labels utilisés pour entraîner le modèle (BRONZE/SILVER/GOLD).",
            ),
        ),
        migrations.AddField(
            model_name="futureskillprediction",
            name="model_version",
            field=models.CharField(
                blank=True,
                max_length=50,
                null=True,
                help_text="Version du modèle utilisé pour générer la prédiction.",
            ),
        ),
        migrations.AddField(
            model_name="futureskillprediction",
            name="data_window",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Fenêtre de données utilisée (ex: dates de formation du modèle).",
            ),
        ),
        migrations.AddField(
            model_name="futureskillprediction",
            name="decision_policy",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Politique de décision (seuils, règles d'abstention, fallback).",
            ),
        ),
        migrations.AddField(
            model_name="futureskillprediction",
            name="audit_payload",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Trace d'audit (inputs, outputs, versioning).",
            ),
        ),
        migrations.AddField(
            model_name="futureskillprediction",
            name="as_of_date",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="Date d'observation de la prédiction (snapshot).",
            ),
        ),
    ]

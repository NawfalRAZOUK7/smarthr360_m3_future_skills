from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("future_skills", "0012_alter_trainingrun_options_futureskillsnapshot"),
    ]

    operations = [
        migrations.CreateModel(
            name="FutureSkillLabel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("as_of_date", models.DateField(help_text="Label date for the observed context.")),
                ("horizon_months", models.PositiveIntegerField(help_text="Prediction horizon in months (ex: 12, 36, 60).")),
                (
                    "level",
                    models.CharField(
                        choices=[("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High")],
                        help_text="Validated label: LOW / MEDIUM / HIGH.",
                        max_length=10,
                    ),
                ),
                (
                    "provenance",
                    models.CharField(
                        choices=[("GOLD", "Gold")],
                        default="GOLD",
                        help_text="Label provenance (GOLD).",
                        max_length=10,
                    ),
                ),
                ("source", models.CharField(default="human_review", help_text="Label source (manual review).", max_length=50)),
                ("notes", models.TextField(blank=True, help_text="Optional validation notes.", null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "job_role",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="future_skill_labels", to="future_skills.jobrole"),
                ),
                (
                    "skill",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="future_skill_labels", to="future_skills.skill"),
                ),
                (
                    "validated_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="Human validator (RH/manager).",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="future_skill_labels_validated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Future skill label",
                "verbose_name_plural": "Future skill labels",
                "unique_together": {("job_role", "skill", "as_of_date", "horizon_months")},
                "indexes": [
                    models.Index(fields=["as_of_date"], name="future_skil_as_of_d_11c2d0_idx"),
                    models.Index(fields=["job_role"], name="future_skil_job_rol_9d37d6_idx"),
                    models.Index(fields=["skill"], name="future_skil_skill_id_4f5e10_idx"),
                    models.Index(fields=["horizon_months"], name="future_skil_horizon_394f30_idx"),
                    models.Index(fields=["job_role", "skill", "as_of_date"], name="future_skil_job_rol_3d1ef7_idx"),
                ],
            },
        ),
    ]

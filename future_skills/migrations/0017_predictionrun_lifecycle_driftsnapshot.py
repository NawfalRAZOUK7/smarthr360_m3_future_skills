from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("future_skills", "0016_skill_platform_code")]
    operations = [
        migrations.AlterField(model_name="predictionrun", name="total_predictions", field=models.IntegerField(default=0)),
        migrations.AddField(model_name="predictionrun", name="status", field=models.CharField(choices=[("QUEUED", "Queued"), ("RUNNING", "Running"), ("DONE", "Done"), ("FAILED", "Failed")], default="DONE", max_length=20)),
        migrations.AddField(model_name="predictionrun", name="started_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="predictionrun", name="completed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="predictionrun", name="error_message", field=models.TextField(blank=True, null=True)),
        migrations.CreateModel(
            name="DriftSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("mean_score", models.FloatField()),
                ("previous_mean_score", models.FloatField(blank=True, null=True)),
                ("delta", models.FloatField(default=0.0)),
                ("status", models.CharField(choices=[("STABLE", "Stable"), ("WARNING", "Warning"), ("DRIFTED", "Drifted")], default="STABLE", max_length=20)),
                ("sample_size", models.PositiveIntegerField(default=0)),
                ("distribution", models.JSONField(blank=True, default=dict)),
                ("prediction_run", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="drift_snapshot", to="future_skills.predictionrun")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]

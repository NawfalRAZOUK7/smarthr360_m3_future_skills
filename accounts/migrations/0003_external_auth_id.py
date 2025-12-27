from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_create_default_groups"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="external_auth_id",
            field=models.CharField(
                blank=True,
                help_text="External auth user identifier (source of truth).",
                max_length=64,
                null=True,
                unique=True,
            ),
        ),
    ]

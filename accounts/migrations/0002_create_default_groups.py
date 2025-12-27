from django.db import migrations


def create_default_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    group_names = [
        "HR",
        "HR_ADMIN",
        "MANAGER",
        "MANAGER_ADMIN",
        "EMPLOYEE",
        "EMPLOYEE_ADMIN",
        "AUDITOR",
        "SECURITY_ADMIN",
        "SUPPORT",
        "DRH",
        "RESPONSABLE_RH",
    ]

    for name in group_names:
        Group.objects.get_or_create(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_groups, migrations.RunPython.noop),
    ]

"""Map future-skills Skill rows to canonical platform codes (ADR-007).

Usage:
    python manage.py map_platform_codes mapping.csv     # code,name rows
    python manage.py map_platform_codes --defaults      # common demo set

Matching is case-insensitive on the skill name; unknown names are
reported, existing mappings are updated idempotently.
"""

import csv

from django.core.management.base import BaseCommand, CommandError

from future_skills.models import Skill

DEFAULT_MAPPING = [
    ("PY", "Python"),
    ("DJ", "Django"),
    ("K8S", "Kubernetes"),
    ("SQL", "SQL"),
    ("COMM", "Communication"),
    ("ML", "Machine Learning"),
    ("PM", "Project Management"),
]


class Command(BaseCommand):
    help = "Assign canonical platform skill codes to future-skills skills."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", nargs="?")
        parser.add_argument("--defaults", action="store_true")

    def handle(self, *args, **options):
        if options["defaults"]:
            pairs = DEFAULT_MAPPING
        elif options["csv_path"]:
            with open(options["csv_path"], newline="",
                      encoding="utf-8-sig") as fh:
                pairs = [
                    (row["code"].strip(), row["name"].strip())
                    for row in csv.DictReader(fh)
                ]
        else:
            raise CommandError("Provide a CSV path or --defaults.")

        mapped = missing = 0
        for code, name in pairs:
            updated = Skill.objects.filter(name__iexact=name).update(
                platform_code=code
            )
            if updated:
                mapped += updated
            else:
                missing += 1
                self.stderr.write(f"no skill named '{name}'")
        self.stdout.write(
            self.style.SUCCESS(f"mapped={mapped} missing={missing}")
        )

from django.core.management import call_command
from django.test import TestCase

from future_skills.models import EconomicReport, Employee, FutureSkillPrediction


class SeedDemoTests(TestCase):
    def test_seed_demo_is_idempotent(self):
        call_command("seed_demo")
        first = (Employee.objects.count(), FutureSkillPrediction.objects.count(), EconomicReport.objects.count())
        call_command("seed_demo")
        self.assertEqual((Employee.objects.count(), FutureSkillPrediction.objects.count(), EconomicReport.objects.count()), first)

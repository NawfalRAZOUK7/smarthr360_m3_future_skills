from django.core.management.base import BaseCommand
from django.db import transaction

from future_skills.models import EconomicReport, Employee, FutureSkillPrediction, JobRole, Skill


class Command(BaseCommand):
    help = "Seed deterministic future-skill predictions and economic context."

    @transaction.atomic
    def handle(self, *args, **options):
        skills = {}
        for code, name, category in (("PY", "Python", "Technical"), ("DJ", "Django", "Technical"), ("K8S", "Kubernetes", "Technical"), ("SQL", "SQL", "Technical"), ("PA", "People Analytics", "Business")):
            skills[code], _ = Skill.objects.update_or_create(name=name, defaults={"platform_code": code, "category": category, "description": "Canonical coherent demo skill."})
        roles = {}
        for name, dept in (("Software Engineer", "ENG"), ("Data Scientist", "DATA"), ("Platform Engineer", "ENG"), ("HR Business Partner", "HR")):
            roles[name], _ = JobRole.objects.update_or_create(name=name, defaults={"department": dept, "description": "Strategic demo role."})
        for role_name, code, score, level in (("Software Engineer", "K8S", 84, "HIGH"), ("Software Engineer", "DJ", 67, "MEDIUM"), ("Data Scientist", "PY", 91, "HIGH"), ("Data Scientist", "SQL", 78, "HIGH"), ("HR Business Partner", "PA", 73, "HIGH")):
            FutureSkillPrediction.objects.update_or_create(job_role=roles[role_name], skill=skills[code], horizon_years=3, defaults={"horizon_months": 36, "score": score, "level": level, "rationale": "Demand, scarcity, and internal capability signals.", "confidence": 0.86, "top_drivers": ["Market demand", "Internal skill gap"], "recommended_actions": [{"action": "TRAINING", "reason": "Close forecast capability gap"}], "model_version": "demo-rf-1"})
        for title, indicator, value, sector in (("Digital jobs outlook", "Tech employment growth", 8.4, "Tech"), ("AI investment index", "AI investment growth", 18.7, "Data"), ("Talent scarcity pulse", "Hard-to-fill roles", 64.0, "Tech")):
            EconomicReport.objects.update_or_create(title=title, year=2026, indicator=indicator, defaults={"source_name": "SmartHR360 Demo Observatory", "value": value, "sector": sector})
        for name, email, department, position, role_name, codes in (
            ("Youssef Employee", "employee@demo.smarthr360.dev", "ENG", "Software Engineer", "Software Engineer", ("PY", "DJ")),
            ("Yasmine Alaoui", "yasmine.alaoui@demo.smarthr360.dev", "DATA", "Data Scientist", "Data Scientist", ("PY", "SQL")),
            ("Karim Bennis", "karim.bennis@demo.smarthr360.dev", "ENG", "Platform Engineer", "Platform Engineer", ("PY", "K8S")),
        ):
            employee, _ = Employee.objects.update_or_create(email=email, defaults={"name": name, "department": department, "position": position, "job_role": roles[role_name], "current_skills": [skills[c].name for c in codes]})
            employee.skills.set([skills[c] for c in codes])
        self.stdout.write(self.style.SUCCESS("Future-skills demo data ready."))

"""
Management command to seed extended realistic data for Future Skills module.
Creates a comprehensive set of job roles, skills, market trends, and economic reports.
"""

from django.core.management.base import BaseCommand
from future_skills.models import JobRole, Skill, MarketTrend, EconomicReport


class Command(BaseCommand):
    help = "Seeds extended realistic data for Future Skills module"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("🌱 Seeding extended data..."))

        # Create Skills
        skills_data = [
            # Technical Skills
            {
                "name": "Python",
                "category": "Technique",
                "description": "Langage de programmation polyvalent",
            },
            {
                "name": "Java",
                "category": "Technique",
                "description": "Langage orienté objet pour applications d'entreprise",
            },
            {
                "name": "JavaScript",
                "category": "Technique",
                "description": "Langage web front-end et back-end",
            },
            {
                "name": "SQL",
                "category": "Technique",
                "description": "Langage de requête pour bases de données",
            },
            {
                "name": "Machine Learning",
                "category": "Technique",
                "description": "Intelligence artificielle et apprentissage automatique",
            },
            {
                "name": "Cloud Computing (AWS/Azure)",
                "category": "Technique",
                "description": "Infrastructure cloud et services",
            },
            {
                "name": "DevOps",
                "category": "Technique",
                "description": "Pratiques de développement et opérations",
            },
            {
                "name": "Cybersécurité",
                "category": "Technique",
                "description": "Sécurité des systèmes d'information",
            },
            {
                "name": "Data Analysis",
                "category": "Technique",
                "description": "Analyse et visualisation de données",
            },
            {
                "name": "Docker & Kubernetes",
                "category": "Technique",
                "description": "Conteneurisation et orchestration",
            },
            # Soft Skills
            {
                "name": "Leadership",
                "category": "Soft Skill",
                "description": "Capacité à diriger et motiver des équipes",
            },
            {
                "name": "Communication",
                "category": "Soft Skill",
                "description": "Communication efficace et collaboration",
            },
            {
                "name": "Gestion de projet",
                "category": "Soft Skill",
                "description": "Planification et exécution de projets",
            },
            {
                "name": "Résolution de problèmes",
                "category": "Soft Skill",
                "description": "Pensée critique et résolution de problèmes complexes",
            },
            {
                "name": "Adaptabilité",
                "category": "Soft Skill",
                "description": "Flexibilité et adaptation au changement",
            },
            {
                "name": "Travail d'équipe",
                "category": "Soft Skill",
                "description": "Collaboration et esprit d'équipe",
            },
            {
                "name": "Gestion du temps",
                "category": "Soft Skill",
                "description": "Organisation et priorisation",
            },
            # Business Skills
            {
                "name": "Analyse financière",
                "category": "Business",
                "description": "Analyse et reporting financier",
            },
            {
                "name": "Marketing digital",
                "category": "Business",
                "description": "Stratégies marketing en ligne",
            },
            {
                "name": "Gestion RH",
                "category": "Business",
                "description": "Ressources humaines et talent management",
            },
        ]

        skills_created = 0
        for skill_data in skills_data:
            skill, created = Skill.objects.get_or_create(
                name=skill_data["name"],
                defaults={
                    "category": skill_data["category"],
                    "description": skill_data["description"],
                },
            )
            if created:
                skills_created += 1

        self.stdout.write(
            f"  ✅ Skills: {skills_created} created, {len(skills_data) - skills_created} already existed"
        )

        # Create Job Roles
        job_roles_data = [
            # IT & Tech
            {
                "name": "Data Engineer",
                "department": "IT",
                "description": "Conception et maintenance des pipelines de données",
            },
            {
                "name": "Data Scientist",
                "department": "Data",
                "description": "Analyse prédictive et machine learning",
            },
            {
                "name": "Software Engineer",
                "department": "Tech",
                "description": "Développement d'applications logicielles",
            },
            {
                "name": "DevOps Engineer",
                "department": "IT",
                "description": "Automatisation et infrastructure",
            },
            {
                "name": "Cybersecurity Analyst",
                "department": "IT",
                "description": "Protection des systèmes informatiques",
            },
            {
                "name": "Cloud Architect",
                "department": "IT",
                "description": "Conception d'architectures cloud",
            },
            {
                "name": "Full Stack Developer",
                "department": "Tech",
                "description": "Développement front-end et back-end",
            },
            {
                "name": "Machine Learning Engineer",
                "department": "Data",
                "description": "Implémentation de modèles ML",
            },
            # Management
            {
                "name": "Product Manager",
                "department": "Tech",
                "description": "Gestion de produits technologiques",
            },
            {
                "name": "IT Manager",
                "department": "IT",
                "description": "Management d'équipes IT",
            },
            {
                "name": "Scrum Master",
                "department": "Tech",
                "description": "Facilitation agile et gestion de projet",
            },
            # HR & Business
            {
                "name": "HR Manager",
                "department": "RH",
                "description": "Gestion des ressources humaines",
            },
            {
                "name": "Talent Acquisition Specialist",
                "department": "RH",
                "description": "Recrutement et acquisition de talents",
            },
            {
                "name": "Business Analyst",
                "department": "Finance",
                "description": "Analyse business et optimisation",
            },
            {
                "name": "Marketing Manager",
                "department": "Marketing",
                "description": "Stratégie et gestion marketing",
            },
            {
                "name": "Financial Analyst",
                "department": "Finance",
                "description": "Analyse et planification financière",
            },
        ]

        roles_created = 0
        for role_data in job_roles_data:
            role, created = JobRole.objects.get_or_create(
                name=role_data["name"],
                defaults={
                    "department": role_data["department"],
                    "description": role_data["description"],
                },
            )
            if created:
                roles_created += 1

        self.stdout.write(
            f"  ✅ Job Roles: {roles_created} created, {len(job_roles_data) - roles_created} already existed"
        )

        # Create Market Trends
        trends_data = [
            {
                "title": "AI and Machine Learning Adoption",
                "source_name": "Gartner Tech Trends 2025",
                "year": 2025,
                "sector": "Tech",
                "trend_score": 0.95,
                "description": "Adoption massive de l'IA dans toutes les industries",
            },
            {
                "title": "Cloud-First Strategies",
                "source_name": "IDC Cloud Report",
                "year": 2025,
                "sector": "IT",
                "trend_score": 0.90,
                "description": "Migration vers le cloud pour la majorité des entreprises",
            },
            {
                "title": "Cybersecurity Skills Gap",
                "source_name": "(ISC)² Workforce Study",
                "year": 2025,
                "sector": "IT",
                "trend_score": 0.88,
                "description": "Pénurie critique de compétences en cybersécurité",
            },
            {
                "title": "Data-Driven Decision Making",
                "source_name": "McKinsey Analytics Report",
                "year": 2025,
                "sector": "Data",
                "trend_score": 0.85,
                "description": "Importance croissante de l'analyse de données",
            },
            {
                "title": "Remote Work and Digital Collaboration",
                "source_name": "World Economic Forum",
                "year": 2025,
                "sector": "RH",
                "trend_score": 0.80,
                "description": "Travail hybride et outils de collaboration",
            },
            {
                "title": "Automation and Process Optimization",
                "source_name": "Deloitte Digital Transformation",
                "year": 2025,
                "sector": "Tech",
                "trend_score": 0.82,
                "description": "Automatisation des processus métier",
            },
            {
                "title": "Green IT and Sustainability",
                "source_name": "UN Sustainable Development Goals",
                "year": 2025,
                "sector": "IT",
                "trend_score": 0.70,
                "description": "Informatique durable et écoresponsable",
            },
            {
                "title": "Soft Skills Renaissance",
                "source_name": "LinkedIn Learning Report 2025",
                "year": 2025,
                "sector": "RH",
                "trend_score": 0.78,
                "description": "Importance accrue des compétences relationnelles",
            },
        ]

        trends_created = 0
        for trend_data in trends_data:
            trend, created = MarketTrend.objects.get_or_create(
                title=trend_data["title"],
                year=trend_data["year"],
                defaults={
                    "source_name": trend_data["source_name"],
                    "sector": trend_data["sector"],
                    "trend_score": trend_data["trend_score"],
                    "description": trend_data["description"],
                },
            )
            if created:
                trends_created += 1

        self.stdout.write(
            f"  ✅ Market Trends: {trends_created} created, {len(trends_data) - trends_created} already existed"
        )

        # Create Economic Reports
        reports_data = [
            {
                "title": "IT Sector Growth",
                "source_name": "World Bank",
                "year": 2025,
                "indicator": "Croissance emploi IT",
                "value": 12.5,
                "sector": "IT",
            },
            {
                "title": "Data Science Investment",
                "source_name": "IMF Tech Report",
                "year": 2025,
                "indicator": "Investissement IA/Data",
                "value": 85.0,
                "sector": "Data",
            },
            {
                "title": "Tech Talent Shortage",
                "source_name": "OECD Employment Report",
                "year": 2025,
                "indicator": "Pénurie talents tech",
                "value": 67.0,
                "sector": "Tech",
            },
            {
                "title": "HR Digital Transformation",
                "source_name": "HCP Maroc",
                "year": 2025,
                "indicator": "Digitalisation RH",
                "value": 55.0,
                "sector": "RH",
            },
            {
                "title": "Cloud Market Growth",
                "source_name": "Gartner",
                "year": 2025,
                "indicator": "Croissance marché cloud",
                "value": 22.0,
                "sector": "IT",
            },
        ]

        reports_created = 0
        for report_data in reports_data:
            report, created = EconomicReport.objects.get_or_create(
                title=report_data["title"],
                year=report_data["year"],
                indicator=report_data["indicator"],
                defaults={
                    "source_name": report_data["source_name"],
                    "value": report_data["value"],
                    "sector": report_data.get("sector"),
                },
            )
            if created:
                reports_created += 1

        self.stdout.write(
            f"  ✅ Economic Reports: {reports_created} created, {len(reports_data) - reports_created} already existed"
        )

        # Summary
        total_jobs = JobRole.objects.count()
        total_skills = Skill.objects.count()
        total_trends = MarketTrend.objects.count()
        total_reports = EconomicReport.objects.count()

        expected_rows = total_jobs * total_skills

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✨ Extended data seeding completed!"))
        self.stdout.write(f"  📊 Job Roles: {total_jobs}")
        self.stdout.write(f"  📊 Skills: {total_skills}")
        self.stdout.write(f"  📊 Market Trends: {total_trends}")
        self.stdout.write(f"  📊 Economic Reports: {total_reports}")
        self.stdout.write(f"  📊 Expected dataset size: {expected_rows} rows")
        self.stdout.write("=" * 60)
        self.stdout.write(
            "\n💡 Next step: python manage.py export_future_skills_dataset"
        )

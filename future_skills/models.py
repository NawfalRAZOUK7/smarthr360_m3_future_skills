from django.db import models
from django.conf import settings


class Skill(models.Model):
    """
    Représente une compétence (technique, soft skill, métier, etc.)
    Exemple : Python, Gestion de projet, IA générative...
    """
    name = models.CharField(max_length=150, unique=True)
    category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Catégorie de la compétence (ex : Technique, Soft Skill, Langue...)"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description optionnelle de la compétence."
    )

    def __str__(self):
        return self.name


class JobRole(models.Model):
    """
    Représente un poste / métier dans l’entreprise.
    Exemple : Data Engineer, Responsable RH, Développeur Fullstack...
    """
    name = models.CharField(max_length=150, unique=True)
    department = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Département ou direction (ex : IT, RH, Finance...)."
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description optionnelle du rôle."
    )

    def __str__(self):
        return self.name


class MarketTrend(models.Model):
    """
    Tendance marché / technologique utilisée comme input
    pour la prédiction des compétences futures.
    """
    title = models.CharField(max_length=200)
    source_name = models.CharField(
        max_length=200,
        help_text="Source de la tendance (ex : LinkedIn Report 2025, World Economic Forum...)."
    )
    year = models.IntegerField()
    sector = models.CharField(
        max_length=150,
        help_text="Secteur / domaine concerné (ex : Tech, RH, Industrie...)."
    )
    trend_score = models.FloatField(
        help_text="Score de tendance entre 0 et 1 (0 = faible, 1 = très forte tendance)."
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description ou résumé de la tendance."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tendance marché"
        verbose_name_plural = "Tendances marché"
        ordering = ["-year", "-trend_score"]

    def __str__(self):
        return f"{self.title} ({self.year})"


class FutureSkillPrediction(models.Model):
    """
    Prédiction de besoin futur d’une compétence pour un métier donné
    à horizon N années.
    """

    LEVEL_LOW = "LOW"
    LEVEL_MEDIUM = "MEDIUM"
    LEVEL_HIGH = "HIGH"

    LEVEL_CHOICES = [
        (LEVEL_LOW, "Low"),
        (LEVEL_MEDIUM, "Medium"),
        (LEVEL_HIGH, "High"),
    ]

    job_role = models.ForeignKey(
        JobRole,
        on_delete=models.CASCADE,
        related_name="future_skill_predictions",
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="future_skill_predictions",
    )
    horizon_years = models.PositiveIntegerField(
        help_text="Horizon de prédiction en années (ex : 3, 5...)."
    )

    # Tu peux choisir : 0–100 ou 0–1. Ici on part sur 0–100 pour être plus lisible.
    score = models.FloatField(
        help_text="Score de besoin futur (0–100)."
    )

    level = models.CharField(
        max_length=10,
        choices=LEVEL_CHOICES,
        help_text="Niveau de criticité : LOW / MEDIUM / HIGH."
    )

    rationale = models.TextField(
        blank=True,
        null=True,
        help_text="Explication textuelle de la prédiction (pour le DRH)."
    )
    
    explanation = models.JSONField(
        blank=True,
        null=True,
        help_text="Explication détaillée générée par SHAP/LIME (text, top_factors, confidence)."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Prédiction de compétence future"
        verbose_name_plural = "Prédictions de compétences futures"
        # Un couple (job_role, skill, horizon) est logique unique :
        unique_together = ("job_role", "skill", "horizon_years")

    def __str__(self):
        return f"{self.job_role} - {self.skill} ({self.horizon_years} ans) [{self.level}]"


class PredictionRun(models.Model):
    """
    Trace une exécution du moteur de prédiction
    (utile pour l’audit et la transparence).
    """
    run_date = models.DateTimeField(auto_now_add=True)
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Contexte du recalcul (ex : 'Mise à jour tendances 2025')."
    )
    total_predictions = models.IntegerField()

    # 🔐 Nouveaux champs de traçabilité
    run_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="future_skills_runs",
        help_text="Utilisateur ayant déclenché le recalcul (null si CLI).",
    )
    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Paramètres utilisés pour ce recalcul (horizon, moteur, trigger, etc.).",
    )

    class Meta:
        verbose_name = "Exécution de prédiction"
        verbose_name_plural = "Exécutions de prédiction"
        ordering = ["-run_date"]

    def __str__(self):
        return f"Run du {self.run_date} - {self.total_predictions} prédictions"

class EconomicReport(models.Model):
    """
    Représente un rapport ou indicateur économique utilisé comme input
    pour la prédiction des compétences futures.
    Exemples :
      - Taux de chômage dans l'IT
      - Investissements en IA par secteur
      - Croissance de l'emploi dans un domaine donné
    """
    title = models.CharField(max_length=200)
    source_name = models.CharField(
        max_length=200,
        help_text="Source du rapport (ex : Banque Mondiale, FMI, HCP, WEF...)."
    )
    year = models.IntegerField()
    indicator = models.CharField(
        max_length=150,
        help_text="Nom de l’indicateur (ex : 'Taux chômage IT', 'Investissement IA')."
    )
    value = models.FloatField(
        help_text="Valeur de l’indicateur (pourcentage, indice, budget…)."
    )
    sector = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Secteur concerné (ex : Tech, Industrie, RH...)."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rapport économique"
        verbose_name_plural = "Rapports économiques"
        ordering = ["-year", "title"]

    def __str__(self):
        return f"{self.title} ({self.year}) - {self.indicator}"

class HRInvestmentRecommendation(models.Model):
    """
    Recommandations d'investissement RH à partir des prédictions
    de compétences futures.

    Exemple :
      - former massivement sur Python pour les Data Engineers
      - lancer une campagne de recrutement sur un profil rare
    """

    PRIORITY_LOW = "LOW"
    PRIORITY_MEDIUM = "MEDIUM"
    PRIORITY_HIGH = "HIGH"

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "Low"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_HIGH, "High"),
    ]

    ACTION_TRAINING = "TRAINING"
    ACTION_HIRING = "HIRING"
    ACTION_RESKILL = "RESKILL"

    ACTION_CHOICES = [
        (ACTION_TRAINING, "Investir en formation"),
        (ACTION_HIRING, "Recruter de nouveaux talents"),
        (ACTION_RESKILL, "Reskilling interne"),
    ]

    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="hr_recommendations",
    )
    job_role = models.ForeignKey(
        JobRole,
        on_delete=models.CASCADE,
        related_name="hr_recommendations",
        blank=True,
        null=True,
        help_text="Rôle cible de la recommandation (optionnel si globale à la compétence).",
    )
    horizon_years = models.PositiveIntegerField(
        help_text="Horizon temporel de la recommandation (en années)."
    )
    priority_level = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        help_text="Priorité de la recommandation (LOW / MEDIUM / HIGH).",
    )
    recommended_action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        help_text="Action RH recommandée (formation, recrutement, reskilling).",
    )
    budget_hint = models.FloatField(
        blank=True,
        null=True,
        help_text="Indice ou estimation de budget (optionnel, en K€ ou KMAD selon contexte).",
    )
    rationale = models.TextField(
        blank=True,
        null=True,
        help_text="Explication textuelle de la recommandation pour le décideur RH.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Recommandation RH"
        verbose_name_plural = "Recommandations RH"
        ordering = ["-created_at"]
        # Une recommandation par couple (job_role, skill, horizon) est logique :
        unique_together = ("job_role", "skill", "horizon_years")

    def __str__(self):
        role = self.job_role.name if self.job_role else "Global"
        return f"{self.skill.name} ({role}, {self.horizon_years} ans) [{self.priority_level}/{self.recommended_action}]"

"""Core models for the Future Skills application."""

from django.conf import settings
from django.db import models


class Industry(models.Model):
    """Industry dimension for market/economic signals and role context."""

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    name_i18n = models.JSONField(default=dict, blank=True, help_text="Multilingual industry names.")
    description_i18n = models.JSONField(default=dict, blank=True, help_text="Multilingual industry descriptions.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta options for Industry model."""

        verbose_name = "Industrie"
        verbose_name_plural = "Industries"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        """Return the string representation of the Industry."""
        return self.name


class Function(models.Model):
    """Functional dimension (e.g., Technology, HR, Finance)."""

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    name_i18n = models.JSONField(default=dict, blank=True, help_text="Multilingual function names.")
    description_i18n = models.JSONField(default=dict, blank=True, help_text="Multilingual function descriptions.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta options for Function model."""

        verbose_name = "Fonction"
        verbose_name_plural = "Fonctions"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        """Return the string representation of the Function."""
        return self.name


class Domain(models.Model):
    """Domain under a function (e.g., Data & AI under Technology)."""

    code = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=150)
    function = models.ForeignKey(Function, on_delete=models.PROTECT, related_name="domains")
    description = models.TextField(blank=True, null=True)
    name_i18n = models.JSONField(default=dict, blank=True, help_text="Multilingual domain names.")
    description_i18n = models.JSONField(default=dict, blank=True, help_text="Multilingual domain descriptions.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta options for Domain model."""

        verbose_name = "Domaine"
        verbose_name_plural = "Domaines"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["function"]),
        ]

    def __str__(self):
        """Return the string representation of the Domain."""
        return self.name


class Skill(models.Model):
    """Représente une compétence (technique, soft skill, métier, etc.).

    Exemple : Python, Gestion de projet, IA générative...
    """

    name = models.CharField(max_length=150, unique=True)
    platform_code = models.SlugField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text=(
            "Canonical SmartHR360 platform skill code (= core-hr Skill.code, "
            "ADR-007). Enables code-based matching across services."
        ),
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Catégorie de la compétence (ex : Technique, Soft Skill, Langue...)",
    )
    description = models.TextField(blank=True, null=True, help_text="Description optionnelle de la compétence.")
    name_i18n = models.JSONField(default=dict, blank=True, help_text="Multilingual skill names.")
    description_i18n = models.JSONField(default=dict, blank=True, help_text="Multilingual skill descriptions.")

    class Meta:
        """Meta options for Skill model."""

        verbose_name = "Compétence"
        verbose_name_plural = "Compétences"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),  # Already unique, helps with lookups
            models.Index(fields=["category"]),  # Category filtering
        ]

    def __str__(self):
        """Return the string representation of the Skill."""
        return self.name


class SkillDomainMap(models.Model):
    """Map skills to domains with optional weighting."""

    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="domain_mappings")
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="skill_mappings")
    weight = models.FloatField(default=1.0, help_text="Mapping weight between 0 and 1.")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta options for SkillDomainMap model."""

        verbose_name = "Mapping compétence/domaine"
        verbose_name_plural = "Mappings compétences/domaines"
        unique_together = ("skill", "domain")
        indexes = [
            models.Index(fields=["skill"]),
            models.Index(fields=["domain"]),
        ]

    def __str__(self):
        """Return a string representation of the mapping."""
        return f"{self.skill} -> {self.domain}"


class JobRole(models.Model):
    """Représente un poste / métier dans l’entreprise.

    Exemple : Data Engineer, Responsable RH, Développeur Fullstack...
    """

    name = models.CharField(max_length=150, unique=True)
    department = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Département ou direction (ex : IT, RH, Finance...).",
    )
    description = models.TextField(blank=True, null=True, help_text="Description optionnelle du rôle.")
    name_i18n = models.JSONField(default=dict, blank=True, help_text="Multilingual role names.")
    description_i18n = models.JSONField(default=dict, blank=True, help_text="Multilingual role descriptions.")
    industry = models.ForeignKey(
        Industry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_roles",
        help_text="Industrie associée au rôle (optionnel).",
    )
    domain = models.ForeignKey(
        Domain,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_roles",
        help_text="Domaine fonctionnel associé au rôle (optionnel).",
    )

    class Meta:
        """Meta options for JobRole model."""

        verbose_name = "Rôle professionnel"
        verbose_name_plural = "Rôles professionnels"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),  # Already unique, helps with lookups
            models.Index(fields=["department"]),  # Department filtering
            models.Index(fields=["industry"]),
            models.Index(fields=["domain"]),
        ]

    def __str__(self):
        """Return the string representation of the JobRole."""
        return self.name


class MarketTrend(models.Model):
    """Tendance marché / technologique utilisée comme input pour la prédiction des compétences futures."""

    title = models.CharField(max_length=200)
    source_name = models.CharField(
        max_length=200,
        help_text="Source de la tendance (ex : LinkedIn Report 2025, World Economic Forum...).",
    )
    year = models.IntegerField()
    sector = models.CharField(
        max_length=150,
        help_text="Secteur / domaine concerné (ex : Tech, RH, Industrie...).",
    )
    trend_score = models.FloatField(help_text="Score de tendance entre 0 et 1 (0 = faible, 1 = très forte tendance).")
    description = models.TextField(blank=True, null=True, help_text="Description ou résumé de la tendance.")
    title_i18n = models.JSONField(default=dict, blank=True, help_text="Multilingual trend titles.")
    description_i18n = models.JSONField(default=dict, blank=True, help_text="Multilingual trend descriptions.")
    industry = models.ForeignKey(
        Industry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="market_trends",
        help_text="Industrie associée à la tendance (optionnel).",
    )
    function = models.ForeignKey(
        Function,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="market_trends",
        help_text="Fonction associée à la tendance (optionnel).",
    )
    domain = models.ForeignKey(
        Domain,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="market_trends",
        help_text="Domaine associé à la tendance (optionnel).",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta options for MarketTrend model."""

        verbose_name = "Tendance marché"
        verbose_name_plural = "Tendances marché"
        ordering = ["-year", "-trend_score"]
        indexes = [
            models.Index(fields=["-year"]),
            models.Index(fields=["sector"]),
            models.Index(fields=["-trend_score"]),
            models.Index(fields=["sector", "-year"]),  # Composite for sector+year queries
            models.Index(fields=["industry"]),
            models.Index(fields=["function"]),
            models.Index(fields=["domain"]),
        ]

    def __str__(self):
        """Return a string representation of the MarketTrend instance."""
        return f"{self.title} ({self.year})"


class FutureSkillSnapshot(models.Model):
    """Snapshot of skill signals at a specific date for silver label derivation."""

    job_role = models.ForeignKey(
        JobRole,
        on_delete=models.CASCADE,
        related_name="skill_snapshots",
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="skill_snapshots",
    )
    as_of_date = models.DateField(help_text="Snapshot date for the captured signals.")

    trend_score = models.FloatField(help_text="Trend score at snapshot time (0-1).")
    internal_usage = models.FloatField(help_text="Estimated internal usage at snapshot time (0-1).")
    training_requests = models.FloatField(help_text="Estimated training requests at snapshot time.")
    scarcity_index = models.FloatField(help_text="Estimated scarcity index at snapshot time (0-1).")
    hiring_difficulty = models.FloatField(help_text="Estimated hiring difficulty at snapshot time (0-1).")
    avg_salary_k = models.FloatField(help_text="Estimated average salary at snapshot time (K/year).")
    economic_indicator = models.FloatField(help_text="Economic indicator at snapshot time (0-1).")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta options for FutureSkillSnapshot."""

        verbose_name = "Skill snapshot"
        verbose_name_plural = "Skill snapshots"
        unique_together = ("job_role", "skill", "as_of_date")
        indexes = [
            models.Index(fields=["as_of_date"]),
            models.Index(fields=["job_role"]),
            models.Index(fields=["skill"]),
            models.Index(fields=["job_role", "skill", "as_of_date"]),
        ]

    def __str__(self):
        """Return a string representation of the snapshot."""
        return f"{self.job_role} - {self.skill} ({self.as_of_date})"


class FutureSkillLabel(models.Model):
    """Human-validated labels for future skill needs (GOLD provenance)."""

    LEVEL_LOW = "LOW"
    LEVEL_MEDIUM = "MEDIUM"
    LEVEL_HIGH = "HIGH"

    LEVEL_CHOICES = [
        (LEVEL_LOW, "Low"),
        (LEVEL_MEDIUM, "Medium"),
        (LEVEL_HIGH, "High"),
    ]

    PROVENANCE_GOLD = "GOLD"
    PROVENANCE_CHOICES = [
        (PROVENANCE_GOLD, "Gold"),
    ]

    job_role = models.ForeignKey(
        JobRole,
        on_delete=models.CASCADE,
        related_name="future_skill_labels",
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="future_skill_labels",
    )
    as_of_date = models.DateField(help_text="Label date for the observed context.")
    horizon_months = models.PositiveIntegerField(help_text="Prediction horizon in months (ex: 12, 36, 60).")
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, help_text="Validated label: LOW / MEDIUM / HIGH.")
    provenance = models.CharField(
        max_length=10,
        choices=PROVENANCE_CHOICES,
        default=PROVENANCE_GOLD,
        help_text="Label provenance (GOLD).",
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="future_skill_labels_validated",
        help_text="Human validator (RH/manager).",
    )
    source = models.CharField(max_length=50, default="human_review", help_text="Label source (manual review).")
    notes = models.TextField(blank=True, null=True, help_text="Optional validation notes.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for FutureSkillLabel."""

        verbose_name = "Future skill label"
        verbose_name_plural = "Future skill labels"
        unique_together = ("job_role", "skill", "as_of_date", "horizon_months")
        indexes = [
            models.Index(fields=["as_of_date"]),
            models.Index(fields=["job_role"]),
            models.Index(fields=["skill"]),
            models.Index(fields=["horizon_months"]),
            models.Index(fields=["job_role", "skill", "as_of_date"]),
        ]

    def __str__(self):
        """Return a string representation of the label."""
        return f"{self.job_role} - {self.skill} ({self.as_of_date}) [{self.level}]"


class FutureSkillPrediction(models.Model):
    """Predict future skill needs for a job role over N years.

    Prédiction de besoin futur d’une compétence pour un métier donné à horizon N années.
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
    horizon_years = models.PositiveIntegerField(help_text="Horizon de prédiction en années (ex : 3, 5...).")
    horizon_months = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Horizon de prédiction en mois (ex : 12, 36, 60...).",
    )

    # Tu peux choisir : 0–100 ou 0–1. Ici on part sur 0–100 pour être plus lisible.
    score = models.FloatField(help_text="Score de besoin futur (0–100).")

    level = models.CharField(
        max_length=10,
        choices=LEVEL_CHOICES,
        help_text="Niveau de criticité : LOW / MEDIUM / HIGH.",
    )

    rationale = models.TextField(
        blank=True,
        null=True,
        help_text="Explication textuelle de la prédiction (pour le DRH).",
    )

    explanation = models.JSONField(
        blank=True,
        null=True,
        help_text="Explication détaillée générée par SHAP/LIME (text, top_factors, confidence).",
    )

    probabilities = models.JSONField(
        default=dict,
        blank=True,
        help_text="Probabilités par classe (p_low, p_medium, p_high) si disponibles.",
    )
    confidence = models.FloatField(
        blank=True,
        null=True,
        help_text="Confiance associée à la prédiction (0-1).",
    )
    top_drivers = models.JSONField(
        default=list,
        blank=True,
        help_text="Principaux facteurs qui expliquent la prédiction.",
    )
    recommended_actions = models.JSONField(
        default=list,
        blank=True,
        help_text="Actions recommandées (hire/train/upskill) avec justification.",
    )
    label_provenance_used = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Provenance des labels utilisés pour entraîner le modèle (BRONZE/SILVER/GOLD).",
    )
    model_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Version du modèle utilisé pour générer la prédiction.",
    )
    data_window = models.JSONField(
        default=dict,
        blank=True,
        help_text="Fenêtre de données utilisée (ex: dates de formation du modèle).",
    )
    decision_policy = models.JSONField(
        default=dict,
        blank=True,
        help_text="Politique de décision (seuils, règles d'abstention, fallback).",
    )
    audit_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Trace d'audit (inputs, outputs, versioning).",
    )

    as_of_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date d'observation de la prédiction (snapshot).",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta options for FutureSkillPrediction model."""

        verbose_name = "Prédiction de compétence future"
        verbose_name_plural = "Prédictions de compétences futures"
        # Un couple (job_role, skill, horizon) est logique unique :
        unique_together = ("job_role", "skill", "horizon_years")
        indexes = [
            models.Index(fields=["job_role"]),
            models.Index(fields=["skill"]),
            models.Index(fields=["horizon_years"]),
            models.Index(fields=["level"]),
            models.Index(fields=["-score"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["job_role", "horizon_years"]),  # Common filter combo
            models.Index(fields=["skill", "level"]),  # Skill filtering by level
            models.Index(fields=["horizon_years", "-score"]),  # Horizon + top scores
        ]

    def __str__(self):
        """Return a string representation of the FutureSkillPrediction instance."""
        return f"{self.job_role} - {self.skill} ({self.horizon_years} ans) [{self.level}]"


class PredictionRun(models.Model):
    """Trace a prediction engine run.

    Trace une exécution du moteur de prédiction (utile pour l’audit et la transparence).
    """

    run_date = models.DateTimeField(auto_now_add=True)
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Contexte du recalcul (ex : 'Mise à jour tendances 2025').",
    )
    total_predictions = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=[("QUEUED", "Queued"), ("RUNNING", "Running"), ("DONE", "Done"), ("FAILED", "Failed")],
        default="DONE",
    )
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

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
        """Meta options for PredictionRun model."""

        verbose_name = "Exécution de prédiction"
        verbose_name_plural = "Exécutions de prédiction"
        ordering = ["-run_date"]
        indexes = [
            models.Index(fields=["-run_date"]),
            models.Index(fields=["run_by"]),  # Filter by user who triggered
        ]

    def __str__(self):
        """Return a string representation of the PredictionRun instance."""
        return f"Run du {self.run_date} - {self.total_predictions} prédictions"


class DriftSnapshot(models.Model):
    """Persisted prediction-score distribution summary for one run."""

    prediction_run = models.OneToOneField(PredictionRun, on_delete=models.CASCADE, related_name="drift_snapshot")
    created_at = models.DateTimeField(auto_now_add=True)
    mean_score = models.FloatField()
    previous_mean_score = models.FloatField(blank=True, null=True)
    delta = models.FloatField(default=0.0)
    status = models.CharField(max_length=20, choices=[("STABLE", "Stable"), ("WARNING", "Warning"), ("DRIFTED", "Drifted")], default="STABLE")
    sample_size = models.PositiveIntegerField(default=0)
    distribution = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]


class TrainingRun(models.Model):
    """Trace an ML model training execution for audit and MLOps tracking.

    Trace une exécution d’entraînement du moteur ML (utile pour l’audit, la reproductibilité, la transparence).
    """

    class Meta:
        """Meta options for TrainingRun model."""

        verbose_name = "Entraînement ML"
        verbose_name_plural = "Entraînements ML"
        ordering = ["-run_date"]
        indexes = [
            models.Index(fields=["-run_date"]),
            models.Index(fields=["model_version"]),
        ]

    run_date = models.DateTimeField(auto_now_add=True)
    model_version = models.CharField(
        max_length=50,
        help_text="Version identifier for the trained model (e.g., 'v1', 'v2.1').",
    )
    model_path = models.CharField(max_length=500, help_text="File system path where the model was saved.")
    dataset_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Path to the training dataset CSV file.",
    )

    # Training parameters
    test_split = models.FloatField(default=0.2, help_text="Test set split ratio (e.g., 0.2 = 20% test).")
    n_estimators = models.IntegerField(default=200, help_text="Number of trees in RandomForest classifier.")
    random_state = models.IntegerField(default=42, help_text="Random seed for reproducibility.")

    # Training metrics
    accuracy = models.FloatField(help_text="Overall accuracy on test set (0.0 to 1.0).")
    precision = models.FloatField(help_text="Weighted average precision on test set.")
    recall = models.FloatField(help_text="Weighted average recall on test set.")
    f1_score = models.FloatField(help_text="Weighted average F1-score on test set.")

    # Dataset information
    total_samples = models.IntegerField(help_text="Total number of samples in the dataset.")
    train_samples = models.IntegerField(help_text="Number of samples in training set.")
    test_samples = models.IntegerField(help_text="Number of samples in test set.")

    # Training duration
    training_duration_seconds = models.FloatField(help_text="Total training duration in seconds.")

    # Per-class metrics (stored as JSON)
    per_class_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-class accuracy and support counts (LOW, MEDIUM, HIGH).",
    )

    # Additional evaluation metrics and dataset metadata
    evaluation_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional evaluation metrics (kappa, brier, confusion matrix, etc.).",
    )
    dataset_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dataset metadata (label provenance, as_of_date range, time split usage).",
    )

    # Feature information
    features_used = models.JSONField(default=list, blank=True, help_text="List of features used for training.")

    # User tracking
    trained_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="training_runs",
        help_text="User who triggered the training (null if CLI).",
    )

    # Additional metadata
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes or comments about this training run.",
    )

    # Training status tracking
    status = models.CharField(
        max_length=20,
        choices=[
            ("RUNNING", "Running"),
            ("COMPLETED", "Completed"),
            ("FAILED", "Failed"),
        ],
        default="COMPLETED",
        help_text="Current status of the training run.",
    )
    error_message = models.TextField(blank=True, null=True, help_text="Error message if training failed.")

    # Consolidated hyperparameters (in addition to individual fields)
    hyperparameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="All hyperparameters used for this training run (consolidated view).",
    )

    def __str__(self):
        """Return a string representation of the TrainingRun instance."""
        return f"Training {self.model_version} - {self.run_date.strftime('%Y-%m-%d %H:%M')} (acc: {self.accuracy:.2%})"


class EconomicReport(models.Model):
    """Economic report for trend and recommendation analysis.

    Représente un rapport ou indicateur économique utilisé comme input pour la prédiction des compétences futures.
    Exemples :
      - Taux de chômage dans l'IT
      - Investissements en IA par secteur
      - Croissance de l'emploi dans un domaine donné
    """

    title = models.CharField(max_length=200)
    source_name = models.CharField(
        max_length=200,
        help_text="Source du rapport (ex : Banque Mondiale, FMI, HCP, WEF...).",
    )
    year = models.IntegerField()
    indicator = models.CharField(
        max_length=150,
        help_text="Nom de l’indicateur (ex : 'Taux chômage IT', 'Investissement IA').",
    )
    value = models.FloatField(help_text="Valeur de l’indicateur (pourcentage, indice, budget…).")
    sector = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Secteur concerné (ex : Tech, Industrie, RH...).",
    )
    title_i18n = models.JSONField(default=dict, blank=True, help_text="Multilingual report titles.")
    indicator_i18n = models.JSONField(default=dict, blank=True, help_text="Multilingual indicator names.")
    industry = models.ForeignKey(
        Industry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="economic_reports",
        help_text="Industrie associée au rapport (optionnel).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta options for EconomicReport model."""

        verbose_name = "Rapport économique"
        verbose_name_plural = "Rapports économiques"
        ordering = ["-year", "title"]
        indexes = [
            models.Index(fields=["-year"]),
            models.Index(fields=["sector"]),
            models.Index(fields=["indicator"]),
            models.Index(fields=["sector", "-year"]),  # Composite for sector+year queries
            models.Index(fields=["industry"]),
        ]

    def __str__(self):
        """Return a string representation of the EconomicReport instance."""
        return f"{self.title} ({self.year}) - {self.indicator}"


class HRInvestmentRecommendation(models.Model):
    """HR investment recommendations based on future skill predictions.

    Recommandations d'investissement RH à partir des prédictions de compétences futures.

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
    horizon_years = models.PositiveIntegerField(help_text="Horizon temporel de la recommandation (en années).")
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
        """Meta options for HRInvestmentRecommendation model."""

        verbose_name = "Recommandation RH"
        verbose_name_plural = "Recommandations RH"
        ordering = ["-created_at"]
        # Une recommandation par couple (job_role, skill, horizon) est logique :
        unique_together = ("job_role", "skill", "horizon_years")
        indexes = [
            models.Index(fields=["skill"]),
            models.Index(fields=["job_role"]),
            models.Index(fields=["horizon_years"]),
            models.Index(fields=["priority_level"]),
            models.Index(fields=["recommended_action"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["skill", "priority_level"]),  # Skill by priority
            models.Index(fields=["job_role", "horizon_years"]),  # Role+horizon combo
            models.Index(fields=["priority_level", "recommended_action"]),  # Action filtering
        ]

    def __str__(self):
        """Return a string representation of the HRInvestmentRecommendation instance."""
        role = self.job_role.name if self.job_role else "Global"
        return f"{self.skill.name} ({role}, {self.horizon_years} ans) [{self.priority_level}/{self.recommended_action}]"


class Employee(models.Model):
    """Employee model for advanced HR analytics.

    Représente un employé dans l'entreprise. Utilisé pour générer des prédictions de compétences personnalisées.
    """

    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=150, help_text="Département de l'employé (ex : IT, RH, Finance...).")
    position = models.CharField(
        max_length=150,
        help_text="Poste actuel de l'employé (ex : Developer, Manager...).",
    )
    job_role = models.ForeignKey(
        JobRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
        help_text="Rôle/métier associé dans le référentiel JobRole.",
    )
    current_skills = models.JSONField(
        default=list,
        blank=True,
        help_text="Liste des compétences actuelles de l'employé (ex : ['Python', 'Django']).",
    )

    # Option B: Use ManyToMany instead of JSONField (advanced, more normalized)
    skills = models.ManyToManyField(
        Skill,
        blank=True,
        related_name="employees",
        help_text="Skills possessed by this employee",
    )

    date_joined = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Employé"
        verbose_name_plural = "Employés"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["email"]),  # Already unique, but index helps lookups
            models.Index(fields=["department"]),
            models.Index(fields=["job_role"]),
            models.Index(fields=["name"]),
            models.Index(fields=["job_role", "department"]),  # Role+dept queries
        ]

    def __str__(self):
        """Return a string representation of the Employee instance."""
        return f"{self.name} ({self.email})"

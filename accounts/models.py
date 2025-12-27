from django.contrib.auth.models import AbstractUser, BaseUserManager, Group
from django.db import models
from django.db.models.functions import Lower
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .grouping import BASE_ROLE_GROUPS, ROLE_TO_BASE_GROUP

def normalize_email_address(email):
    if not email:
        return email
    return email.strip().lower()


class UserManager(BaseUserManager):
    """Custom manager for User using email as identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("username", email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    @classmethod
    def normalize_email(cls, email):
        return normalize_email_address(email)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if "role" not in extra_fields:
            extra_fields["role"] = self.model.Role.ADMIN

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom User model aligned with auth (email-first, role enum)."""

    class Role(models.TextChoices):
        EMPLOYEE = "EMPLOYEE", "Employee"
        MANAGER = "MANAGER", "Manager"
        HR = "HR", "HR"
        ADMIN = "ADMIN", "Admin"

    username = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        null=True,
        help_text="Compatibility username; defaults to normalized email.",
    )

    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
    )

    ROLE_HIERARCHY: dict[str, int] = {
        "EMPLOYEE": 1,
        "MANAGER": 2,
        "HR": 3,
        "ADMIN": 4,
    }

    is_email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["role"], name="accounts_user_role_idx"),
        ]

    @property
    def role_rank(self) -> int:
        """Return numeric rank for comparisons (higher = more privileges)."""
        return self.ROLE_HIERARCHY.get(self.role, 0)

    def has_role(self, *roles) -> bool:
        return self.role in roles

    def is_at_least(self, role: str) -> bool:
        required_rank = self.ROLE_HIERARCHY.get(role, 0)
        return self.role_rank >= required_rank

    def save(self, *args, **kwargs):
        if self.email:
            self.email = normalize_email_address(self.email)
        if self.email and not self.username:
            self.username = self.email
        if self.is_email_verified and not self.email_verified_at:
            self.email_verified_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({self.role})"


def _ensure_group(name: str) -> Group:
    group, _ = Group.objects.get_or_create(name=name)
    return group


def _sync_role_base_group(user: User) -> None:
    if not user.pk:
        return

    if user.role == User.Role.ADMIN:
        if BASE_ROLE_GROUPS:
            user.groups.remove(*Group.objects.filter(name__in=BASE_ROLE_GROUPS))
        return

    base_group_name = ROLE_TO_BASE_GROUP.get(user.role)
    if not base_group_name:
        return

    target_group = _ensure_group(base_group_name)
    user.groups.add(target_group)

    other_base_groups = BASE_ROLE_GROUPS - {base_group_name}
    if other_base_groups:
        user.groups.remove(*Group.objects.filter(name__in=other_base_groups))


@receiver(post_save, sender=User)
def sync_user_role_group(sender, instance, **kwargs):
    _sync_role_base_group(instance)

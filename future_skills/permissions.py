# future_skills/permissions.py

from rest_framework.permissions import BasePermission


# On part sur des groupes Django pour représenter les rôles.
# Tu pourras les créer dans l'admin :
#  - DRH
#  - RESPONSABLE_RH
#  - MANAGER

HR_STAFF_GROUPS = {"DRH", "RESPONSABLE_RH"}
MANAGER_GROUPS = HR_STAFF_GROUPS | {"MANAGER"}


def _user_in_groups(user, group_names) -> bool:
    """
    Vérifie si l'utilisateur appartient à au moins un des groupes donnés.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        # Le superuser a accès à tout
        return True

    return user.groups.filter(name__in=group_names).exists()


class IsHRStaff(BasePermission):
    """
    Autorise uniquement les utilisateurs appartenant aux groupes:
      - DRH
      - RESPONSABLE_RH
    """

    message = "Vous devez être membre du staff RH (DRH ou Responsable RH) pour accéder à cette ressource."

    def has_permission(self, request, view):
        return _user_in_groups(request.user, HR_STAFF_GROUPS)


class IsHRStaffOrManager(BasePermission):
    """
    Autorise les utilisateurs appartenant aux groupes:
      - DRH
      - RESPONSABLE_RH
      - MANAGER
    """

    message = "Vous devez être DRH, Responsable RH ou Manager pour accéder à cette ressource."

    def has_permission(self, request, view):
        return _user_in_groups(request.user, MANAGER_GROUPS)

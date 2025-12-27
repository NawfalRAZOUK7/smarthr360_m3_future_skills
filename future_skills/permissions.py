# future_skills/permissions.py

from rest_framework.permissions import BasePermission

from accounts.access import has_hr_access, has_manager_access


class IsHRStaff(BasePermission):
    """
    Autorise uniquement les utilisateurs RH (role ou groupe).
    """

    message = "Vous devez etre RH pour acceder a cette ressource."

    def has_permission(self, request, view):
        return has_hr_access(request.user)


class IsHRStaffOrManager(BasePermission):
    """
    Autorise les utilisateurs RH ou Manager (role ou groupe).
    """

    message = "Vous devez etre RH ou Manager pour acceder a cette ressource."

    def has_permission(self, request, view):
        return has_manager_access(request.user, include_hr=True)

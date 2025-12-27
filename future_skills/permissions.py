# future_skills/permissions.py

from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.access import (
    has_hr_access,
    has_manager_access,
    is_auditor,
    is_security_admin,
    is_support,
)


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


class IsAuditorReadOnly(BasePermission):
    """
    Autorise les auditors en lecture seule.
    """

    message = "Vous devez etre AUDITOR (lecture seule) pour acceder a cette ressource."

    def has_permission(self, request, view):
        if request.method not in SAFE_METHODS:
            return False
        return is_auditor(request.user)


class IsSecurityAdmin(BasePermission):
    """
    Autorise les security admins (ou admin global).
    """

    message = "Vous devez etre SECURITY_ADMIN pour acceder a cette ressource."

    def has_permission(self, request, view):
        return is_security_admin(request.user)


class IsSupport(BasePermission):
    """
    Autorise le support (ou admin global).
    """

    message = "Vous devez etre SUPPORT pour acceder a cette ressource."

    def has_permission(self, request, view):
        return is_support(request.user)


class IsManagerOrAuditorReadOnly(BasePermission):
    """
    Autorise Manager/HR en ecriture, et Auditor en lecture seule.
    """

    message = "Vous devez etre Manager/HR (ecriture) ou Auditor (lecture) pour acceder a cette ressource."

    def has_permission(self, request, view):
        user = request.user
        if request.method in SAFE_METHODS:
            return has_manager_access(user, include_hr=True) or is_auditor(user)
        return has_manager_access(user, include_hr=True)


class IsManagerOrSupportReadOnly(BasePermission):
    """
    Autorise Manager/HR en ecriture, et Support en lecture seule.
    """

    message = "Vous devez etre Manager/HR (ecriture) ou Support (lecture) pour acceder a cette ressource."

    def has_permission(self, request, view):
        user = request.user
        if request.method in SAFE_METHODS:
            return has_manager_access(user, include_hr=True) or is_support(user)
        return has_manager_access(user, include_hr=True)


class IsManagerOrSupportAuditorReadOnly(BasePermission):
    """
    Autorise Manager/HR en ecriture, et Support/Auditor en lecture seule.
    """

    message = "Vous devez etre Manager/HR (ecriture) ou Support/Auditor (lecture) pour acceder a cette ressource."

    def has_permission(self, request, view):
        user = request.user
        if request.method in SAFE_METHODS:
            return (
                has_manager_access(user, include_hr=True)
                or is_support(user)
                or is_auditor(user)
            )
        return has_manager_access(user, include_hr=True)

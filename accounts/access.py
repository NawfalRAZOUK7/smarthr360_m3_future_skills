from __future__ import annotations

from .grouping import (
    AUDITOR_GROUPS,
    EMPLOYEE_GROUPS,
    HR_GROUPS,
    MANAGER_GROUPS,
    SECURITY_ADMIN_GROUPS,
    SUPPORT_GROUPS,
)


def _is_authenticated(user) -> bool:
    return bool(user and getattr(user, "is_authenticated", False))


def is_admin(user) -> bool:
    return bool(
        _is_authenticated(user)
        and (getattr(user, "is_superuser", False) or getattr(user, "role", None) == "ADMIN")
    )


def in_groups(user, group_names) -> bool:
    if not _is_authenticated(user):
        return False
    return user.groups.filter(name__in=group_names).exists()


def is_hr(user) -> bool:
    if not _is_authenticated(user):
        return False
    return bool(getattr(user, "role", None) == "HR" or in_groups(user, HR_GROUPS))


def is_manager(user) -> bool:
    if not _is_authenticated(user):
        return False
    return bool(getattr(user, "role", None) == "MANAGER" or in_groups(user, MANAGER_GROUPS))


def is_employee(user) -> bool:
    if not _is_authenticated(user):
        return False
    return bool(getattr(user, "role", None) == "EMPLOYEE" or in_groups(user, EMPLOYEE_GROUPS))


def has_hr_access(user) -> bool:
    return bool(is_admin(user) or is_hr(user))


def has_manager_access(user, *, include_hr: bool = True) -> bool:
    if is_admin(user) or is_manager(user):
        return True
    return bool(include_hr and is_hr(user))


def has_employee_access(user) -> bool:
    return bool(is_admin(user) or is_employee(user))


def is_auditor(user) -> bool:
    return bool(is_admin(user) or in_groups(user, AUDITOR_GROUPS))


def is_security_admin(user) -> bool:
    return bool(is_admin(user) or in_groups(user, SECURITY_ADMIN_GROUPS))


def is_support(user) -> bool:
    return bool(is_admin(user) or in_groups(user, SUPPORT_GROUPS))

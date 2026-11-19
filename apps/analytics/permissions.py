"""
Permissions for FlightFix Analytics & Reporting module.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.accounts.models import User


class IsAnalyticsUser(BasePermission):
    """
    Grants read-only analytics access exclusively to management roles:
    - ADMIN
    - SAFETY_OFFICER
    - CONTRACTS_MANAGER
    Rejects FIELD_TECHNICIAN with 403 Forbidden.
    Unauthenticated users are rejected with 401 Unauthorized via IsAuthenticated.
    """
    message = "Field technicians are not authorized to access management analytics."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        # Explicitly forbid FIELD_TECHNICIAN
        if user.role == User.Role.FIELD_TECHNICIAN:
            return False

        return (
            user.role in (
                User.Role.ADMIN,
                User.Role.SAFETY_OFFICER,
                User.Role.CONTRACTS_MANAGER,
            )
            or user.is_superuser
            or user.is_staff
        )

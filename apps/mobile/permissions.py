"""
Permissions for FlightFix Mobile / Field Technician Support module.
"""

from rest_framework.permissions import BasePermission
from apps.accounts.models import User


class IsFieldTechnician(BasePermission):
    """
    Grants access exclusively to authenticated users with the FIELD_TECHNICIAN role.
    Rejects other roles (ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER) with 403 Forbidden.
    Unauthenticated users are rejected with 401 Unauthorized via IsAuthenticated.
    """
    message = "Access restricted to field technicians only."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.role == User.Role.FIELD_TECHNICIAN

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.role == User.Role.FIELD_TECHNICIAN

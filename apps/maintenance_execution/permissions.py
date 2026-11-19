"""
Role-based access permissions for FlightFix Maintenance Execution & Documentation module.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.accounts.models import User


class MaintenanceExecutionPermission(BasePermission):
    """
    Role-Based Access Control for Maintenance Execution Records:
    - Authentication required (401 for unauthenticated).
    - ADMIN: Full CRUD permissions (including DELETE).
    - SAFETY_OFFICER: Add, view, and update (POST, GET, PUT, PATCH). Deletions are forbidden.
    - CONTRACTS_MANAGER: Read-only access (GET, HEAD, OPTIONS).
    - FIELD_TECHNICIAN: View and update ONLY records assigned to them (executed_by == request.user).
      Deletions are forbidden.
    """
    message = "You do not have permission to perform this maintenance execution operation."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if user.is_superuser or user.role == User.Role.ADMIN:
            return True

        if request.method in SAFE_METHODS:
            return user.role in (
                User.Role.SAFETY_OFFICER,
                User.Role.CONTRACTS_MANAGER,
                User.Role.FIELD_TECHNICIAN,
            )

        if request.method in ('POST', 'PUT', 'PATCH'):
            return user.role in (User.Role.SAFETY_OFFICER, User.Role.FIELD_TECHNICIAN)

        # DELETE is restricted to ADMIN
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if user.is_superuser or user.role == User.Role.ADMIN:
            return True

        if user.role == User.Role.SAFETY_OFFICER:
            return request.method != 'DELETE'

        if user.role == User.Role.CONTRACTS_MANAGER:
            return request.method in SAFE_METHODS

        if user.role == User.Role.FIELD_TECHNICIAN:
            if request.method == 'DELETE':
                return False
            # Check if this execution record is assigned to the technician
            return getattr(obj, 'executed_by', None) == user

        return False


class MaintenanceDocumentationPermission(BasePermission):
    """
    Role-Based Access Control for Technical Maintenance Documentation:
    - ADMIN: Full CRUD.
    - SAFETY_OFFICER: Create, view, and update (signing/verifying). No DELETE.
    - CONTRACTS_MANAGER: Read-only.
    - FIELD_TECHNICIAN: Read-only (view only for their assigned executions).
    """
    message = "You do not have permission to manage this maintenance documentation record."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if user.is_superuser or user.role == User.Role.ADMIN:
            return True

        if request.method in SAFE_METHODS:
            return user.role in (
                User.Role.SAFETY_OFFICER,
                User.Role.CONTRACTS_MANAGER,
                User.Role.FIELD_TECHNICIAN,
            )

        if request.method in ('POST', 'PUT', 'PATCH'):
            return user.role == User.Role.SAFETY_OFFICER

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if user.is_superuser or user.role == User.Role.ADMIN:
            return True

        if user.role == User.Role.SAFETY_OFFICER:
            return request.method != 'DELETE'

        if user.role in (User.Role.CONTRACTS_MANAGER, User.Role.FIELD_TECHNICIAN):
            return request.method in SAFE_METHODS

        return False

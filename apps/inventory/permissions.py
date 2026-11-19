"""
Role-based access permissions for FlightFix Spare Parts Inventory module.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.accounts.models import User


class InventoryPermission(BasePermission):
    """
    Role-Based Access Control for Spare Parts and Inventory Transactions:
    - Authentication required for all endpoints (401 if unauthenticated).
    - ADMIN: Full CRUD permissions (including DELETE).
    - SAFETY_OFFICER: Add, view, update (POST, GET, PUT, PATCH). Deletions are forbidden.
    - CONTRACTS_MANAGER: Read-only access (GET, HEAD, OPTIONS).
    - FIELD_TECHNICIAN: Read-only access (GET, HEAD, OPTIONS).
    """
    message = "You do not have permission to perform this inventory operation."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        # Superusers and ADMIN have full access
        if user.is_superuser or user.role == User.Role.ADMIN:
            return True

        # Read-only access for other roles
        if request.method in SAFE_METHODS:
            return user.role in (
                User.Role.SAFETY_OFFICER,
                User.Role.CONTRACTS_MANAGER,
                User.Role.FIELD_TECHNICIAN,
            )

        # SAFETY_OFFICER can create (POST) and update (PUT, PATCH)
        if request.method in ('POST', 'PUT', 'PATCH'):
            return user.role == User.Role.SAFETY_OFFICER

        # All other methods (e.g. DELETE) are forbidden
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

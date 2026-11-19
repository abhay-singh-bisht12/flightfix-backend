"""
Role-based access permissions for FlightFix Work Order Management.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.accounts.models import User
from apps.work_orders.models import WorkOrder


class WorkOrderPermission(BasePermission):
    """
    Role-Based Access Control for Work Orders:
    - Authentication required for all endpoints.
    - ADMIN: Full CRUD (including DELETE).
    - SAFETY_OFFICER: Add, view, update (no DELETE).
    - CONTRACTS_MANAGER: View and track (GET only).
    - FIELD_TECHNICIAN: View assigned work orders (GET only).
    - Unauthenticated: 401 Unauthorized.
    """
    message = "You do not have permission to perform this work order action."

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

        # All other methods (e.g. DELETE) are restricted
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
            if request.method not in SAFE_METHODS:
                return False
            # Technicians can only view work orders assigned to them
            return obj.assigned_to == user

        return False

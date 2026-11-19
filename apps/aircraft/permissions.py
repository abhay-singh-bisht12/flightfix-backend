"""
Role-based access permissions for FlightFix Aircraft and Equipment management.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.accounts.models import User


class AircraftEquipmentPermission(BasePermission):
    """
    Granular Role-Based Access Control for Aircraft and Equipment:
    - Authentication required for all endpoints.
    - Read (GET, HEAD, OPTIONS): ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER, FIELD_TECHNICIAN.
    - Create (POST) & Update (PUT, PATCH): ADMIN, SAFETY_OFFICER.
    - Delete (DELETE): ADMIN only.
    """
    message = "You do not have permission to perform this action on aircraft or equipment records."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        # Superusers and ADMIN have full access (all methods including DELETE)
        if user.is_superuser or user.role == User.Role.ADMIN:
            return True

        # Read-only access for SAFETY_OFFICER, CONTRACTS_MANAGER, FIELD_TECHNICIAN
        if request.method in SAFE_METHODS:
            return user.role in (
                User.Role.SAFETY_OFFICER,
                User.Role.CONTRACTS_MANAGER,
                User.Role.FIELD_TECHNICIAN,
            )

        # SAFETY_OFFICER can create (POST) and update (PUT, PATCH), but CANNOT DELETE
        if request.method in ('POST', 'PUT', 'PATCH'):
            return user.role == User.Role.SAFETY_OFFICER

        # DELETE is restricted strictly to ADMIN
        if request.method == 'DELETE':
            return False

        return False

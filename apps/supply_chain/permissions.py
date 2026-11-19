"""
Role-based access permissions for FlightFix ERP & Supply Chain Integration module.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.accounts.models import User


class SupplyChainPermission(BasePermission):
    """
    Role-Based Access Control for Suppliers, Purchase Orders, and Items:
    - Authentication required (401 for unauthenticated requests).
    - ADMIN: Full CRUD, approve purchase orders, receive items, manage suppliers.
    - SAFETY_OFFICER: Add, view, and update (POST, GET, PUT, PATCH). Deletions are forbidden (403).
    - CONTRACTS_MANAGER: Add, view, and update (POST, GET, PUT, PATCH). Deletions are forbidden (403).
    - FIELD_TECHNICIAN: Read-only access (GET, HEAD, OPTIONS). Modifications and deletions forbidden (403).
    """
    message = "You do not have permission to perform this supply chain operation."

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
            return user.role in (User.Role.SAFETY_OFFICER, User.Role.CONTRACTS_MANAGER)

        # DELETE is restricted to ADMIN
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if user.is_superuser or user.role == User.Role.ADMIN:
            return True

        if user.role in (User.Role.SAFETY_OFFICER, User.Role.CONTRACTS_MANAGER):
            return request.method != 'DELETE'

        if user.role == User.Role.FIELD_TECHNICIAN:
            return request.method in SAFE_METHODS

        return False


class CanReceivePOPermission(BasePermission):
    """
    Permission check specifically for receiving items on purchase orders.
    ADMIN, SAFETY_OFFICER, and CONTRACTS_MANAGER are authorized.
    FIELD_TECHNICIAN and unauthenticated users are forbidden.
    """
    message = "You do not have permission to receive items on purchase orders."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if user.is_superuser or user.role in (
            User.Role.ADMIN,
            User.Role.SAFETY_OFFICER,
            User.Role.CONTRACTS_MANAGER,
        ):
            return True

        return False

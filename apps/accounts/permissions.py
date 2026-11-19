"""
Reusable Role-Based Permission Classes for FlightFix.
"""

from rest_framework.permissions import BasePermission
from apps.accounts.models import User


class BaseRolePermission(BasePermission):
    """
    Base permission class to check if a user is authenticated and belongs to allowed roles.
    Superusers automatically bypass role restrictions.
    """
    allowed_roles = ()

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        return request.user.role in self.allowed_roles


class IsAdmin(BaseRolePermission):
    """
    Allows access only to users with the ADMIN role (or superusers).
    """
    allowed_roles = (User.Role.ADMIN,)


class IsSafetyOfficer(BaseRolePermission):
    """
    Allows access only to users with the SAFETY_OFFICER role.
    """
    allowed_roles = (User.Role.SAFETY_OFFICER,)


class IsContractsManager(BaseRolePermission):
    """
    Allows access only to users with the CONTRACTS_MANAGER role.
    """
    allowed_roles = (User.Role.CONTRACTS_MANAGER,)


class IsFieldTechnician(BaseRolePermission):
    """
    Allows access only to users with the FIELD_TECHNICIAN role.
    """
    allowed_roles = (User.Role.FIELD_TECHNICIAN,)


class IsAdminOrSafetyOfficer(BaseRolePermission):
    """
    Allows access to users with either ADMIN or SAFETY_OFFICER roles.
    """
    allowed_roles = (User.Role.ADMIN, User.Role.SAFETY_OFFICER)

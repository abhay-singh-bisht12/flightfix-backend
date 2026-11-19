"""
Role-based access permissions for FlightFix Airworthiness & Regulatory Compliance module.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.accounts.models import User


class CompliancePermission(BasePermission):
    """
    Role-Based Access Control for Compliance Requirements and Verification Records:
    - Authentication required (401 for unauthenticated).
    - ADMIN: Full CRUD permissions (including DELETE).
    - SAFETY_OFFICER: Add, view, and update (POST, GET, PUT, PATCH). Deletions are forbidden.
    - CONTRACTS_MANAGER: Read-only access (GET, HEAD, OPTIONS).
    - FIELD_TECHNICIAN: Read-only access restricted strictly to records associated with
      aircraft or maintenance executions assigned to them. Modifications and deletions are forbidden.
    """
    message = "You do not have permission to perform this compliance operation."

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
            if request.method not in SAFE_METHODS:
                return False

            # Check relevance for ComplianceRequirement
            if hasattr(obj, 'requirement_code'):
                if obj.assigned_to == user:
                    return True
                # Check if technician has work orders or executions on this aircraft
                return (
                    obj.aircraft.work_orders.filter(assigned_to=user).exists() or
                    obj.aircraft.maintenance_executions.filter(executed_by=user).exists()
                )

            # Check relevance for ComplianceRecord
            if hasattr(obj, 'verification_status'):
                if obj.maintenance_execution and obj.maintenance_execution.executed_by == user:
                    return True
                if obj.requirement.assigned_to == user:
                    return True
                return (
                    obj.aircraft.work_orders.filter(assigned_to=user).exists() or
                    obj.aircraft.maintenance_executions.filter(executed_by=user).exists()
                )

        return False

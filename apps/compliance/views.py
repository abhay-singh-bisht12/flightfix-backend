"""
Views and ViewSets for FlightFix Airworthiness & Regulatory Compliance module.
"""

from django.db import models, transaction
from django.utils import timezone
from rest_framework import viewsets, filters

from apps.accounts.models import User
from apps.aircraft.pagination import StandardResultsSetPagination
from apps.compliance.models import (
    ComplianceRequirement,
    ComplianceRecord,
    RequirementStatus,
    VerificationStatus,
)
from apps.compliance.permissions import CompliancePermission
from apps.compliance.serializers import (
    ComplianceRequirementSerializer,
    ComplianceRequirementDetailSerializer,
    ComplianceRecordSerializer,
)


class ComplianceRequirementViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Compliance Requirements (Airworthiness Directives, SBs, etc.).
    Supports search, multi-field filtering, ordering, pagination, and automated expiration logic.
    """
    queryset = ComplianceRequirement.objects.select_related(
        'aircraft',
        'assigned_to',
        'created_by'
    ).all()
    permission_classes = [CompliancePermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'requirement_code',
        'title',
        'description',
        'issuing_authority',
        'aircraft__registration_number',
        'aircraft__model',
        'assigned_to__username',
    ]

    ordering_fields = [
        'due_date',
        'effective_date',
        'priority',
        'status',
        'requirement_code',
        'created_at',
    ]
    ordering = ['-due_date']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ComplianceRequirementDetailSerializer
        return ComplianceRequirementSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # FIELD_TECHNICIAN can only view compliance requirements relevant to their aircraft/tasks
        if user.is_authenticated and not (user.is_superuser or user.role == User.Role.ADMIN):
            if user.role == User.Role.FIELD_TECHNICIAN:
                queryset = queryset.filter(
                    models.Q(assigned_to=user) |
                    models.Q(aircraft__work_orders__assigned_to=user) |
                    models.Q(aircraft__maintenance_executions__executed_by=user)
                ).distinct()

        # Filter by aircraft (ID or registration number)
        aircraft_param = self.request.query_params.get('aircraft')
        if aircraft_param:
            if aircraft_param.isdigit():
                queryset = queryset.filter(aircraft_id=aircraft_param)
            else:
                queryset = queryset.filter(aircraft__registration_number__iexact=aircraft_param.strip())

        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status__iexact=status_param.strip())

        # Filter by priority
        priority_param = self.request.query_params.get('priority')
        if priority_param:
            queryset = queryset.filter(priority__iexact=priority_param.strip())

        # Filter by regulation type
        type_param = self.request.query_params.get('regulation_type')
        if type_param:
            queryset = queryset.filter(regulation_type__iexact=type_param.strip())

        # Filter by assigned_to
        assigned_param = self.request.query_params.get('assigned_to')
        if assigned_param:
            if assigned_param.isdigit():
                queryset = queryset.filter(assigned_to_id=assigned_param)
            else:
                queryset = queryset.filter(assigned_to__username__iexact=assigned_param.strip())

        # Filter by due_date
        due_date_param = self.request.query_params.get('due_date')
        if due_date_param:
            queryset = queryset.filter(due_date=due_date_param.strip())

        # Filter by effective_date
        effective_date_param = self.request.query_params.get('effective_date')
        if effective_date_param:
            queryset = queryset.filter(effective_date=effective_date_param.strip())

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ComplianceRecordViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Compliance Verification Records.
    Audits verification evidence, certifiers, and updates requirement compliance status.
    """
    queryset = ComplianceRecord.objects.select_related(
        'requirement',
        'aircraft',
        'maintenance_execution',
        'verified_by'
    ).all()
    permission_classes = [CompliancePermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'evidence_reference',
        'findings',
        'corrective_action',
        'remarks',
        'requirement__requirement_code',
        'requirement__title',
        'aircraft__registration_number',
        'verified_by__username',
    ]

    ordering_fields = [
        'created_at',
        'verified_at',
        'verification_status',
    ]
    ordering = ['-created_at']
    serializer_class = ComplianceRecordSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # FIELD_TECHNICIAN can only view compliance records relevant to their work
        if user.is_authenticated and not (user.is_superuser or user.role == User.Role.ADMIN):
            if user.role == User.Role.FIELD_TECHNICIAN:
                queryset = queryset.filter(
                    models.Q(requirement__assigned_to=user) |
                    models.Q(maintenance_execution__executed_by=user) |
                    models.Q(aircraft__work_orders__assigned_to=user)
                ).distinct()

        # Filter by requirement (ID or code)
        req_param = self.request.query_params.get('requirement')
        if req_param:
            if req_param.isdigit():
                queryset = queryset.filter(requirement_id=req_param)
            else:
                queryset = queryset.filter(requirement__requirement_code__iexact=req_param.strip())

        # Filter by aircraft
        aircraft_param = self.request.query_params.get('aircraft')
        if aircraft_param:
            if aircraft_param.isdigit():
                queryset = queryset.filter(aircraft_id=aircraft_param)
            else:
                queryset = queryset.filter(aircraft__registration_number__iexact=aircraft_param.strip())

        # Filter by verification status
        status_param = self.request.query_params.get('verification_status')
        if status_param:
            queryset = queryset.filter(verification_status__iexact=status_param.strip())

        # Filter by verified_by
        verifier_param = self.request.query_params.get('verified_by')
        if verifier_param:
            if verifier_param.isdigit():
                queryset = queryset.filter(verified_by_id=verifier_param)
            else:
                queryset = queryset.filter(verified_by__username__iexact=verifier_param.strip())

        # Filter by maintenance execution ID
        exec_param = self.request.query_params.get('maintenance_execution')
        if exec_param and exec_param.isdigit():
            queryset = queryset.filter(maintenance_execution_id=exec_param)

        # Date range filtering
        start_date = self.request.query_params.get('start_date') or self.request.query_params.get('date_from')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date.strip())

        end_date = self.request.query_params.get('end_date') or self.request.query_params.get('date_to')
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date.strip())

        return queryset

    def perform_create(self, serializer):
        requirement = serializer.validated_data['requirement']
        verified_by = serializer.validated_data.get('verified_by')
        verification_status = serializer.validated_data.get('verification_status', VerificationStatus.PENDING)

        # If VERIFIED and verified_by is not explicitly passed, assign authenticated certifier
        if verification_status == VerificationStatus.VERIFIED and not verified_by:
            verified_by = self.request.user

        verified_at = serializer.validated_data.get('verified_at')
        if verification_status == VerificationStatus.VERIFIED and not verified_at:
            verified_at = timezone.now()

        with transaction.atomic():
            serializer.save(
                aircraft=requirement.aircraft,
                verified_by=verified_by,
                verified_at=verified_at
            )

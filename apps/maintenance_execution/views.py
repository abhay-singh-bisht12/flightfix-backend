"""
Views and ViewSets for FlightFix Maintenance Execution & Documentation module.
"""

from django.db import transaction
from rest_framework import viewsets, filters

from apps.accounts.models import User
from apps.aircraft.pagination import StandardResultsSetPagination
from apps.maintenance_execution.models import (
    MaintenanceExecution,
    MaintenanceDocumentation,
    ExecutionStatus,
)
from apps.maintenance_execution.permissions import (
    MaintenanceExecutionPermission,
    MaintenanceDocumentationPermission,
)
from apps.maintenance_execution.serializers import (
    MaintenanceExecutionSerializer,
    MaintenanceExecutionDetailSerializer,
    MaintenanceDocumentationSerializer,
)


class MaintenanceExecutionViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Maintenance Execution Records.
    Supports real-time technician execution logs, labor hours, discrepancies, and work order sync.
    """
    queryset = MaintenanceExecution.objects.select_related(
        'work_order',
        'maintenance_task',
        'aircraft',
        'executed_by',
        'created_by'
    ).all()
    permission_classes = [MaintenanceExecutionPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'work_order__work_order_number',
        'aircraft__registration_number',
        'aircraft__model',
        'executed_by__username',
        'executed_by__first_name',
        'executed_by__last_name',
        'work_performed',
        'findings',
        'corrective_actions',
        'remarks',
    ]

    ordering_fields = [
        'created_at',
        'started_at',
        'completed_at',
        'actual_labor_hours',
        'status',
    ]
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MaintenanceExecutionDetailSerializer
        return MaintenanceExecutionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # FIELD_TECHNICIAN can only view executions assigned to them
        if user.is_authenticated and not (user.is_superuser or user.role == User.Role.ADMIN):
            if user.role == User.Role.FIELD_TECHNICIAN:
                queryset = queryset.filter(executed_by=user)

        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status__iexact=status_param.strip())

        # Filter by work order (ID or work order number)
        wo_param = self.request.query_params.get('work_order')
        if wo_param:
            if wo_param.isdigit():
                queryset = queryset.filter(work_order_id=wo_param)
            else:
                queryset = queryset.filter(work_order__work_order_number__iexact=wo_param.strip())

        # Filter by aircraft (ID or registration number)
        aircraft_param = self.request.query_params.get('aircraft')
        if aircraft_param:
            if aircraft_param.isdigit():
                queryset = queryset.filter(aircraft_id=aircraft_param)
            else:
                queryset = queryset.filter(aircraft__registration_number__iexact=aircraft_param.strip())

        # Filter by executed_by (ID or username)
        tech_param = self.request.query_params.get('executed_by')
        if tech_param:
            if tech_param.isdigit():
                queryset = queryset.filter(executed_by_id=tech_param)
            else:
                queryset = queryset.filter(executed_by__username__iexact=tech_param.strip())

        # Filter by date range
        start_date = self.request.query_params.get('start_date') or self.request.query_params.get('date_from')
        if start_date:
            queryset = queryset.filter(started_at__date__gte=start_date.strip())

        end_date = self.request.query_params.get('end_date') or self.request.query_params.get('date_to')
        if end_date:
            queryset = queryset.filter(completed_at__date__lte=end_date.strip())

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        work_order = serializer.validated_data['work_order']

        # Determine executed_by technician
        executed_by = serializer.validated_data.get('executed_by')
        if user.role == User.Role.FIELD_TECHNICIAN or not executed_by:
            executed_by = user

        with transaction.atomic():
            execution = serializer.save(
                created_by=user,
                aircraft=work_order.aircraft,
                executed_by=executed_by
            )

            # Sync WorkOrder status and actual hours if completed
            if execution.status == ExecutionStatus.COMPLETED:
                if execution.completed_at and not work_order.actual_completion_date:
                    work_order.actual_completion_date = execution.completed_at.date()
                if execution.actual_labor_hours and not work_order.actual_hours:
                    work_order.actual_hours = execution.actual_labor_hours
                work_order.save()


class MaintenanceDocumentationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Maintenance Documentation & Release-to-Service sign-offs.
    """
    queryset = MaintenanceDocumentation.objects.select_related(
        'execution',
        'execution__work_order',
        'signed_off_by'
    ).all()
    permission_classes = [MaintenanceDocumentationPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'document_number',
        'title',
        'issuing_authority',
        'document_reference',
        'remarks',
        'execution__work_order__work_order_number',
        'signed_off_by__username',
    ]

    ordering_fields = [
        'created_at',
        'signed_off_at',
        'document_type',
        'sign_off_status',
    ]
    ordering = ['-created_at']
    serializer_class = MaintenanceDocumentationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # FIELD_TECHNICIAN can only view documentation for executions assigned to them
        if user.is_authenticated and not (user.is_superuser or user.role == User.Role.ADMIN):
            if user.role == User.Role.FIELD_TECHNICIAN:
                queryset = queryset.filter(execution__executed_by=user)

        # Filter by document type
        type_param = self.request.query_params.get('document_type')
        if type_param:
            queryset = queryset.filter(document_type__iexact=type_param.strip())

        # Filter by sign_off_status
        status_param = self.request.query_params.get('sign_off_status')
        if status_param:
            queryset = queryset.filter(sign_off_status__iexact=status_param.strip())

        # Filter by execution ID
        exec_param = self.request.query_params.get('execution')
        if exec_param and exec_param.isdigit():
            queryset = queryset.filter(execution_id=exec_param)

        # Filter by work order number
        wo_param = self.request.query_params.get('work_order')
        if wo_param:
            if wo_param.isdigit():
                queryset = queryset.filter(execution__work_order_id=wo_param)
            else:
                queryset = queryset.filter(execution__work_order__work_order_number__iexact=wo_param.strip())

        # Filter by certifier
        certifier_param = self.request.query_params.get('signed_off_by')
        if certifier_param:
            if certifier_param.isdigit():
                queryset = queryset.filter(signed_off_by_id=certifier_param)
            else:
                queryset = queryset.filter(signed_off_by__username__iexact=certifier_param.strip())

        return queryset

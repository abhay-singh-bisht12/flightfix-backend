"""
Views and ViewSets for FlightFix Work Order Management.
"""

from rest_framework import viewsets, filters
from apps.accounts.models import User
from apps.aircraft.pagination import StandardResultsSetPagination
from apps.work_orders.models import WorkOrder
from apps.work_orders.permissions import WorkOrderPermission
from apps.work_orders.serializers import (
    WorkOrderSerializer,
    WorkOrderDetailSerializer,
)


class WorkOrderViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Work Orders.
    Supports search, multi-field filtering, ordering, and pagination.
    """
    queryset = WorkOrder.objects.select_related(
        'aircraft',
        'maintenance_schedule',
        'assigned_to',
        'created_by'
    ).all()

    permission_classes = [WorkOrderPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'work_order_number',
        'title',
        'description',
        'findings',
        'corrective_action',
        'aircraft__registration_number',
        'aircraft__model',
        'assigned_to__username',
        'assigned_to__first_name',
        'assigned_to__last_name',
    ]

    ordering_fields = [
        'work_order_number',
        'planned_start_date',
        'planned_completion_date',
        'actual_start_date',
        'actual_completion_date',
        'priority',
        'status',
        'created_at',
    ]
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WorkOrderDetailSerializer
        return WorkOrderSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # FIELD_TECHNICIAN can only view work orders assigned to them
        if user.is_authenticated and not (user.is_superuser or user.role == User.Role.ADMIN):
            if user.role == User.Role.FIELD_TECHNICIAN:
                queryset = queryset.filter(assigned_to=user)

        # Filters
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status__iexact=status_param.strip())

        priority_param = self.request.query_params.get('priority')
        if priority_param:
            queryset = queryset.filter(priority__iexact=priority_param.strip())

        type_param = self.request.query_params.get('work_order_type')
        if type_param:
            queryset = queryset.filter(work_order_type__iexact=type_param.strip())

        aircraft_param = self.request.query_params.get('aircraft')
        if aircraft_param:
            if aircraft_param.isdigit():
                queryset = queryset.filter(aircraft_id=aircraft_param)
            else:
                queryset = queryset.filter(aircraft__registration_number__iexact=aircraft_param.strip())

        assigned_to_param = self.request.query_params.get('assigned_to')
        if assigned_to_param:
            if assigned_to_param.isdigit():
                queryset = queryset.filter(assigned_to_id=assigned_to_param)
            else:
                queryset = queryset.filter(assigned_to__username__iexact=assigned_to_param.strip())

        schedule_param = self.request.query_params.get('maintenance_schedule')
        if schedule_param:
            queryset = queryset.filter(maintenance_schedule_id=schedule_param.strip())

        planned_start_param = self.request.query_params.get('planned_start_date')
        if planned_start_param:
            queryset = queryset.filter(planned_start_date=planned_start_param.strip())

        planned_completion_param = self.request.query_params.get('planned_completion_date')
        if planned_completion_param:
            queryset = queryset.filter(planned_completion_date=planned_completion_param.strip())

        return queryset

    def perform_create(self, serializer):
        # Automatically assign the creating user
        serializer.save(created_by=self.request.user)

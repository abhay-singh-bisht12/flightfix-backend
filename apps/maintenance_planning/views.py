"""
Views and ViewSets for FlightFix Maintenance Planning & Scheduling module.
"""

from rest_framework import viewsets, filters
from apps.accounts.models import User
from apps.aircraft.pagination import StandardResultsSetPagination
from apps.maintenance_planning.models import MaintenanceSchedule, MaintenanceTask
from apps.maintenance_planning.permissions import MaintenancePlanningPermission
from apps.maintenance_planning.serializers import (
    MaintenanceScheduleSerializer,
    MaintenanceScheduleDetailSerializer,
    MaintenanceTaskSerializer,
)


class MaintenanceScheduleViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Maintenance Schedules.
    Supports search, status/priority/type/aircraft/assigned_to/date filtering, ordering, and pagination.
    """
    queryset = MaintenanceSchedule.objects.select_related(
        'aircraft',
        'assigned_to',
        'created_by'
    ).prefetch_related('tasks').all()

    permission_classes = [MaintenancePlanningPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'title',
        'description',
        'aircraft__registration_number',
        'aircraft__model',
        'assigned_to__username',
        'assigned_to__first_name',
        'assigned_to__last_name',
    ]
    ordering_fields = [
        'planned_date',
        'due_date',
        'priority',
        'status',
        'created_at',
    ]
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MaintenanceScheduleDetailSerializer
        return MaintenanceScheduleSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # FIELD_TECHNICIAN can only view schedules assigned to them
        if user.is_authenticated and not (user.is_superuser or user.role == User.Role.ADMIN):
            if user.role == User.Role.FIELD_TECHNICIAN:
                queryset = queryset.filter(assigned_to=user)

        # Query parameter filters
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status__iexact=status_param.strip())

        priority_param = self.request.query_params.get('priority')
        if priority_param:
            queryset = queryset.filter(priority__iexact=priority_param.strip())

        type_param = self.request.query_params.get('maintenance_type')
        if type_param:
            queryset = queryset.filter(maintenance_type__iexact=type_param.strip())

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

        planned_date_param = self.request.query_params.get('planned_date')
        if planned_date_param:
            queryset = queryset.filter(planned_date=planned_date_param.strip())

        due_date_param = self.request.query_params.get('due_date')
        if due_date_param:
            queryset = queryset.filter(due_date=due_date_param.strip())

        return queryset

    def perform_create(self, serializer):
        # Automatically assign the creating user
        serializer.save(created_by=self.request.user)


class MaintenanceTaskViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for individual Maintenance Tasks.
    Supports search, status/schedule filtering, ordering, and pagination.
    """
    queryset = MaintenanceTask.objects.select_related(
        'schedule',
        'schedule__aircraft',
        'schedule__assigned_to'
    ).all()

    serializer_class = MaintenanceTaskSerializer
    permission_classes = [MaintenancePlanningPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'task_name',
        'description',
        'schedule__title',
        'schedule__aircraft__registration_number',
    ]
    ordering_fields = [
        'task_order',
        'status',
        'estimated_hours',
        'completed_at',
        'created_at',
    ]
    ordering = ['task_order', 'id']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # FIELD_TECHNICIAN can only view tasks of schedules assigned to them
        if user.is_authenticated and not (user.is_superuser or user.role == User.Role.ADMIN):
            if user.role == User.Role.FIELD_TECHNICIAN:
                queryset = queryset.filter(schedule__assigned_to=user)

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status__iexact=status_param.strip())

        schedule_param = self.request.query_params.get('schedule')
        if schedule_param:
            queryset = queryset.filter(schedule_id=schedule_param.strip())

        return queryset

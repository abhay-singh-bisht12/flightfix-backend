"""
Views for FlightFix Mobile / Field Technician Support module.
"""

from django.db.models import Q
from rest_framework import filters, mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.aircraft.models import Aircraft
from apps.aircraft.pagination import StandardResultsSetPagination
from apps.compliance.models import ComplianceRecord, VerificationStatus
from apps.inventory.models import SparePart
from apps.maintenance_execution.models import MaintenanceExecution
from apps.maintenance_planning.models import (
    MaintenanceSchedule,
    MaintenanceTask,
    TaskStatus,
)
from apps.mobile.permissions import IsFieldTechnician
from apps.mobile.serializers import (
    TechnicianAircraftSerializer,
    TechnicianAvailablePartSerializer,
    TechnicianComplianceRecordSerializer,
    TechnicianDashboardSerializer,
    TechnicianExecutionCreateSerializer,
    TechnicianExecutionSerializer,
    TechnicianExecutionUpdateSerializer,
    TechnicianTaskSerializer,
    TechnicianWorkOrderSerializer,
    TechnicianWorkOrderUpdateSerializer,
)
from apps.work_orders.models import WorkOrder, WorkOrderStatus


class TechnicianDashboardView(APIView):
    """
    Compact mobile dashboard for authenticated field technicians.
    Returns technician profile, summary counts, assigned aircraft, tasks,
    work orders, and recent execution records.
    """
    permission_classes = [IsAuthenticated, IsFieldTechnician]

    def get(self, request):
        user = request.user

        # 1. Summary counts
        assigned_schedules_count = MaintenanceSchedule.objects.filter(
            assigned_to=user
        ).count()

        pending_tasks_count = MaintenanceTask.objects.filter(
            schedule__assigned_to=user,
            status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
        ).count()

        open_work_orders_count = WorkOrder.objects.filter(
            assigned_to=user,
            status__in=[
                WorkOrderStatus.OPEN,
                WorkOrderStatus.ASSIGNED,
                WorkOrderStatus.IN_PROGRESS,
                WorkOrderStatus.ON_HOLD,
            ]
        ).count()

        pending_compliance_count = ComplianceRecord.objects.filter(
            Q(maintenance_execution__executed_by=user) |
            Q(aircraft__work_orders__assigned_to=user) |
            Q(aircraft__maintenance_schedules__assigned_to=user)
        ).exclude(verification_status=VerificationStatus.VERIFIED).distinct().count()

        # 2. Scoped data querysets with query optimization
        assigned_aircraft_qs = Aircraft.objects.filter(
            Q(work_orders__assigned_to=user) |
            Q(maintenance_schedules__assigned_to=user) |
            Q(maintenance_executions__executed_by=user)
        ).distinct()[:10]

        tasks_qs = MaintenanceTask.objects.filter(
            schedule__assigned_to=user
        ).select_related('schedule', 'schedule__aircraft').order_by('status', 'task_order', '-created_at')[:10]

        work_orders_qs = WorkOrder.objects.filter(
            assigned_to=user
        ).select_related('aircraft', 'maintenance_schedule').order_by('-created_at')[:10]

        recent_executions_qs = MaintenanceExecution.objects.filter(
            executed_by=user
        ).select_related('work_order', 'aircraft', 'maintenance_task', 'executed_by', 'created_by').order_by('-created_at')[:10]

        dashboard_payload = {
            'technician': user,
            'summary': {
                'assigned_schedules': assigned_schedules_count,
                'pending_tasks': pending_tasks_count,
                'open_work_orders': open_work_orders_count,
                'pending_compliance': pending_compliance_count,
            },
            'assigned_aircraft': assigned_aircraft_qs,
            'tasks': tasks_qs,
            'work_orders': work_orders_qs,
            'recent_executions': recent_executions_qs,
        }

        serializer = TechnicianDashboardSerializer(dashboard_payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TechnicianTaskViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for maintenance tasks assigned to the logged-in technician.
    Supports filtering by status, planned_date, due_date, search, and ordering.
    """
    permission_classes = [IsAuthenticated, IsFieldTechnician]
    serializer_class = TechnicianTaskSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'task_name',
        'description',
        'notes',
        'schedule__title',
        'schedule__aircraft__registration_number',
    ]
    ordering_fields = ['task_order', 'status', 'created_at', 'schedule__planned_date', 'schedule__due_date']
    ordering = ['task_order', 'id']

    def get_queryset(self):
        user = self.request.user
        qs = MaintenanceTask.objects.filter(
            schedule__assigned_to=user
        ).select_related('schedule', 'schedule__aircraft')

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status__iexact=status_param.strip())

        planned_date = self.request.query_params.get('planned_date')
        if planned_date:
            qs = qs.filter(schedule__planned_date=planned_date)

        due_date = self.request.query_params.get('due_date')
        if due_date:
            qs = qs.filter(schedule__due_date=due_date)

        return qs


class TechnicianWorkOrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    """
    Viewset for work orders assigned to the logged-in technician.
    Allows listing, retrieval, and partial updates (PATCH) to execution fields.
    Blocks PUT, POST, and DELETE.
    """
    http_method_names = ['get', 'patch', 'head', 'options']
    permission_classes = [IsAuthenticated, IsFieldTechnician]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'work_order_number',
        'title',
        'description',
        'findings',
        'corrective_action',
        'notes',
        'aircraft__registration_number',
    ]
    ordering_fields = ['created_at', 'priority', 'status', 'planned_start_date', 'actual_start_date']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return TechnicianWorkOrderUpdateSerializer
        return TechnicianWorkOrderSerializer

    def get_queryset(self):
        user = self.request.user
        qs = WorkOrder.objects.filter(
            assigned_to=user
        ).select_related('aircraft', 'maintenance_schedule')

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status__iexact=status_param.strip())

        priority_param = self.request.query_params.get('priority')
        if priority_param:
            qs = qs.filter(priority__iexact=priority_param.strip())

        aircraft_param = self.request.query_params.get('aircraft')
        if aircraft_param:
            if aircraft_param.isdigit():
                qs = qs.filter(aircraft_id=aircraft_param)
            else:
                qs = qs.filter(aircraft__registration_number__iexact=aircraft_param.strip())

        return qs


class TechnicianExecutionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    """
    Viewset for maintenance execution records performed by the logged-in technician.
    Supports listing, retrieval, execution creation (POST), and updates (PATCH).
    Blocks PUT and DELETE.
    """
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    permission_classes = [IsAuthenticated, IsFieldTechnician]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'work_order__work_order_number',
        'work_performed',
        'findings',
        'corrective_actions',
        'remarks',
        'aircraft__registration_number',
    ]
    ordering_fields = ['created_at', 'started_at', 'completed_at', 'actual_labor_hours', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return TechnicianExecutionCreateSerializer
        elif self.action == 'partial_update':
            return TechnicianExecutionUpdateSerializer
        return TechnicianExecutionSerializer

    def get_queryset(self):
        user = self.request.user
        qs = MaintenanceExecution.objects.filter(
            executed_by=user
        ).select_related(
            'work_order',
            'aircraft',
            'maintenance_task',
            'executed_by',
            'created_by'
        )

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status__iexact=status_param.strip())

        work_order_param = self.request.query_params.get('work_order')
        if work_order_param:
            qs = qs.filter(work_order_id=work_order_param)

        aircraft_param = self.request.query_params.get('aircraft')
        if aircraft_param:
            qs = qs.filter(aircraft_id=aircraft_param)

        return qs


class TechnicianAircraftViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for aircraft relevant to the logged-in technician's assignments.
    Prevents exposure of unrelated fleet aircraft.
    """
    http_method_names = ['get', 'head', 'options']
    permission_classes = [IsAuthenticated, IsFieldTechnician]
    serializer_class = TechnicianAircraftSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['registration_number', 'model', 'manufacturer', 'serial_number']
    ordering_fields = ['registration_number', 'model', 'manufacturer', 'status', 'created_at']
    ordering = ['registration_number']

    def get_queryset(self):
        user = self.request.user
        qs = Aircraft.objects.filter(
            Q(work_orders__assigned_to=user) |
            Q(maintenance_schedules__assigned_to=user) |
            Q(maintenance_executions__executed_by=user)
        ).distinct()

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status__iexact=status_param.strip())

        aircraft_type_param = self.request.query_params.get('aircraft_type')
        if aircraft_type_param:
            qs = qs.filter(aircraft_type__iexact=aircraft_type_param.strip())

        return qs


class TechnicianComplianceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for compliance records relevant to technician assignments.
    Technicians cannot create or delete compliance requirements or verification records.
    """
    http_method_names = ['get', 'head', 'options']
    permission_classes = [IsAuthenticated, IsFieldTechnician]
    serializer_class = TechnicianComplianceRecordSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'requirement__requirement_code',
        'requirement__title',
        'evidence_reference',
        'aircraft__registration_number',
    ]
    ordering_fields = ['created_at', 'verification_status', 'requirement__due_date']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs = ComplianceRecord.objects.filter(
            Q(maintenance_execution__executed_by=user) |
            Q(aircraft__work_orders__assigned_to=user) |
            Q(aircraft__maintenance_schedules__assigned_to=user)
        ).select_related('requirement', 'aircraft', 'verified_by').distinct()

        verification_status = self.request.query_params.get('verification_status')
        if verification_status:
            qs = qs.filter(verification_status__iexact=verification_status.strip())

        requirement_code = self.request.query_params.get('requirement_code')
        if requirement_code:
            qs = qs.filter(requirement__requirement_code__iexact=requirement_code.strip())

        return qs


class TechnicianAvailablePartsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for spare parts inventory needed by technicians.
    Strictly excludes vendor and purchasing data.
    """
    http_method_names = ['get', 'head', 'options']
    permission_classes = [IsAuthenticated, IsFieldTechnician]
    serializer_class = TechnicianAvailablePartSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'part_number',
        'name',
        'manufacturer',
        'manufacturer_part_number',
        'location',
        'description',
    ]
    ordering_fields = ['part_number', 'name', 'quantity_in_stock', 'status']
    ordering = ['part_number']

    def get_queryset(self):
        qs = SparePart.objects.all()

        category_param = self.request.query_params.get('category')
        if category_param:
            qs = qs.filter(category__iexact=category_param.strip())

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status__iexact=status_param.strip())

        return qs

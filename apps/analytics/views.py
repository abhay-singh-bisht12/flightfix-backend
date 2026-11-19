"""
Views for FlightFix Analytics & Reporting module.
All views are strictly read-only and restricted to management roles.
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.aircraft.models import Aircraft, AircraftStatus
from apps.analytics.permissions import IsAnalyticsUser
from apps.analytics.utils import parse_date_range
from apps.compliance.models import (
    ComplianceRecord,
    ComplianceRequirement,
    RegulationType,
    RequirementPriority,
    RequirementStatus,
    VerificationStatus,
)
from apps.inventory.models import PartCategory, SparePart, StockStatus, TransactionType
from apps.maintenance_execution.models import ExecutionStatus, MaintenanceExecution
from apps.maintenance_planning.models import (
    MaintenancePriority,
    MaintenanceSchedule,
    MaintenanceStatus,
    MaintenanceType,
    TaskStatus,
)
from apps.supply_chain.models import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderPriority,
    PurchaseOrderStatus,
    Supplier,
    SupplierStatus,
    SupplierType,
)
from apps.work_orders.models import (
    WorkOrder,
    WorkOrderPriority,
    WorkOrderStatus,
)

User = get_user_model()


class AnalyticsDashboardView(APIView):
    """
    Management dashboard providing executive high-level metrics across
    aircraft, maintenance, inventory, compliance, and supply chain.
    """
    http_method_names = ['get', 'head', 'options']
    permission_classes = [IsAuthenticated, IsAnalyticsUser]

    def get(self, request):
        today = timezone.now().date()

        # 1. Aircraft metrics
        total_aircraft = Aircraft.objects.count()
        active_aircraft = Aircraft.objects.filter(status=AircraftStatus.ACTIVE).count()

        # 2. Maintenance Schedule metrics
        total_maint_schedules = MaintenanceSchedule.objects.count()
        pending_maint_schedules = MaintenanceSchedule.objects.filter(
            status__in=[MaintenanceStatus.PLANNED, MaintenanceStatus.IN_PROGRESS]
        ).count()
        overdue_maint_schedules = MaintenanceSchedule.objects.filter(
            due_date__lt=today
        ).exclude(status__in=[MaintenanceStatus.COMPLETED, MaintenanceStatus.CANCELLED]).count()
        completed_maint_schedules = MaintenanceSchedule.objects.filter(
            status=MaintenanceStatus.COMPLETED
        ).count()

        # 3. Work Order metrics
        total_work_orders = WorkOrder.objects.count()
        open_wo_count = WorkOrder.objects.filter(
            status__in=[
                WorkOrderStatus.OPEN,
                WorkOrderStatus.ASSIGNED,
                WorkOrderStatus.IN_PROGRESS,
                WorkOrderStatus.ON_HOLD,
            ]
        ).count()
        completed_work_orders = WorkOrder.objects.filter(
            status=WorkOrderStatus.COMPLETED
        ).count()

        # 4. Maintenance Executions
        total_executions = MaintenanceExecution.objects.count()

        # 5. Inventory & Spare Parts
        total_spare_parts = SparePart.objects.count()
        low_stock_parts = SparePart.objects.filter(status=StockStatus.LOW_STOCK).count()
        out_of_stock_parts = SparePart.objects.filter(status=StockStatus.OUT_OF_STOCK).count()

        # 6. Compliance
        open_compliance = ComplianceRequirement.objects.filter(
            status__in=[RequirementStatus.OPEN, RequirementStatus.IN_PROGRESS]
        ).count()
        non_compliant = ComplianceRequirement.objects.filter(
            status=RequirementStatus.NON_COMPLIANT
        ).count()
        expired_compliance = ComplianceRequirement.objects.filter(
            Q(status=RequirementStatus.EXPIRED) |
            (Q(due_date__lt=today) & ~Q(status=RequirementStatus.COMPLIANT))
        ).count()

        # 7. Supply Chain
        total_suppliers = Supplier.objects.count()
        active_suppliers = Supplier.objects.filter(status=SupplierStatus.ACTIVE).count()

        po_counts_qs = PurchaseOrder.objects.values('status').annotate(total=Count('id'))
        po_counts_dict = {row['status']: row['total'] for row in po_counts_qs}
        po_by_status = {choice: po_counts_dict.get(choice, 0) for choice in PurchaseOrderStatus.values}

        payload = {
            'total_aircraft': total_aircraft,
            'active_aircraft': active_aircraft,
            'total_maintenance_schedules': total_maint_schedules,
            'pending_maintenance_schedules': pending_maint_schedules,
            'overdue_maintenance_schedules': overdue_maint_schedules,
            'completed_maintenance_schedules': completed_maint_schedules,
            'total_work_orders': total_work_orders,
            'open_work_orders': open_wo_count,
            'open_in_progress_work_orders': open_wo_count,
            'completed_work_orders': completed_work_orders,
            'total_maintenance_executions': total_executions,
            'total_spare_parts': total_spare_parts,
            'low_stock_spare_parts': low_stock_parts,
            'out_of_stock_spare_parts': out_of_stock_parts,
            'open_compliance_requirements': open_compliance,
            'non_compliant_requirements': non_compliant,
            'expired_requirements': expired_compliance,
            'total_suppliers': total_suppliers,
            'active_suppliers': active_suppliers,
            'purchase_orders_by_status': po_by_status,
        }

        return Response(payload, status=status.HTTP_200_OK)


class MaintenanceSummaryView(APIView):
    """
    Provides maintenance KPIs: schedules, work orders, executions,
    completed vs pending breakdown, and overdue counts.
    Supports optional date filtering via 'start_date' and 'end_date' (YYYY-MM-DD).
    """
    http_method_names = ['get', 'head', 'options']
    permission_classes = [IsAuthenticated, IsAnalyticsUser]

    def get(self, request):
        today = timezone.now().date()
        start_date, end_date = parse_date_range(request)

        # Schedules base queryset with date filter
        schedules_qs = MaintenanceSchedule.objects.all()
        if start_date:
            schedules_qs = schedules_qs.filter(planned_date__gte=start_date)
        if end_date:
            schedules_qs = schedules_qs.filter(planned_date__lte=end_date)

        # Work Orders base queryset with date filter
        wo_qs = WorkOrder.objects.all()
        if start_date:
            wo_qs = wo_qs.filter(Q(planned_start_date__gte=start_date) | Q(created_at__date__gte=start_date))
        if end_date:
            wo_qs = wo_qs.filter(Q(planned_start_date__lte=end_date) | Q(created_at__date__lte=end_date))

        # Executions base queryset with date filter
        exec_qs = MaintenanceExecution.objects.all()
        if start_date:
            exec_qs = exec_qs.filter(Q(started_at__date__gte=start_date) | Q(created_at__date__gte=start_date))
        if end_date:
            exec_qs = exec_qs.filter(Q(started_at__date__lte=end_date) | Q(created_at__date__lte=end_date))

        # Schedules by status
        sched_status_counts = dict(schedules_qs.values('status').annotate(total=Count('id')).values_list('status', 'total'))
        schedules_by_status = {choice: sched_status_counts.get(choice, 0) for choice in MaintenanceStatus.values}

        # Schedules by maintenance type
        sched_type_counts = dict(schedules_qs.values('maintenance_type').annotate(total=Count('id')).values_list('maintenance_type', 'total'))
        schedules_by_type = {choice: sched_type_counts.get(choice, 0) for choice in MaintenanceType.values}

        # Schedules by priority
        sched_pri_counts = dict(schedules_qs.values('priority').annotate(total=Count('id')).values_list('priority', 'total'))
        schedules_by_priority = {choice: sched_pri_counts.get(choice, 0) for choice in MaintenancePriority.values}

        # Work Orders by status
        wo_status_counts = dict(wo_qs.values('status').annotate(total=Count('id')).values_list('status', 'total'))
        work_orders_by_status = {choice: wo_status_counts.get(choice, 0) for choice in WorkOrderStatus.values}

        # Work Orders by priority
        wo_pri_counts = dict(wo_qs.values('priority').annotate(total=Count('id')).values_list('priority', 'total'))
        work_orders_by_priority = {choice: wo_pri_counts.get(choice, 0) for choice in WorkOrderPriority.values}

        # Executions by status
        exec_status_counts = dict(exec_qs.values('status').annotate(total=Count('id')).values_list('status', 'total'))
        executions_by_status = {choice: exec_status_counts.get(choice, 0) for choice in ExecutionStatus.values}

        # Completed vs Pending maintenance
        completed_schedules = schedules_qs.filter(status=MaintenanceStatus.COMPLETED).count()
        pending_schedules = schedules_qs.filter(status__in=[MaintenanceStatus.PLANNED, MaintenanceStatus.IN_PROGRESS]).count()
        completed_work_orders = wo_qs.filter(status=WorkOrderStatus.COMPLETED).count()
        pending_work_orders = wo_qs.filter(status__in=[
            WorkOrderStatus.OPEN,
            WorkOrderStatus.ASSIGNED,
            WorkOrderStatus.IN_PROGRESS,
            WorkOrderStatus.ON_HOLD,
        ]).count()

        # Overdue maintenance count
        overdue_count = schedules_qs.filter(due_date__lt=today).exclude(
            status__in=[MaintenanceStatus.COMPLETED, MaintenanceStatus.CANCELLED]
        ).count()

        payload = {
            'schedules_by_status': schedules_by_status,
            'schedules_by_maintenance_type': schedules_by_type,
            'schedules_by_priority': schedules_by_priority,
            'work_orders_by_status': work_orders_by_status,
            'work_orders_by_priority': work_orders_by_priority,
            'executions_by_status': executions_by_status,
            'completed_vs_pending_maintenance': {
                'completed_schedules': completed_schedules,
                'pending_schedules': pending_schedules,
                'completed_work_orders': completed_work_orders,
                'pending_work_orders': pending_work_orders,
            },
            'overdue_maintenance_count': overdue_count,
            'date_filter': {
                'start_date': str(start_date) if start_date else None,
                'end_date': str(end_date) if end_date else None,
            },
        }

        return Response(payload, status=status.HTTP_200_OK)


class AircraftSummaryView(APIView):
    """
    Fleet analytics summarizing aircraft distribution by status, aircraft type,
    manufacturer, and operational maintenance activity per airframe.
    """
    http_method_names = ['get', 'head', 'options']
    permission_classes = [IsAuthenticated, IsAnalyticsUser]

    def get(self, request):
        # 1. Aircraft count by status
        status_counts = dict(Aircraft.objects.values('status').annotate(total=Count('id')).values_list('status', 'total'))
        aircraft_by_status = {choice: status_counts.get(choice, 0) for choice in AircraftStatus.values}

        # 2. Aircraft count by aircraft type
        type_counts = dict(Aircraft.objects.values('aircraft_type').annotate(total=Count('id')).values_list('aircraft_type', 'total'))

        # 3. Aircraft count by manufacturer
        manufacturer_counts = dict(Aircraft.objects.values('manufacturer').annotate(total=Count('id')).values_list('manufacturer', 'total'))

        # 4. Maintenance activity per aircraft
        aircraft_annotated = Aircraft.objects.annotate(
            schedules_count=Count('maintenance_schedules', distinct=True),
            work_orders_count=Count('work_orders', distinct=True),
            executions_count=Count('maintenance_executions', distinct=True),
        ).values(
            'id',
            'registration_number',
            'model',
            'manufacturer',
            'status',
            'schedules_count',
            'work_orders_count',
            'executions_count',
        ).order_by('registration_number')

        activity_list = list(aircraft_annotated)
        wo_count_per_aircraft = {item['registration_number']: item['work_orders_count'] for item in activity_list}
        exec_count_per_aircraft = {item['registration_number']: item['executions_count'] for item in activity_list}

        payload = {
            'aircraft_count_by_status': aircraft_by_status,
            'aircraft_count_by_aircraft_type': type_counts,
            'aircraft_count_by_manufacturer': manufacturer_counts,
            'maintenance_activity_per_aircraft': activity_list,
            'work_order_count_per_aircraft': wo_count_per_aircraft,
            'execution_count_per_aircraft': exec_count_per_aircraft,
        }

        return Response(payload, status=status.HTTP_200_OK)


class InventorySummaryView(APIView):
    """
    Inventory analytics summarizing spare parts stock levels, transaction
    frequencies, high-demand components, and reorder alerts.
    """
    http_method_names = ['get', 'head', 'options']
    permission_classes = [IsAuthenticated, IsAnalyticsUser]

    def get(self, request):
        total_parts = SparePart.objects.count()
        in_stock_count = SparePart.objects.filter(status=StockStatus.IN_STOCK).count()
        low_stock_count = SparePart.objects.filter(status=StockStatus.LOW_STOCK).count()
        out_of_stock_count = SparePart.objects.filter(status=StockStatus.OUT_OF_STOCK).count()
        discontinued_count = SparePart.objects.filter(status=StockStatus.DISCONTINUED).count()

        # Transactions by type
        tx_counts = dict(SparePart.objects.model.transactions.field.model.objects.values('transaction_type').annotate(total=Count('id')).values_list('transaction_type', 'total'))
        transactions_by_type = {choice: tx_counts.get(choice, 0) for choice in TransactionType.values}

        # Most frequently issued parts
        frequent_parts_qs = SparePart.objects.filter(
            transactions__transaction_type=TransactionType.ISSUE
        ).annotate(
            total_quantity_issued=Sum('transactions__quantity'),
            issue_transactions_count=Count('transactions', distinct=True),
        ).order_by('-total_quantity_issued')[:10].values(
            'id',
            'part_number',
            'name',
            'category',
            'total_quantity_issued',
            'issue_transactions_count',
        )

        # Parts with low or out of stock
        low_stock_parts_qs = SparePart.objects.filter(
            Q(status__in=[StockStatus.LOW_STOCK, StockStatus.OUT_OF_STOCK]) |
            Q(quantity_in_stock__lte=F('minimum_stock_level'))
        ).values(
            'id',
            'part_number',
            'name',
            'category',
            'quantity_in_stock',
            'minimum_stock_level',
            'status',
            'location',
        ).order_by('quantity_in_stock')[:25]

        payload = {
            'total_spare_parts': total_parts,
            'in_stock_count': in_stock_count,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'discontinued_count': discontinued_count,
            'inventory_transactions_by_type': transactions_by_type,
            'most_frequently_issued_parts': list(frequent_parts_qs),
            'parts_with_low_stock': list(low_stock_parts_qs),
        }

        return Response(payload, status=status.HTTP_200_OK)


class ComplianceSummaryView(APIView):
    """
    Regulatory compliance analytics summarizing airworthiness directives,
    service bulletins, compliance rates, and verification audit statuses.
    """
    http_method_names = ['get', 'head', 'options']
    permission_classes = [IsAuthenticated, IsAnalyticsUser]

    def get(self, request):
        today = timezone.now().date()

        # Requirements by status
        req_status_counts = dict(ComplianceRequirement.objects.values('status').annotate(total=Count('id')).values_list('status', 'total'))
        requirements_by_status = {choice: req_status_counts.get(choice, 0) for choice in RequirementStatus.values}

        # Requirements by priority
        req_pri_counts = dict(ComplianceRequirement.objects.values('priority').annotate(total=Count('id')).values_list('priority', 'total'))
        requirements_by_priority = {choice: req_pri_counts.get(choice, 0) for choice in RequirementPriority.values}

        # Requirements by regulation type
        req_type_counts = dict(ComplianceRequirement.objects.values('regulation_type').annotate(total=Count('id')).values_list('regulation_type', 'total'))
        requirements_by_type = {choice: req_type_counts.get(choice, 0) for choice in RegulationType.values}

        # Overdue / Expired compliance requirements
        overdue_expired_count = ComplianceRequirement.objects.filter(
            Q(status=RequirementStatus.EXPIRED) |
            (Q(due_date__lt=today) & ~Q(status=RequirementStatus.COMPLIANT))
        ).count()

        # Compliant vs Non-Compliant counts
        compliant_count = ComplianceRequirement.objects.filter(status=RequirementStatus.COMPLIANT).count()
        non_compliant_count = ComplianceRequirement.objects.filter(status=RequirementStatus.NON_COMPLIANT).count()
        open_or_in_progress = ComplianceRequirement.objects.filter(status__in=[RequirementStatus.OPEN, RequirementStatus.IN_PROGRESS]).count()
        expired_count = ComplianceRequirement.objects.filter(status=RequirementStatus.EXPIRED).count()

        # Compliance records by verification status
        rec_status_counts = dict(ComplianceRecord.objects.values('verification_status').annotate(total=Count('id')).values_list('verification_status', 'total'))
        records_by_verification_status = {choice: rec_status_counts.get(choice, 0) for choice in VerificationStatus.values}

        payload = {
            'requirements_by_status': requirements_by_status,
            'requirements_by_priority': requirements_by_priority,
            'requirements_by_regulation_type': requirements_by_type,
            'overdue_expired_compliance_requirements': overdue_expired_count,
            'compliant_vs_non_compliant_counts': {
                'compliant': compliant_count,
                'non_compliant': non_compliant_count,
                'open_or_in_progress': open_or_in_progress,
                'expired': expired_count,
            },
            'compliance_records_by_verification_status': records_by_verification_status,
        }

        return Response(payload, status=status.HTTP_200_OK)


class SupplyChainSummaryView(APIView):
    """
    Supply chain & procurement analytics summarizing supplier statuses,
    purchase order commitments, total order values, and delivery tracking.
    """
    http_method_names = ['get', 'head', 'options']
    permission_classes = [IsAuthenticated, IsAnalyticsUser]

    def get(self, request):
        # Suppliers by status
        supp_status_counts = dict(Supplier.objects.values('status').annotate(total=Count('id')).values_list('status', 'total'))
        suppliers_by_status = {choice: supp_status_counts.get(choice, 0) for choice in SupplierStatus.values}

        # Suppliers by type
        supp_type_counts = dict(Supplier.objects.values('supplier_type').annotate(total=Count('id')).values_list('supplier_type', 'total'))
        suppliers_by_type = {choice: supp_type_counts.get(choice, 0) for choice in SupplierType.values}

        # Purchase orders by status
        po_status_counts = dict(PurchaseOrder.objects.values('status').annotate(total=Count('id')).values_list('status', 'total'))
        purchase_orders_by_status = {choice: po_status_counts.get(choice, 0) for choice in PurchaseOrderStatus.values}

        # Purchase orders by priority
        po_pri_counts = dict(PurchaseOrder.objects.values('priority').annotate(total=Count('id')).values_list('priority', 'total'))
        purchase_orders_by_priority = {choice: po_pri_counts.get(choice, 0) for choice in PurchaseOrderPriority.values}

        # Total purchase order value
        po_val_agg = PurchaseOrderItem.objects.aggregate(
            total_val=Sum(F('quantity_ordered') * F('unit_price'), output_field=models.DecimalField())
        )
        total_po_value = po_val_agg['total_val'] or Decimal('0.00')

        # Pending deliveries
        pending_deliveries = PurchaseOrder.objects.filter(
            status__in=[
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.ORDERED,
                PurchaseOrderStatus.PARTIALLY_RECEIVED,
            ],
            actual_delivery_date__isnull=True,
        ).count()

        # Received purchase orders
        received_purchase_orders = PurchaseOrder.objects.filter(
            status=PurchaseOrderStatus.RECEIVED
        ).count()

        payload = {
            'suppliers_by_status': suppliers_by_status,
            'suppliers_by_type': suppliers_by_type,
            'purchase_orders_by_status': purchase_orders_by_status,
            'purchase_orders_by_priority': purchase_orders_by_priority,
            'total_purchase_order_value': str(total_po_value),
            'pending_deliveries': pending_deliveries,
            'received_purchase_orders': received_purchase_orders,
        }

        return Response(payload, status=status.HTTP_200_OK)


class TechnicianPerformanceView(APIView):
    """
    Operational analytics reporting performance KPIs for field technicians:
    assigned/completed work orders, executions logged, actual labor hours,
    and task progress. Strictly avoids exposing sensitive user data.
    """
    http_method_names = ['get', 'head', 'options']
    permission_classes = [IsAuthenticated, IsAnalyticsUser]

    def get(self, request):
        labor_hours_by_tech = dict(
            MaintenanceExecution.objects.values('executed_by').annotate(
                total=Sum('actual_labor_hours')
            ).values_list('executed_by', 'total')
        )

        techs = User.objects.filter(role=User.Role.FIELD_TECHNICIAN).annotate(
            assigned_wo_count=Count('assigned_work_orders', distinct=True),
            completed_wo_count=Count(
                'assigned_work_orders',
                filter=Q(assigned_work_orders__status=WorkOrderStatus.COMPLETED),
                distinct=True
            ),
            executions_count=Count('assigned_executions', distinct=True),
            pending_tasks_count=Count(
                'assigned_maintenance_schedules__tasks',
                filter=Q(assigned_maintenance_schedules__tasks__status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
                distinct=True
            ),
            completed_tasks_count=Count(
                'assigned_maintenance_schedules__tasks',
                filter=Q(assigned_maintenance_schedules__tasks__status=TaskStatus.COMPLETED),
                distinct=True
            ),
        ).order_by('username')

        performance_data = []
        for tech in techs:
            full_name = f"{tech.first_name} {tech.last_name}".strip() or tech.username
            performance_data.append({
                'technician_id': tech.id,
                'technician_name': full_name,
                'username': tech.username,
                'assigned_work_orders': tech.assigned_wo_count,
                'completed_work_orders': tech.completed_wo_count,
                'maintenance_executions': tech.executions_count,
                'total_actual_labor_hours': str(labor_hours_by_tech.get(tech.id, Decimal('0.00'))),
                'pending_tasks': tech.pending_tasks_count,
                'completed_tasks': tech.completed_tasks_count,
            })

        payload = {
            'total_technicians': len(performance_data),
            'technicians': performance_data,
        }

        return Response(payload, status=status.HTTP_200_OK)

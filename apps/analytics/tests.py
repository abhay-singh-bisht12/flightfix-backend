"""
Comprehensive automated tests for FlightFix Analytics & Reporting module.
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.aircraft.models import Aircraft, AircraftStatus
from apps.compliance.models import (
    ComplianceRecord,
    ComplianceRequirement,
    RegulationType,
    RequirementPriority,
    RequirementStatus,
    VerificationStatus,
)
from apps.inventory.models import (
    InventoryTransaction,
    PartCategory,
    SparePart,
    StockStatus,
    TransactionType,
)
from apps.maintenance_execution.models import (
    ExecutionStatus,
    MaintenanceExecution,
)
from apps.maintenance_planning.models import (
    MaintenancePriority,
    MaintenanceSchedule,
    MaintenanceStatus,
    MaintenanceType,
    MaintenanceTask,
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
    WorkOrderType,
)

User = get_user_model()


class AnalyticsBaseTestCase(APITestCase):
    """
    Base test fixture initializing users, roles, aircraft, maintenance,
    inventory, compliance, and supply chain data using setUpTestData for speed.
    """
    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.now().date()

        # 1. Users
        cls.admin_user = User.objects.create_user(
            username='analytics_admin',
            email='analytics_admin@flightfix.com',
            password='Password123!',
            first_name='Admin',
            last_name='Director',
            role=User.Role.ADMIN,
        )
        cls.safety_user = User.objects.create_user(
            username='analytics_safety',
            email='analytics_safety@flightfix.com',
            password='Password123!',
            first_name='Sarah',
            last_name='Safety',
            role=User.Role.SAFETY_OFFICER,
        )
        cls.contracts_user = User.objects.create_user(
            username='analytics_contracts',
            email='analytics_contracts@flightfix.com',
            password='Password123!',
            first_name='Connie',
            last_name='Contracts',
            role=User.Role.CONTRACTS_MANAGER,
        )
        cls.tech_user = User.objects.create_user(
            username='analytics_tech',
            email='analytics_tech@flightfix.com',
            password='Password123!',
            first_name='Tim',
            last_name='Tech',
            role=User.Role.FIELD_TECHNICIAN,
        )

        # 2. Aircraft
        cls.aircraft_1 = Aircraft.objects.create(
            registration_number='N101AN',
            aircraft_type='Commercial Jet',
            model='Boeing 737-800',
            manufacturer='Boeing',
            serial_number='SN-BOE-101',
            status=AircraftStatus.ACTIVE,
        )
        cls.aircraft_2 = Aircraft.objects.create(
            registration_number='N202AN',
            aircraft_type='Regional Jet',
            model='Airbus A320neo',
            manufacturer='Airbus',
            serial_number='SN-AIR-202',
            status=AircraftStatus.MAINTENANCE,
        )

        # 3. Maintenance Schedules
        cls.sched_completed = MaintenanceSchedule.objects.create(
            aircraft=cls.aircraft_1,
            title='500-Hour Inspection',
            description='Periodic inspection',
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.HIGH,
            planned_date=cls.today - timezone.timedelta(days=15),
            due_date=cls.today - timezone.timedelta(days=10),
            status=MaintenanceStatus.COMPLETED,
            assigned_to=cls.tech_user,
            created_by=cls.admin_user,
        )
        cls.sched_in_progress = MaintenanceSchedule.objects.create(
            aircraft=cls.aircraft_2,
            title='Avionics Calibration',
            description='Transponder test',
            maintenance_type=MaintenanceType.INSPECTION,
            priority=MaintenancePriority.CRITICAL,
            planned_date=cls.today - timezone.timedelta(days=2),
            due_date=cls.today + timezone.timedelta(days=5),
            status=MaintenanceStatus.IN_PROGRESS,
            assigned_to=cls.tech_user,
            created_by=cls.admin_user,
        )
        cls.sched_overdue = MaintenanceSchedule.objects.create(
            aircraft=cls.aircraft_1,
            title='Hydraulic Valve Check',
            description='Overdue valve inspection',
            maintenance_type=MaintenanceType.CORRECTIVE,
            priority=MaintenancePriority.MEDIUM,
            planned_date=cls.today - timezone.timedelta(days=20),
            due_date=cls.today - timezone.timedelta(days=3),
            status=MaintenanceStatus.PLANNED,
            assigned_to=cls.tech_user,
            created_by=cls.admin_user,
        )

        # 4. Tasks
        cls.task_1 = MaintenanceTask.objects.create(
            schedule=cls.sched_completed,
            task_name='Replace O-Rings',
            status=TaskStatus.COMPLETED,
            estimated_hours=Decimal('3.00'),
        )
        cls.task_2 = MaintenanceTask.objects.create(
            schedule=cls.sched_in_progress,
            task_name='Tune Transceiver',
            status=TaskStatus.PENDING,
            estimated_hours=Decimal('4.00'),
        )

        # 5. Work Orders
        cls.wo_completed = WorkOrder.objects.create(
            work_order_number='WO-AN-0001',
            aircraft=cls.aircraft_1,
            maintenance_schedule=cls.sched_completed,
            title='Actuator Seal Replacement',
            description='Replace all seals',
            work_order_type=WorkOrderType.PREVENTIVE,
            priority=WorkOrderPriority.HIGH,
            status=WorkOrderStatus.COMPLETED,
            assigned_to=cls.tech_user,
            created_by=cls.admin_user,
            planned_start_date=cls.today - timezone.timedelta(days=15),
            actual_start_date=cls.today - timezone.timedelta(days=15),
            actual_completion_date=cls.today - timezone.timedelta(days=10),
            actual_hours=Decimal('6.00'),
        )
        cls.wo_in_progress = WorkOrder.objects.create(
            work_order_number='WO-AN-0002',
            aircraft=cls.aircraft_2,
            maintenance_schedule=cls.sched_in_progress,
            title='Radar Alignment',
            description='Calibrate weather radar',
            work_order_type=WorkOrderType.INSPECTION,
            priority=WorkOrderPriority.CRITICAL,
            status=WorkOrderStatus.IN_PROGRESS,
            assigned_to=cls.tech_user,
            created_by=cls.admin_user,
            planned_start_date=cls.today - timezone.timedelta(days=2),
            actual_start_date=cls.today - timezone.timedelta(days=2),
        )

        # 6. Maintenance Executions
        cls.exec_1 = MaintenanceExecution.objects.create(
            work_order=cls.wo_completed,
            maintenance_task=cls.task_1,
            aircraft=cls.aircraft_1,
            executed_by=cls.tech_user,
            status=ExecutionStatus.COMPLETED,
            actual_labor_hours=Decimal('6.00'),
            work_performed='O-rings replaced and torqued.',
            created_by=cls.tech_user,
            started_at=timezone.now() - timezone.timedelta(days=12),
        )

        # 7. Spare Parts & Transactions
        cls.part_in_stock = SparePart.objects.create(
            part_number='PN-AN-HYD-01',
            name='Hydraulic O-Ring Kit',
            category=PartCategory.HYDRAULICS,
            manufacturer='Parker Aerospace',
            quantity_in_stock=50,
            minimum_stock_level=10,
            unit_price=Decimal('100.00'),
            location='Hangar-1 / Shelf-A01',
            status=StockStatus.IN_STOCK,
        )
        cls.part_low_stock = SparePart.objects.create(
            part_number='PN-AN-ENG-02',
            name='Fuel Filter Element',
            category=PartCategory.ENGINE,
            manufacturer='Pall Aerospace',
            quantity_in_stock=3,
            minimum_stock_level=5,
            unit_price=Decimal('250.00'),
            location='Hangar-2 / Bin-B02',
            status=StockStatus.LOW_STOCK,
        )
        cls.part_out_of_stock = SparePart.objects.create(
            part_number='PN-AN-AV-03',
            name='Radar Transceiver Diode',
            category=PartCategory.AVIONICS,
            manufacturer='Honeywell',
            quantity_in_stock=0,
            minimum_stock_level=2,
            unit_price=Decimal('75.00'),
            location='Hangar-1 / Bin-C03',
            status=StockStatus.OUT_OF_STOCK,
        )

        cls.tx_issue = InventoryTransaction.objects.create(
            spare_part=cls.part_in_stock,
            transaction_type=TransactionType.ISSUE,
            quantity=10,
            reference='WO-AN-0001',
            performed_by=cls.tech_user,
        )
        cls.tx_receipt = InventoryTransaction.objects.create(
            spare_part=cls.part_in_stock,
            transaction_type=TransactionType.RECEIPT,
            quantity=20,
            reference='PO-AN-0001',
            performed_by=cls.admin_user,
        )

        # 8. Compliance
        cls.req_compliant = ComplianceRequirement.objects.create(
            requirement_code='AD-2026-AN-01',
            title='Hydraulic Seal Directive',
            description='Mandatory seal check',
            regulation_type=RegulationType.AIRWORTHINESS_DIRECTIVE,
            issuing_authority='FAA',
            aircraft=cls.aircraft_1,
            effective_date=cls.today - timezone.timedelta(days=30),
            due_date=cls.today + timezone.timedelta(days=30),
            status=RequirementStatus.COMPLIANT,
            priority=RequirementPriority.CRITICAL,
            created_by=cls.safety_user,
        )
        cls.req_non_compliant = ComplianceRequirement.objects.create(
            requirement_code='SB-2026-AN-02',
            title='Radar Calibration SB',
            description='Radar pulse test',
            regulation_type=RegulationType.SERVICE_BULLETIN,
            issuing_authority='Airbus',
            aircraft=cls.aircraft_2,
            effective_date=cls.today - timezone.timedelta(days=40),
            due_date=cls.today + timezone.timedelta(days=15),
            status=RequirementStatus.NON_COMPLIANT,
            priority=RequirementPriority.HIGH,
            created_by=cls.safety_user,
        )
        cls.req_expired = ComplianceRequirement.objects.create(
            requirement_code='SB-2026-AN-03',
            title='Overdue Inspection Directive',
            description='Expired directive check',
            regulation_type=RegulationType.INSPECTION_REQUIREMENT,
            issuing_authority='FAA',
            aircraft=cls.aircraft_2,
            effective_date=cls.today - timezone.timedelta(days=60),
            due_date=cls.today - timezone.timedelta(days=10),
            status=RequirementStatus.OPEN,
            priority=RequirementPriority.MEDIUM,
            created_by=cls.safety_user,
        )
        cls.req_open = ComplianceRequirement.objects.create(
            requirement_code='INSP-2026-AN-04',
            title='Cabin Pressure Seal Mandate',
            description='Ongoing inspection check',
            regulation_type=RegulationType.SAFETY_REQUIREMENT,
            issuing_authority='FAA',
            aircraft=cls.aircraft_1,
            effective_date=cls.today - timezone.timedelta(days=5),
            due_date=cls.today + timezone.timedelta(days=25),
            status=RequirementStatus.OPEN,
            priority=RequirementPriority.LOW,
            created_by=cls.safety_user,
        )
        cls.rec_verified = ComplianceRecord.objects.create(
            requirement=cls.req_compliant,
            aircraft=cls.aircraft_1,
            maintenance_execution=cls.exec_1,
            verification_status=VerificationStatus.VERIFIED,
            verified_by=cls.safety_user,
            evidence_reference='CRS-AN-001',
        )

        # 9. Supply Chain & Purchase Orders
        cls.supplier_active = Supplier.objects.create(
            supplier_code='SUPP-AN-PARKER',
            name='Parker Supply Corp',
            status=SupplierStatus.ACTIVE,
            supplier_type=SupplierType.OEM,
        )
        cls.po_approved = PurchaseOrder.objects.create(
            po_number='PO-AN-0001',
            supplier=cls.supplier_active,
            order_date=cls.today,
            expected_delivery_date=cls.today + timezone.timedelta(days=14),
            status=PurchaseOrderStatus.APPROVED,
            priority=PurchaseOrderPriority.HIGH,
            created_by=cls.contracts_user,
            approved_by=cls.admin_user,
            approved_at=timezone.now(),
        )
        cls.po_item_1 = PurchaseOrderItem.objects.create(
            purchase_order=cls.po_approved,
            spare_part=cls.part_in_stock,
            quantity_ordered=10,
            unit_price=Decimal('100.00'),
        )

        cls.po_received = PurchaseOrder.objects.create(
            po_number='PO-AN-0002',
            supplier=cls.supplier_active,
            order_date=cls.today - timezone.timedelta(days=30),
            expected_delivery_date=cls.today - timezone.timedelta(days=15),
            actual_delivery_date=cls.today - timezone.timedelta(days=14),
            status=PurchaseOrderStatus.RECEIVED,
            priority=PurchaseOrderPriority.MEDIUM,
            created_by=cls.contracts_user,
        )
        cls.po_item_2 = PurchaseOrderItem.objects.create(
            purchase_order=cls.po_received,
            spare_part=cls.part_low_stock,
            quantity_ordered=5,
            unit_price=Decimal('200.00'),
        )

    def setUp(self):
        # Generate fresh tokens for authorization
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        self.safety_token = str(RefreshToken.for_user(self.safety_user).access_token)
        self.contracts_token = str(RefreshToken.for_user(self.contracts_user).access_token)
        self.tech_token = str(RefreshToken.for_user(self.tech_user).access_token)

    def auth_as(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def unauth(self):
        self.client.credentials()


class AnalyticsAuthenticationAndRoleTests(AnalyticsBaseTestCase):
    """
    Validates RBAC on analytics endpoints:
    - 401 for unauthenticated
    - 403 for FIELD_TECHNICIAN
    - 200 for ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER
    """
    ENDPOINTS = [
        '/api/analytics/dashboard/',
        '/api/analytics/maintenance-summary/',
        '/api/analytics/aircraft-summary/',
        '/api/analytics/inventory-summary/',
        '/api/analytics/compliance-summary/',
        '/api/analytics/supply-chain-summary/',
        '/api/analytics/technician-performance/',
    ]

    def test_unauthenticated_requests_return_401(self):
        self.unauth()
        for endpoint in self.ENDPOINTS:
            response = self.client.get(endpoint)
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Expected 401 for unauthenticated GET {endpoint}"
            )

    def test_field_technician_rejected_403(self):
        self.auth_as(self.tech_token)
        for endpoint in self.ENDPOINTS:
            response = self.client.get(endpoint)
            self.assertEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                f"Expected 403 for FIELD_TECHNICIAN on GET {endpoint}"
            )

    def test_admin_access_all_endpoints_200(self):
        self.auth_as(self.admin_token)
        for endpoint in self.ENDPOINTS:
            response = self.client.get(endpoint)
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"Expected 200 for ADMIN on GET {endpoint}"
            )

    def test_safety_officer_access_200(self):
        self.auth_as(self.safety_token)
        for endpoint in self.ENDPOINTS:
            response = self.client.get(endpoint)
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"Expected 200 for SAFETY_OFFICER on GET {endpoint}"
            )

    def test_contracts_manager_access_200(self):
        self.auth_as(self.contracts_token)
        for endpoint in self.ENDPOINTS:
            response = self.client.get(endpoint)
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"Expected 200 for CONTRACTS_MANAGER on GET {endpoint}"
            )


class AnalyticsDashboardTests(AnalyticsBaseTestCase):
    """
    Validates management dashboard metrics and count accuracy.
    """
    def test_dashboard_response_structure(self):
        self.auth_as(self.admin_token)
        response = self.client.get('/api/analytics/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        expected_keys = [
            'total_aircraft',
            'active_aircraft',
            'total_maintenance_schedules',
            'pending_maintenance_schedules',
            'overdue_maintenance_schedules',
            'completed_maintenance_schedules',
            'total_work_orders',
            'open_work_orders',
            'open_in_progress_work_orders',
            'completed_work_orders',
            'total_maintenance_executions',
            'total_spare_parts',
            'low_stock_spare_parts',
            'out_of_stock_spare_parts',
            'open_compliance_requirements',
            'non_compliant_requirements',
            'expired_requirements',
            'total_suppliers',
            'active_suppliers',
            'purchase_orders_by_status',
        ]
        for key in expected_keys:
            self.assertIn(key, data, f"Missing key '{key}' in dashboard response")

    def test_dashboard_count_accuracy(self):
        self.auth_as(self.admin_token)
        response = self.client.get('/api/analytics/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertEqual(data['total_aircraft'], 2)
        self.assertEqual(data['active_aircraft'], 1)
        self.assertEqual(data['total_maintenance_schedules'], 3)
        self.assertEqual(data['pending_maintenance_schedules'], 2)  # 1 in progress + 1 planned
        self.assertEqual(data['overdue_maintenance_schedules'], 1)  # sched_overdue
        self.assertEqual(data['completed_maintenance_schedules'], 1)
        self.assertEqual(data['total_work_orders'], 2)
        self.assertEqual(data['completed_work_orders'], 1)
        self.assertEqual(data['open_work_orders'], 1)
        self.assertEqual(data['total_maintenance_executions'], 1)
        self.assertEqual(data['total_spare_parts'], 3)
        self.assertEqual(data['low_stock_spare_parts'], 1)
        self.assertEqual(data['out_of_stock_spare_parts'], 1)
        self.assertEqual(data['total_suppliers'], 1)
        self.assertEqual(data['active_suppliers'], 1)
        self.assertEqual(data['open_compliance_requirements'], 1)
        self.assertEqual(data['non_compliant_requirements'], 1)
        self.assertEqual(data['expired_requirements'], 1)
        self.assertIn('APPROVED', data['purchase_orders_by_status'])
        self.assertEqual(data['purchase_orders_by_status']['APPROVED'], 1)
        self.assertEqual(data['purchase_orders_by_status']['RECEIVED'], 1)


class AnalyticsMaintenanceSummaryTests(AnalyticsBaseTestCase):
    """
    Validates maintenance KPIs and date range filtering.
    """
    def test_maintenance_summary_structure_and_counts(self):
        self.auth_as(self.admin_token)
        response = self.client.get('/api/analytics/maintenance-summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertIn('schedules_by_status', data)
        self.assertIn('schedules_by_maintenance_type', data)
        self.assertIn('schedules_by_priority', data)
        self.assertIn('work_orders_by_status', data)
        self.assertIn('work_orders_by_priority', data)
        self.assertIn('executions_by_status', data)
        self.assertIn('completed_vs_pending_maintenance', data)
        self.assertIn('overdue_maintenance_count', data)
        self.assertEqual(data['overdue_maintenance_count'], 1)

    def test_maintenance_summary_date_filtering(self):
        self.auth_as(self.admin_token)
        # Filter for recent 5 days
        start = str(self.today - timezone.timedelta(days=5))
        end = str(self.today + timezone.timedelta(days=10))
        response = self.client.get(f'/api/analytics/maintenance-summary/?start_date={start}&end_date={end}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['date_filter']['start_date'], start)
        self.assertEqual(data['date_filter']['end_date'], end)
        # Sched 1 was 15 days ago, so only sched_in_progress (2 days ago) is in range
        self.assertEqual(data['completed_vs_pending_maintenance']['pending_schedules'], 1)

    def test_invalid_start_date_format_400(self):
        self.auth_as(self.admin_token)
        response = self.client.get('/api/analytics/maintenance-summary/?start_date=invalid-date')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start_date', response.data)

    def test_invalid_end_date_format_400(self):
        self.auth_as(self.admin_token)
        response = self.client.get('/api/analytics/maintenance-summary/?end_date=2026-13-45')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('end_date', response.data)

    def test_start_date_after_end_date_400(self):
        self.auth_as(self.admin_token)
        response = self.client.get('/api/analytics/maintenance-summary/?start_date=2026-12-01&end_date=2026-11-01')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start_date', response.data)


class AnalyticsAircraftSummaryTests(AnalyticsBaseTestCase):
    """
    Validates aircraft fleet analytics and per-aircraft maintenance activity.
    """
    def test_aircraft_summary_counts_and_activity(self):
        self.auth_as(self.admin_token)
        response = self.client.get('/api/analytics/aircraft-summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertIn('aircraft_count_by_status', data)
        self.assertEqual(data['aircraft_count_by_status']['ACTIVE'], 1)
        self.assertEqual(data['aircraft_count_by_status']['MAINTENANCE'], 1)

        self.assertIn('maintenance_activity_per_aircraft', data)
        self.assertGreaterEqual(len(data['maintenance_activity_per_aircraft']), 2)

        self.assertIn('work_order_count_per_aircraft', data)
        self.assertEqual(data['work_order_count_per_aircraft']['N101AN'], 1)
        self.assertEqual(data['work_order_count_per_aircraft']['N202AN'], 1)

    def test_aircraft_summary_manufacturer_and_type_distribution(self):
        self.auth_as(self.safety_token)
        response = self.client.get('/api/analytics/aircraft-summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertIn('aircraft_count_by_aircraft_type', data)
        self.assertEqual(data['aircraft_count_by_aircraft_type']['Commercial Jet'], 1)
        self.assertEqual(data['aircraft_count_by_aircraft_type']['Regional Jet'], 1)

        self.assertIn('aircraft_count_by_manufacturer', data)
        self.assertEqual(data['aircraft_count_by_manufacturer']['Boeing'], 1)
        self.assertEqual(data['aircraft_count_by_manufacturer']['Airbus'], 1)


class AnalyticsInventorySummaryTests(AnalyticsBaseTestCase):
    """
    Validates inventory stock levels and transaction analytics.
    """
    def test_inventory_summary_counts(self):
        self.auth_as(self.admin_token)
        response = self.client.get('/api/analytics/inventory-summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertEqual(data['total_spare_parts'], 3)
        self.assertEqual(data['in_stock_count'], 1)
        self.assertEqual(data['low_stock_count'], 1)
        self.assertEqual(data['out_of_stock_count'], 1)

    def test_inventory_summary_low_stock_and_transactions(self):
        self.auth_as(self.contracts_token)
        response = self.client.get('/api/analytics/inventory-summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertIn('inventory_transactions_by_type', data)
        self.assertEqual(data['inventory_transactions_by_type']['ISSUE'], 1)
        self.assertEqual(data['inventory_transactions_by_type']['RECEIPT'], 1)

        self.assertIn('most_frequently_issued_parts', data)
        self.assertEqual(len(data['most_frequently_issued_parts']), 1)
        self.assertEqual(data['most_frequently_issued_parts'][0]['part_number'], 'PN-AN-HYD-01')

        self.assertIn('parts_with_low_stock', data)
        self.assertGreaterEqual(len(data['parts_with_low_stock']), 2)


class AnalyticsComplianceSummaryTests(AnalyticsBaseTestCase):
    """
    Validates regulatory compliance breakdown and audit statistics.
    """
    def test_compliance_summary_metrics(self):
        self.auth_as(self.admin_token)
        response = self.client.get('/api/analytics/compliance-summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertIn('requirements_by_status', data)
        self.assertEqual(data['requirements_by_status']['COMPLIANT'], 1)
        self.assertEqual(data['requirements_by_status']['NON_COMPLIANT'], 1)
        self.assertEqual(data['requirements_by_status']['OPEN'], 1)
        self.assertEqual(data['requirements_by_status']['EXPIRED'], 1)

        self.assertEqual(data['overdue_expired_compliance_requirements'], 1)

        self.assertIn('compliant_vs_non_compliant_counts', data)
        self.assertEqual(data['compliant_vs_non_compliant_counts']['compliant'], 1)
        self.assertEqual(data['compliant_vs_non_compliant_counts']['non_compliant'], 1)
        self.assertEqual(data['compliant_vs_non_compliant_counts']['open_or_in_progress'], 1)
        self.assertEqual(data['compliant_vs_non_compliant_counts']['expired'], 1)

    def test_compliance_summary_regulation_and_priority_distribution(self):
        self.auth_as(self.safety_token)
        response = self.client.get('/api/analytics/compliance-summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertIn('requirements_by_priority', data)
        self.assertIn('CRITICAL', data['requirements_by_priority'])
        self.assertIn('HIGH', data['requirements_by_priority'])

        self.assertIn('requirements_by_regulation_type', data)
        self.assertIn('AIRWORTHINESS_DIRECTIVE', data['requirements_by_regulation_type'])
        self.assertIn('SERVICE_BULLETIN', data['requirements_by_regulation_type'])

        self.assertIn('compliance_records_by_verification_status', data)
        self.assertEqual(data['compliance_records_by_verification_status']['VERIFIED'], 1)


class AnalyticsSupplyChainSummaryTests(AnalyticsBaseTestCase):
    """
    Validates supply chain KPIs, PO values, and delivery progress.
    """
    def test_supply_chain_summary_metrics(self):
        self.auth_as(self.admin_token)
        response = self.client.get('/api/analytics/supply-chain-summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertIn('suppliers_by_status', data)
        self.assertEqual(data['suppliers_by_status']['ACTIVE'], 1)

        self.assertIn('purchase_orders_by_status', data)
        self.assertEqual(data['purchase_orders_by_status']['APPROVED'], 1)
        self.assertEqual(data['purchase_orders_by_status']['RECEIVED'], 1)

        # Total PO Value: (10 * 100) + (5 * 200) = 1000 + 1000 = 2000.00
        self.assertIn('total_purchase_order_value', data)
        self.assertEqual(Decimal(data['total_purchase_order_value']), Decimal('2000.00'))

    def test_supply_chain_summary_pending_and_received_deliveries(self):
        self.auth_as(self.contracts_token)
        response = self.client.get('/api/analytics/supply-chain-summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertIn('pending_deliveries', data)
        self.assertEqual(data['pending_deliveries'], 1)  # po_approved
        self.assertEqual(data['received_purchase_orders'], 1)  # po_received


class AnalyticsTechnicianPerformanceTests(AnalyticsBaseTestCase):
    """
    Validates technician operational performance reporting and ensures
    sensitive personal authentication data is omitted.
    """
    def test_technician_performance_metrics(self):
        self.auth_as(self.admin_token)
        response = self.client.get('/api/analytics/technician-performance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertIn('total_technicians', data)
        self.assertGreaterEqual(data['total_technicians'], 1)
        self.assertIn('technicians', data)

        tech_row = next((t for t in data['technicians'] if t['username'] == 'analytics_tech'), None)
        self.assertIsNotNone(tech_row)

        self.assertEqual(tech_row['technician_name'], 'Tim Tech')
        self.assertEqual(tech_row['assigned_work_orders'], 2)
        self.assertEqual(tech_row['completed_work_orders'], 1)
        self.assertEqual(tech_row['maintenance_executions'], 1)
        self.assertEqual(Decimal(tech_row['total_actual_labor_hours']), Decimal('6.00'))
        self.assertEqual(tech_row['pending_tasks'], 1)  # task_2 (PENDING)
        self.assertEqual(tech_row['completed_tasks'], 1)  # task_1 (COMPLETED)

    def test_technician_performance_sensitive_data_not_exposed(self):
        self.auth_as(self.safety_token)
        response = self.client.get('/api/analytics/technician-performance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        tech_row = next((t for t in data['technicians'] if t['username'] == 'analytics_tech'), None)
        self.assertIsNotNone(tech_row)

        self.assertNotIn('password', tech_row)
        self.assertNotIn('email', tech_row)
        self.assertNotIn('phone', tech_row)
        self.assertNotIn('token', tech_row)


class AnalyticsMethodRestrictionsTests(AnalyticsBaseTestCase):
    """
    Ensures analytics APIs are strictly READ-ONLY:
    POST, PUT, PATCH, DELETE must return 405 Method Not Allowed.
    """
    ENDPOINTS = [
        '/api/analytics/dashboard/',
        '/api/analytics/maintenance-summary/',
        '/api/analytics/aircraft-summary/',
        '/api/analytics/inventory-summary/',
        '/api/analytics/compliance-summary/',
        '/api/analytics/supply-chain-summary/',
        '/api/analytics/technician-performance/',
    ]

    def test_post_rejected_405(self):
        self.auth_as(self.admin_token)
        for url in self.ENDPOINTS:
            res = self.client.post(url, {'test': 'data'}, format='json')
            self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, f"POST {url} should be 405")

    def test_put_rejected_405(self):
        self.auth_as(self.admin_token)
        for url in self.ENDPOINTS:
            res = self.client.put(url, {'test': 'data'}, format='json')
            self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, f"PUT {url} should be 405")

    def test_patch_rejected_405(self):
        self.auth_as(self.admin_token)
        for url in self.ENDPOINTS:
            res = self.client.patch(url, {'test': 'data'}, format='json')
            self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, f"PATCH {url} should be 405")

    def test_delete_rejected_405(self):
        self.auth_as(self.admin_token)
        for url in self.ENDPOINTS:
            res = self.client.delete(url)
            self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, f"DELETE {url} should be 405")

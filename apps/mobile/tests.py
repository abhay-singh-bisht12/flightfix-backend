"""
Comprehensive automated tests for FlightFix Mobile / Field Technician Support module.
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
from apps.inventory.models import PartCategory, SparePart, StockStatus
from apps.maintenance_execution.models import ExecutionStatus, MaintenanceExecution
from apps.maintenance_planning.models import (
    MaintenancePriority,
    MaintenanceSchedule,
    MaintenanceStatus,
    MaintenanceTask,
    MaintenanceType,
    TaskStatus,
)
from apps.work_orders.models import (
    WorkOrder,
    WorkOrderPriority,
    WorkOrderStatus,
    WorkOrderType,
)

User = get_user_model()


class BaseMobileAPITestCase(APITestCase):
    """
    Base test fixture initializing users, roles, aircraft, schedules, tasks,
    work orders, executions, compliance records, and inventory parts.
    """
    def setUp(self):
        self.today = timezone.now().date()

        # 1. Users with distinct RBAC roles
        self.tech1 = User.objects.create_user(
            username='tech_alex',
            email='tech_alex@flightfix.com',
            password='Password123!',
            first_name='Alex',
            last_name='Rivera',
            role=User.Role.FIELD_TECHNICIAN,
        )
        self.tech2 = User.objects.create_user(
            username='tech_jordan',
            email='tech_jordan@flightfix.com',
            password='Password123!',
            first_name='Jordan',
            last_name='Lee',
            role=User.Role.FIELD_TECHNICIAN,
        )
        self.admin_user = User.objects.create_user(
            username='admin_boss',
            email='admin_boss@flightfix.com',
            password='Password123!',
            first_name='Admin',
            last_name='Boss',
            role=User.Role.ADMIN,
        )
        self.safety_user = User.objects.create_user(
            username='safety_sarah',
            email='safety_sarah@flightfix.com',
            password='Password123!',
            first_name='Sarah',
            last_name='Connor',
            role=User.Role.SAFETY_OFFICER,
        )
        self.contracts_user = User.objects.create_user(
            username='contracts_clark',
            email='contracts_clark@flightfix.com',
            password='Password123!',
            first_name='Clark',
            last_name='Kent',
            role=User.Role.CONTRACTS_MANAGER,
        )

        # JWT Tokens
        self.tech1_token = str(RefreshToken.for_user(self.tech1).access_token)
        self.tech2_token = str(RefreshToken.for_user(self.tech2).access_token)
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        self.safety_token = str(RefreshToken.for_user(self.safety_user).access_token)
        self.contracts_token = str(RefreshToken.for_user(self.contracts_user).access_token)

        # 2. Aircraft
        self.aircraft1 = Aircraft.objects.create(
            registration_number='N101FF',
            aircraft_type='Commercial Passenger',
            model='Boeing 737-800',
            manufacturer='Boeing',
            serial_number='SN-737-101',
            status=AircraftStatus.MAINTENANCE,
        )
        self.aircraft2 = Aircraft.objects.create(
            registration_number='N202FF',
            aircraft_type='Regional Jet',
            model='Airbus A320neo',
            manufacturer='Airbus',
            serial_number='SN-320-202',
            status=AircraftStatus.ACTIVE,
        )
        self.unrelated_aircraft = Aircraft.objects.create(
            registration_number='N999XX',
            aircraft_type='Cargo Transport',
            model='Boeing 777F',
            manufacturer='Boeing',
            serial_number='SN-777-999',
            status=AircraftStatus.GROUNDED,
        )

        # 3. Maintenance Schedules
        self.sched1 = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft1,
            title='737 500-Hour Inspection',
            description='Periodic hydraulic and wing inspection',
            maintenance_type=MaintenanceType.INSPECTION,
            priority=MaintenancePriority.HIGH,
            planned_date=self.today,
            due_date=self.today + timezone.timedelta(days=7),
            status=MaintenanceStatus.IN_PROGRESS,
            assigned_to=self.tech1,
            created_by=self.admin_user,
        )
        self.sched2 = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft2,
            title='A320 Avionics Calibration',
            description='ADSB and radar checks',
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.MEDIUM,
            planned_date=self.today,
            due_date=self.today + timezone.timedelta(days=5),
            status=MaintenanceStatus.PLANNED,
            assigned_to=self.tech2,
            created_by=self.admin_user,
        )

        # 4. Maintenance Tasks
        self.task1 = MaintenanceTask.objects.create(
            schedule=self.sched1,
            task_name='Inspect Left Wing Actuators',
            description='Check hydraulic actuator seal integrity.',
            task_order=1,
            status=TaskStatus.IN_PROGRESS,
            estimated_hours=Decimal('3.50'),
        )
        self.task2 = MaintenanceTask.objects.create(
            schedule=self.sched1,
            task_name='Lubricate Flap Mechanisms',
            description='Grease trailing edge flap tracks.',
            task_order=2,
            status=TaskStatus.PENDING,
            estimated_hours=Decimal('2.00'),
        )
        self.task_other = MaintenanceTask.objects.create(
            schedule=self.sched2,
            task_name='Calibrate Weather Radar',
            description='Radar transceiver frequency tuning.',
            task_order=1,
            status=TaskStatus.PENDING,
            estimated_hours=Decimal('4.00'),
        )

        # 5. Work Orders
        self.wo1 = WorkOrder.objects.create(
            work_order_number='WO-2026-0001',
            aircraft=self.aircraft1,
            maintenance_schedule=self.sched1,
            title='Replace Hydraulic Actuator O-Rings',
            description='Perform teardown and resealing of primary actuator.',
            work_order_type=WorkOrderType.CORRECTIVE,
            priority=WorkOrderPriority.HIGH,
            status=WorkOrderStatus.IN_PROGRESS,
            assigned_to=self.tech1,
            created_by=self.admin_user,
            planned_start_date=self.today,
            planned_completion_date=self.today + timezone.timedelta(days=3),
            estimated_hours=Decimal('5.00'),
            actual_hours=Decimal('1.50'),
            findings='Minor fluid weepage on port B seals.',
            notes='Parts staged in bay 1.',
        )
        self.wo_other = WorkOrder.objects.create(
            work_order_number='WO-2026-0002',
            aircraft=self.aircraft2,
            maintenance_schedule=self.sched2,
            title='Avionics Transponder Test',
            description='Perform Mode S transponder alignment.',
            work_order_type=WorkOrderType.INSPECTION,
            priority=WorkOrderPriority.MEDIUM,
            status=WorkOrderStatus.ASSIGNED,
            assigned_to=self.tech2,
            created_by=self.admin_user,
            planned_start_date=self.today,
            planned_completion_date=self.today + timezone.timedelta(days=2),
            estimated_hours=Decimal('3.00'),
        )

        # 6. Maintenance Executions
        self.exec1 = MaintenanceExecution.objects.create(
            work_order=self.wo1,
            maintenance_task=self.task1,
            aircraft=self.aircraft1,
            executed_by=self.tech1,
            status=ExecutionStatus.IN_PROGRESS,
            started_at=timezone.now() - timezone.timedelta(hours=2),
            actual_labor_hours=Decimal('2.00'),
            work_performed='Removed hydraulic panel and disassembled actuator casing.',
            findings='O-ring hardening observed.',
            corrective_actions='Cleaned housing surfaces.',
            remarks='Awaiting replacement seals.',
            created_by=self.tech1,
        )
        self.exec_other = MaintenanceExecution.objects.create(
            work_order=self.wo_other,
            maintenance_task=self.task_other,
            aircraft=self.aircraft2,
            executed_by=self.tech2,
            status=ExecutionStatus.PENDING,
            actual_labor_hours=Decimal('0.00'),
            work_performed='Initial test rig hooked up.',
            created_by=self.tech2,
        )

        # 7. Compliance Requirements & Records
        self.req1 = ComplianceRequirement.objects.create(
            requirement_code='AD-2026-FAA-737-01',
            title='Hydraulic Actuator Seal Airworthiness Directive',
            description='Mandatory inspection and replacement of hydraulic seals.',
            regulation_type=RegulationType.AIRWORTHINESS_DIRECTIVE,
            issuing_authority='Federal Aviation Administration (FAA)',
            aircraft=self.aircraft1,
            effective_date=self.today - timezone.timedelta(days=30),
            due_date=self.today + timezone.timedelta(days=30),
            status=RequirementStatus.OPEN,
            priority=RequirementPriority.CRITICAL,
            created_by=self.safety_user,
        )
        self.rec1 = ComplianceRecord.objects.create(
            requirement=self.req1,
            aircraft=self.aircraft1,
            maintenance_execution=self.exec1,
            verification_status=VerificationStatus.PENDING,
            evidence_reference='CRS-2026-N101FF-01',
            findings='Physical verification in progress.',
        )

        self.req_other = ComplianceRequirement.objects.create(
            requirement_code='SB-2026-AIRBUS-320-09',
            title='A320 Flap Roller Bearing Service Bulletin',
            description='Inspection of roller bearing wear tolerances.',
            regulation_type=RegulationType.SERVICE_BULLETIN,
            issuing_authority='Airbus Industries',
            aircraft=self.aircraft2,
            effective_date=self.today - timezone.timedelta(days=60),
            due_date=self.today + timezone.timedelta(days=45),
            status=RequirementStatus.IN_PROGRESS,
            priority=RequirementPriority.HIGH,
            created_by=self.safety_user,
        )
        self.rec_other = ComplianceRecord.objects.create(
            requirement=self.req_other,
            aircraft=self.aircraft2,
            maintenance_execution=self.exec_other,
            verification_status=VerificationStatus.VERIFIED,
            verified_by=self.safety_user,
            verified_at=timezone.now(),
            evidence_reference='SB-LOG-320-884',
        )

        # 8. Spare Parts Inventory
        self.part1 = SparePart.objects.create(
            part_number='PN-MOB-SEAL-01',
            name='Hydraulic Actuator Viton Seal Kit',
            description='High-temp fluoroelastomer seal kit.',
            category=PartCategory.HYDRAULICS,
            manufacturer='Parker Aerospace',
            quantity_in_stock=25,
            minimum_stock_level=10,
            unit_price=Decimal('150.00'),
            location='Hangar-1 / Shelf-A02',
            status=StockStatus.IN_STOCK,
        )
        self.part2 = SparePart.objects.create(
            part_number='PN-MOB-FILTER-02',
            name='Fuel System 10-Micron Filter',
            description='Standard fuel strainer replacement.',
            category=PartCategory.ENGINE,
            manufacturer='Pall Aerospace',
            quantity_in_stock=2,
            minimum_stock_level=5,
            unit_price=Decimal('420.00'),
            location='Hangar-2 / Bin-C04',
            status=StockStatus.LOW_STOCK,
        )

    def auth_as(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def unauth(self):
        self.client.credentials()


class MobileAuthenticationAndRoleRestrictionTests(BaseMobileAPITestCase):
    """
    Validates authentication and role restrictions:
    - 401 Unauthorized for unauthenticated requests
    - 403 Forbidden for non-technician roles (ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER)
    - 200 OK for FIELD_TECHNICIAN
    """
    def test_unauthenticated_requests_rejected_401(self):
        self.unauth()
        endpoints = [
            '/api/mobile/dashboard/',
            '/api/mobile/my-tasks/',
            '/api/mobile/my-work-orders/',
            '/api/mobile/my-executions/',
            '/api/mobile/my-aircraft/',
            '/api/mobile/my-compliance/',
            '/api/mobile/available-parts/',
        ]
        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Expected 401 for unauthenticated GET {url}, got {response.status_code}"
            )

    def test_admin_user_forbidden_403(self):
        self.auth_as(self.admin_token)
        response = self.client.get('/api/mobile/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response_tasks = self.client.get('/api/mobile/my-tasks/')
        self.assertEqual(response_tasks.status_code, status.HTTP_403_FORBIDDEN)

    def test_safety_officer_forbidden_403(self):
        self.auth_as(self.safety_token)
        response = self.client.get('/api/mobile/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_contracts_manager_forbidden_403(self):
        self.auth_as(self.contracts_token)
        response = self.client.get('/api/mobile/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_technician_allowed_200(self):
        self.auth_as(self.tech1_token)
        response = self.client.get('/api/mobile/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TechnicianDashboardTests(BaseMobileAPITestCase):
    """
    Validates the compact mobile dashboard structure and accurate counts.
    """
    def test_dashboard_structure_and_technician_info(self):
        self.auth_as(self.tech1_token)
        response = self.client.get('/api/mobile/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertIn('technician', data)
        self.assertIn('summary', data)
        self.assertIn('assigned_aircraft', data)
        self.assertIn('tasks', data)
        self.assertIn('work_orders', data)
        self.assertIn('recent_executions', data)

        tech = data['technician']
        self.assertEqual(tech['username'], self.tech1.username)
        self.assertEqual(tech['name'], 'Alex Rivera')
        self.assertEqual(tech['role'], User.Role.FIELD_TECHNICIAN)

    def test_dashboard_summary_counts_accurate(self):
        self.auth_as(self.tech1_token)
        response = self.client.get('/api/mobile/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        summary = response.data['summary']

        self.assertEqual(summary['assigned_schedules'], 1)
        self.assertEqual(summary['pending_tasks'], 2)  # task1 (IN_PROGRESS) + task2 (PENDING)
        self.assertEqual(summary['open_work_orders'], 1)  # wo1 (IN_PROGRESS)
        self.assertEqual(summary['pending_compliance'], 1)  # rec1 (PENDING)

    def test_dashboard_scoped_to_assigned_work_only(self):
        self.auth_as(self.tech1_token)
        response = self.client.get('/api/mobile/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        # Aircraft should only include aircraft1, NOT aircraft2 or unrelated
        aircraft_regs = [a['registration_number'] for a in data['assigned_aircraft']]
        self.assertIn(self.aircraft1.registration_number, aircraft_regs)
        self.assertNotIn(self.aircraft2.registration_number, aircraft_regs)
        self.assertNotIn(self.unrelated_aircraft.registration_number, aircraft_regs)

        # Work orders should only include wo1
        wo_numbers = [w['work_order_number'] for w in data['work_orders']]
        self.assertIn(self.wo1.work_order_number, wo_numbers)
        self.assertNotIn(self.wo_other.work_order_number, wo_numbers)


class TechnicianMyTasksTests(BaseMobileAPITestCase):
    """
    Validates technician tasks listing, filtering, search, pagination, and IDOR protection.
    """
    def test_my_tasks_lists_only_assigned_tasks(self):
        self.auth_as(self.tech1_token)
        response = self.client.get('/api/mobile/my-tasks/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task_names = [t['task_name'] for t in response.data['results']]
        self.assertIn(self.task1.task_name, task_names)
        self.assertIn(self.task2.task_name, task_names)
        self.assertNotIn(self.task_other.task_name, task_names)

    def test_cannot_access_other_technician_task_idor_404(self):
        self.auth_as(self.tech1_token)
        response = self.client.get(f'/api/mobile/my-tasks/{self.task_other.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_tasks_by_status(self):
        self.auth_as(self.tech1_token)
        response = self.client.get(f'/api/mobile/my-tasks/?status={TaskStatus.PENDING}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task_names = [t['task_name'] for t in response.data['results']]
        self.assertIn(self.task2.task_name, task_names)
        self.assertNotIn(self.task1.task_name, task_names)

    def test_filter_tasks_by_dates(self):
        self.auth_as(self.tech1_token)
        response = self.client.get(f'/api/mobile/my-tasks/?planned_date={self.today}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)

    def test_search_tasks(self):
        self.auth_as(self.tech1_token)
        response = self.client.get('/api/mobile/my-tasks/?search=Actuator')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task_names = [t['task_name'] for t in response.data['results']]
        self.assertIn(self.task1.task_name, task_names)
        self.assertNotIn(self.task2.task_name, task_names)

    def test_ordering_and_pagination_tasks(self):
        self.auth_as(self.tech1_token)
        response = self.client.get('/api/mobile/my-tasks/?ordering=-task_order&page_size=1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['task_name'], self.task2.task_name)


class TechnicianMyWorkOrdersTests(BaseMobileAPITestCase):
    """
    Validates technician work orders listing, filtering, safe PATCH update,
    tamper-proofing protected fields, and IDOR prevention.
    """
    def test_my_work_orders_lists_only_assigned(self):
        self.auth_as(self.tech1_token)
        response = self.client.get('/api/mobile/my-work-orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        numbers = [w['work_order_number'] for w in response.data['results']]
        self.assertIn(self.wo1.work_order_number, numbers)
        self.assertNotIn(self.wo_other.work_order_number, numbers)

    def test_cannot_access_other_technician_work_order_idor_404(self):
        self.auth_as(self.tech1_token)
        response = self.client.get(f'/api/mobile/my-work-orders/{self.wo_other.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_and_search_work_orders(self):
        self.auth_as(self.tech1_token)
        # Filter by status
        response = self.client.get(f'/api/mobile/my-work-orders/?status={WorkOrderStatus.IN_PROGRESS}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

        # Filter by priority
        response_pri = self.client.get(f'/api/mobile/my-work-orders/?priority={WorkOrderPriority.HIGH}')
        self.assertEqual(response_pri.status_code, status.HTTP_200_OK)
        self.assertEqual(response_pri.data['count'], 1)

        # Search
        response_search = self.client.get('/api/mobile/my-work-orders/?search=Hydraulic')
        self.assertEqual(response_search.status_code, status.HTTP_200_OK)
        self.assertEqual(response_search.data['count'], 1)

    def test_patch_work_order_allowed_execution_fields(self):
        self.auth_as(self.tech1_token)
        payload = {
            'status': WorkOrderStatus.COMPLETED,
            'actual_hours': '4.50',
            'findings': 'All seals replaced with new Viton rings.',
            'corrective_action': 'Torqued casing bolts to 45 Nm.',
            'notes': 'Ready for QA verification.',
            'actual_start_date': str(self.today),
            'actual_completion_date': str(self.today),
        }
        response = self.client.patch(
            f'/api/mobile/my-work-orders/{self.wo1.id}/',
            payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.wo1.refresh_from_db()
        self.assertEqual(self.wo1.status, WorkOrderStatus.COMPLETED)
        self.assertEqual(self.wo1.actual_hours, Decimal('4.50'))
        self.assertEqual(self.wo1.findings, 'All seals replaced with new Viton rings.')

    def test_patch_work_order_protected_fields_rejected(self):
        self.auth_as(self.tech1_token)
        # Attempt to reassign technician
        response_reassign = self.client.patch(
            f'/api/mobile/my-work-orders/{self.wo1.id}/',
            {'assigned_to': self.tech2.id},
            format='json'
        )
        self.assertEqual(response_reassign.status_code, status.HTTP_400_BAD_REQUEST)

        # Attempt to change priority
        response_priority = self.client.patch(
            f'/api/mobile/my-work-orders/{self.wo1.id}/',
            {'priority': WorkOrderPriority.LOW},
            format='json'
        )
        self.assertEqual(response_priority.status_code, status.HTTP_400_BAD_REQUEST)

        # Attempt to reassign aircraft
        response_aircraft = self.client.patch(
            f'/api/mobile/my-work-orders/{self.wo1.id}/',
            {'aircraft': self.aircraft2.id},
            format='json'
        )
        self.assertEqual(response_aircraft.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_patch_other_technician_work_order_idor_404(self):
        self.auth_as(self.tech1_token)
        response = self.client.patch(
            f'/api/mobile/my-work-orders/{self.wo_other.id}/',
            {'status': WorkOrderStatus.IN_PROGRESS},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_http_methods_restriction(self):
        self.auth_as(self.tech1_token)
        # POST to work orders list should be 405 Method Not Allowed
        response_post = self.client.post('/api/mobile/my-work-orders/', {'title': 'New WO'}, format='json')
        self.assertEqual(response_post.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # DELETE should be 405
        response_delete = self.client.delete(f'/api/mobile/my-work-orders/{self.wo1.id}/')
        self.assertEqual(response_delete.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TechnicianExecutionsTests(BaseMobileAPITestCase):
    """
    Validates technician execution endpoints: GET, POST, PATCH, IDOR safeguards.
    """
    def test_my_executions_lists_only_technician_executions(self):
        self.auth_as(self.tech1_token)
        response = self.client.get('/api/mobile/my-executions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        exec_ids = [e['id'] for e in response.data['results']]
        self.assertIn(self.exec1.id, exec_ids)
        self.assertNotIn(self.exec_other.id, exec_ids)

    def test_cannot_access_other_technician_execution_idor_404(self):
        self.auth_as(self.tech1_token)
        response = self.client.get(f'/api/mobile/my-executions/{self.exec_other.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_execution_for_assigned_work_order_success(self):
        self.auth_as(self.tech1_token)
        payload = {
            'work_order': self.wo1.id,
            'maintenance_task': self.task2.id,
            'status': ExecutionStatus.IN_PROGRESS,
            'work_performed': 'Applied Aeroshell 22 grease to actuator slide mechanisms.',
            'actual_labor_hours': '1.50',
            'remarks': 'Slide mechanism moving freely.',
        }
        response = self.client.post('/api/mobile/my-executions/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_exec_id = response.data['id']
        created_exec = MaintenanceExecution.objects.get(id=new_exec_id)
        self.assertEqual(created_exec.executed_by, self.tech1)
        self.assertEqual(created_exec.aircraft, self.aircraft1)

    def test_create_execution_against_other_technician_work_order_rejected_idor(self):
        self.auth_as(self.tech1_token)
        payload = {
            'work_order': self.wo_other.id,  # Assigned to tech2!
            'work_performed': 'Attempting unauthorized execution log.',
            'actual_labor_hours': '1.00',
        }
        response = self.client.post('/api/mobile/my-executions/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('work_order', response.data)

    def test_patch_execution_fields_success(self):
        self.auth_as(self.tech1_token)
        payload = {
            'status': ExecutionStatus.COMPLETED,
            'actual_labor_hours': '3.75',
            'work_performed': 'Complete actuator overhaul finished and pressure tested.',
        }
        response = self.client.patch(
            f'/api/mobile/my-executions/{self.exec1.id}/',
            payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.exec1.refresh_from_db()
        self.assertEqual(self.exec1.status, ExecutionStatus.COMPLETED)
        self.assertEqual(self.exec1.actual_labor_hours, Decimal('3.75'))

    def test_cannot_patch_other_technician_execution_idor_404(self):
        self.auth_as(self.tech1_token)
        response = self.client.patch(
            f'/api/mobile/my-executions/{self.exec_other.id}/',
            {'status': ExecutionStatus.COMPLETED},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_execution_not_allowed_405(self):
        self.auth_as(self.tech1_token)
        response = self.client.delete(f'/api/mobile/my-executions/{self.exec1.id}/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TechnicianAircraftAndComplianceTests(BaseMobileAPITestCase):
    """
    Validates aircraft and compliance read-only endpoints scoped to technician assignments.
    """
    def test_my_aircraft_lists_only_relevant_aircraft(self):
        self.auth_as(self.tech1_token)
        response = self.client.get('/api/mobile/my-aircraft/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        regs = [a['registration_number'] for a in response.data['results']]
        self.assertIn(self.aircraft1.registration_number, regs)
        self.assertNotIn(self.aircraft2.registration_number, regs)
        self.assertNotIn(self.unrelated_aircraft.registration_number, regs)

    def test_cannot_access_unrelated_aircraft_idor_404(self):
        self.auth_as(self.tech1_token)
        response = self.client.get(f'/api/mobile/my-aircraft/{self.unrelated_aircraft.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_my_compliance_lists_only_relevant_records(self):
        self.auth_as(self.tech1_token)
        response = self.client.get('/api/mobile/my-compliance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        codes = [c['requirement_code'] for c in response.data['results']]
        self.assertIn(self.req1.requirement_code, codes)
        self.assertNotIn(self.req_other.requirement_code, codes)

    def test_cannot_access_unrelated_compliance_record_idor_404(self):
        self.auth_as(self.tech1_token)
        response = self.client.get(f'/api/mobile/my-compliance/{self.rec_other.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_technician_cannot_create_or_delete_compliance_405(self):
        self.auth_as(self.tech1_token)
        response_post = self.client.post('/api/mobile/my-compliance/', {'evidence_reference': 'TEST'}, format='json')
        self.assertEqual(response_post.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response_del = self.client.delete(f'/api/mobile/my-compliance/{self.rec1.id}/')
        self.assertEqual(response_del.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TechnicianAvailablePartsTests(BaseMobileAPITestCase):
    """
    Validates spare parts read-only inventory endpoint for technicians:
    - Lists parts with technical information
    - Strictly excludes sensitive vendor and unit pricing data
    - Disallows modifications (POST/PUT/PATCH/DELETE)
    """
    def test_technician_can_list_and_search_available_parts(self):
        self.auth_as(self.tech1_token)
        response = self.client.get('/api/mobile/available-parts/?search=Viton')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        part_data = response.data['results'][0]
        self.assertEqual(part_data['part_number'], self.part1.part_number)
        self.assertEqual(part_data['quantity_in_stock'], 25)

    def test_parts_response_excludes_cost_and_supplier_sensitive_data(self):
        self.auth_as(self.tech1_token)
        response = self.client.get(f'/api/mobile/available-parts/{self.part1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        # Operational fields present
        self.assertIn('part_number', data)
        self.assertIn('name', data)
        self.assertIn('category', data)
        self.assertIn('quantity_in_stock', data)
        self.assertIn('location', data)

        # Sensitive commercial / supplier fields must NOT be exposed
        self.assertNotIn('unit_price', data)
        self.assertNotIn('supplier', data)
        self.assertNotIn('minimum_stock_level', data)

    def test_technician_cannot_modify_parts_inventory_405(self):
        self.auth_as(self.tech1_token)
        # POST
        response_post = self.client.post(
            '/api/mobile/available-parts/',
            {'part_number': 'PN-HACK-01', 'name': 'Hacked Part'},
            format='json'
        )
        self.assertEqual(response_post.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # PATCH
        response_patch = self.client.patch(
            f'/api/mobile/available-parts/{self.part1.id}/',
            {'quantity_in_stock': 9999},
            format='json'
        )
        self.assertEqual(response_patch.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # DELETE
        response_delete = self.client.delete(f'/api/mobile/available-parts/{self.part1.id}/')
        self.assertEqual(response_delete.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

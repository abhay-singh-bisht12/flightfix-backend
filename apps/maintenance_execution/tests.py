"""
Unit and integration tests for FlightFix Maintenance Execution & Documentation module.
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.aircraft.models import Aircraft, AircraftStatus
from apps.maintenance_planning.models import (
    MaintenanceSchedule,
    MaintenanceType,
    MaintenancePriority,
    MaintenanceStatus,
)
from apps.work_orders.models import (
    WorkOrder,
    WorkOrderType,
    WorkOrderPriority,
    WorkOrderStatus,
)
from apps.maintenance_execution.models import (
    MaintenanceExecution,
    MaintenanceDocumentation,
    ExecutionStatus,
    DocumentType,
    SignOffStatus,
)

User = get_user_model()


class BaseExecutionTestCase(APITestCase):
    """
    Sets up users with different roles, tokens, aircraft, schedules, and work orders.
    """
    def setUp(self):
        # 1. Setup Users for all 4 roles
        self.admin_user = User.objects.create_user(
            username='exec_admin',
            email='exec_admin@flightfix.com',
            password='Password123!',
            first_name='Admin',
            last_name='Officer',
            role=User.Role.ADMIN,
        )
        self.safety_user = User.objects.create_user(
            username='exec_safety',
            email='exec_safety@flightfix.com',
            password='Password123!',
            first_name='Safety',
            last_name='Lead',
            role=User.Role.SAFETY_OFFICER,
        )
        self.contracts_user = User.objects.create_user(
            username='exec_contracts',
            email='exec_contracts@flightfix.com',
            password='Password123!',
            first_name='Contracts',
            last_name='Lead',
            role=User.Role.CONTRACTS_MANAGER,
        )
        self.tech_user_1 = User.objects.create_user(
            username='exec_tech_1',
            email='tech1@flightfix.com',
            password='Password123!',
            first_name='Bob',
            last_name='Tech',
            role=User.Role.FIELD_TECHNICIAN,
        )
        self.tech_user_2 = User.objects.create_user(
            username='exec_tech_2',
            email='tech2@flightfix.com',
            password='Password123!',
            first_name='Alice',
            last_name='Tech',
            role=User.Role.FIELD_TECHNICIAN,
        )

        # 2. Setup JWT Tokens
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        self.safety_token = str(RefreshToken.for_user(self.safety_user).access_token)
        self.contracts_token = str(RefreshToken.for_user(self.contracts_user).access_token)
        self.tech_token_1 = str(RefreshToken.for_user(self.tech_user_1).access_token)
        self.tech_token_2 = str(RefreshToken.for_user(self.tech_user_2).access_token)

        # 3. Prerequisite: Aircraft
        self.aircraft = Aircraft.objects.create(
            registration_number='VT-EXE-101',
            aircraft_type='Commercial Jet',
            model='Airbus A320neo',
            manufacturer='Airbus',
            serial_number='MSN-EXE-101',
            status=AircraftStatus.ACTIVE,
        )

        # 4. Prerequisite: MaintenanceSchedule
        self.schedule = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft,
            title='Line Check 100 Flight Hours',
            description='Routine turn-around inspection.',
            maintenance_type=MaintenanceType.INSPECTION,
            priority=MaintenancePriority.HIGH,
            planned_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=2),
            status=MaintenanceStatus.IN_PROGRESS,
            assigned_to=self.tech_user_1,
            created_by=self.admin_user,
        )

        # 5. Prerequisite: WorkOrder
        self.work_order = WorkOrder.objects.create(
            work_order_number='WO-EXEC-2026-001',
            aircraft=self.aircraft,
            maintenance_schedule=self.schedule,
            title='Overhaul Main Gear Retraction Actuator',
            description='Inspect seals, lubricate linkages, and test hydraulic pressure.',
            work_order_type=WorkOrderType.CORRECTIVE,
            priority=WorkOrderPriority.HIGH,
            status=WorkOrderStatus.ASSIGNED,
            assigned_to=self.tech_user_1,
            created_by=self.admin_user,
            planned_start_date=timezone.now().date(),
            planned_completion_date=timezone.now().date() + timezone.timedelta(days=1),
            estimated_hours=Decimal('5.00'),
        )

        # 6. Sample MaintenanceExecution assigned to tech_user_1
        self.sample_execution = MaintenanceExecution.objects.create(
            work_order=self.work_order,
            aircraft=self.aircraft,
            executed_by=self.tech_user_1,
            created_by=self.admin_user,
            status=ExecutionStatus.IN_PROGRESS,
            started_at=timezone.now() - timezone.timedelta(hours=3),
            actual_labor_hours=Decimal('3.00'),
            work_performed='Disassembled actuator casing and inspected fluid seals.',
            findings='Minor seal wear noted on primary piston cylinder.',
            corrective_actions='Replaced fluorocarbon O-rings and torqued to manual spec.',
            remarks='Awaiting pressure bleed test.',
        )

    def auth_as(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def unauth(self):
        self.client.credentials()


class MaintenanceExecutionModelTests(BaseExecutionTestCase):
    """
    Tests for MaintenanceExecution model constraints and validation rules.
    """
    def test_auto_align_aircraft_with_work_order(self):
        execution = MaintenanceExecution(
            work_order=self.work_order,
            executed_by=self.tech_user_1,
            created_by=self.admin_user,
            work_performed='Lubricated main landing gear pivot pins.',
        )
        execution.save()
        self.assertEqual(execution.aircraft, self.work_order.aircraft)

    def test_negative_labor_hours_rejected(self):
        with self.assertRaises(ValidationError):
            exec_neg = MaintenanceExecution(
                work_order=self.work_order,
                aircraft=self.aircraft,
                executed_by=self.tech_user_1,
                created_by=self.admin_user,
                actual_labor_hours=Decimal('-2.50'),
                work_performed='Test work',
            )
            exec_neg.save()

    def test_completed_at_prior_to_started_at_rejected(self):
        now = timezone.now()
        with self.assertRaises(ValidationError):
            exec_invalid_time = MaintenanceExecution(
                work_order=self.work_order,
                aircraft=self.aircraft,
                executed_by=self.tech_user_1,
                created_by=self.admin_user,
                started_at=now,
                completed_at=now - timezone.timedelta(hours=2),
                work_performed='Invalid time sequence test',
            )
            exec_invalid_time.save()

    def test_mismatched_aircraft_rejected(self):
        other_aircraft = Aircraft.objects.create(
            registration_number='VT-OTHER-99',
            aircraft_type='Commercial Jet',
            model='Boeing 777-300ER',
            manufacturer='Boeing',
            serial_number='MSN-OTH-99',
        )
        with self.assertRaises(ValidationError):
            exec_mismatch = MaintenanceExecution(
                work_order=self.work_order,
                aircraft=other_aircraft,  # does not match work_order.aircraft
                executed_by=self.tech_user_1,
                created_by=self.admin_user,
                work_performed='Mismatch test',
            )
            exec_mismatch.save()


class MaintenanceDocumentationModelTests(BaseExecutionTestCase):
    """
    Tests for MaintenanceDocumentation model validation and uppercase normalization.
    """
    def test_document_number_normalized_uppercase(self):
        doc = MaintenanceDocumentation.objects.create(
            execution=self.sample_execution,
            document_type=DocumentType.RELEASE_TO_SERVICE,
            document_number='  crs-2026-test-01  ',
            title='Certificate of Release to Service',
            issuing_authority='DGCA India',
            sign_off_status=SignOffStatus.DRAFT,
        )
        self.assertEqual(doc.document_number, 'CRS-2026-TEST-01')

    def test_duplicate_document_number_rejected(self):
        MaintenanceDocumentation.objects.create(
            execution=self.sample_execution,
            document_type=DocumentType.RELEASE_TO_SERVICE,
            document_number='CRS-2026-DUP-01',
            title='First Cert',
            issuing_authority='DGCA',
            sign_off_status=SignOffStatus.DRAFT,
        )
        with self.assertRaises(ValidationError):
            dup = MaintenanceDocumentation(
                execution=self.sample_execution,
                document_type=DocumentType.INSPECTION_REPORT,
                document_number='crs-2026-dup-01',  # same number in lowercase
                title='Second Cert',
                issuing_authority='DGCA',
                sign_off_status=SignOffStatus.DRAFT,
            )
            dup.save()

    def test_signed_off_without_certifier_rejected(self):
        with self.assertRaises(ValidationError):
            doc = MaintenanceDocumentation(
                execution=self.sample_execution,
                document_type=DocumentType.RELEASE_TO_SERVICE,
                document_number='CRS-FAIL-NO-SIGNER',
                title='Unsigned Approval',
                issuing_authority='DGCA',
                sign_off_status=SignOffStatus.SIGNED,  # SIGNED requires signed_off_by
                signed_off_by=None,
            )
            doc.save()


class MaintenanceExecutionAPITests(BaseExecutionTestCase):
    """
    Tests for MaintenanceExecution API: permissions across all 4 roles, CRUD, validation, search, filter.
    """
    def test_unauthenticated_request_rejected(self):
        self.unauth()
        response = self.client.get('/api/maintenance-execution/records/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_create_execution_record(self):
        self.auth_as(self.admin_token)
        payload = {
            'work_order': self.work_order.id,
            'executed_by': self.tech_user_1.id,
            'status': 'IN_PROGRESS',
            'started_at': timezone.now().isoformat(),
            'actual_labor_hours': '2.50',
            'work_performed': 'Removed worn brake pads and cleaned caliper housing.',
            'findings': 'Heavy brake lining wear.',
            'corrective_actions': 'Fitted new carbon brake pack.',
        }
        response = self.client.post('/api/maintenance-execution/records/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['work_order_number'], self.work_order.work_order_number)
        self.assertEqual(response.data['created_by_username'], self.admin_user.username)

    def test_safety_officer_can_create_and_update_but_not_delete(self):
        self.auth_as(self.safety_token)
        payload = {
            'work_order': self.work_order.id,
            'executed_by': self.tech_user_1.id,
            'status': 'IN_PROGRESS',
            'actual_labor_hours': '1.00',
            'work_performed': 'Safety inspection on flap trailing edge.',
        }
        create_resp = self.client.post('/api/maintenance-execution/records/', payload)
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        exec_id = create_resp.data['id']

        # Update
        patch_resp = self.client.patch(
            f'/api/maintenance-execution/records/{exec_id}/',
            {'remarks': 'Inspected and verified.'}
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)

        # Delete should be forbidden (403)
        del_resp = self.client.delete(f'/api/maintenance-execution/records/{exec_id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_contracts_manager_read_only(self):
        self.auth_as(self.contracts_token)
        # List and Retrieve allowed
        list_resp = self.client.get('/api/maintenance-execution/records/')
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)

        detail_resp = self.client.get(f'/api/maintenance-execution/records/{self.sample_execution.id}/')
        self.assertEqual(detail_resp.status_code, status.HTTP_200_OK)

        # POST / PUT / PATCH / DELETE forbidden
        post_resp = self.client.post('/api/maintenance-execution/records/', {'work_order': self.work_order.id})
        self.assertEqual(post_resp.status_code, status.HTTP_403_FORBIDDEN)

        patch_resp = self.client.patch(f'/api/maintenance-execution/records/{self.sample_execution.id}/', {'remarks': 'test'})
        self.assertEqual(patch_resp.status_code, status.HTTP_403_FORBIDDEN)

        del_resp = self.client.delete(f'/api/maintenance-execution/records/{self.sample_execution.id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_field_technician_can_view_and_update_only_assigned_record(self):
        # 1. Tech 1 (assigned) can view and update sample_execution
        self.auth_as(self.tech_token_1)
        resp_view = self.client.get(f'/api/maintenance-execution/records/{self.sample_execution.id}/')
        self.assertEqual(resp_view.status_code, status.HTTP_200_OK)

        resp_update = self.client.patch(
            f'/api/maintenance-execution/records/{self.sample_execution.id}/',
            {'actual_labor_hours': '4.50', 'remarks': 'Completed hydraulic bleed test.'}
        )
        self.assertEqual(resp_update.status_code, status.HTTP_200_OK)
        self.sample_execution.refresh_from_db()
        self.assertEqual(self.sample_execution.actual_labor_hours, Decimal('4.50'))

        # Tech 1 cannot DELETE
        resp_del = self.client.delete(f'/api/maintenance-execution/records/{self.sample_execution.id}/')
        self.assertEqual(resp_del.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Tech 2 (not assigned) CANNOT view or update Tech 1's record
        self.auth_as(self.tech_token_2)
        resp_other_list = self.client.get('/api/maintenance-execution/records/')
        self.assertEqual(resp_other_list.status_code, status.HTTP_200_OK)
        results = resp_other_list.data.get('results', resp_other_list.data)
        self.assertFalse(any(r['id'] == self.sample_execution.id for r in results))

        resp_other_detail = self.client.get(f'/api/maintenance-execution/records/{self.sample_execution.id}/')
        self.assertEqual(resp_other_detail.status_code, status.HTTP_404_NOT_FOUND)

        resp_other_patch = self.client.patch(
            f'/api/maintenance-execution/records/{self.sample_execution.id}/',
            {'remarks': 'Hacked by another tech'}
        )
        self.assertIn(resp_other_patch.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_negative_labor_hours_api_rejected(self):
        self.auth_as(self.admin_token)
        payload = {
            'work_order': self.work_order.id,
            'executed_by': self.tech_user_1.id,
            'actual_labor_hours': '-1.50',
            'work_performed': 'Negative labor test',
        }
        response = self.client.post('/api/maintenance-execution/records/', payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('actual_labor_hours', response.data)

    def test_invalid_timestamps_api_rejected(self):
        self.auth_as(self.admin_token)
        now = timezone.now()
        payload = {
            'work_order': self.work_order.id,
            'executed_by': self.tech_user_1.id,
            'started_at': now.isoformat(),
            'completed_at': (now - timezone.timedelta(hours=1)).isoformat(),
            'work_performed': 'Invalid timestamp sequence test',
        }
        response = self.client.post('/api/maintenance-execution/records/', payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('completed_at', response.data)

    def test_completed_execution_syncs_work_order_actual_hours(self):
        self.auth_as(self.admin_token)
        now = timezone.now()
        payload = {
            'work_order': self.work_order.id,
            'executed_by': self.tech_user_1.id,
            'status': 'COMPLETED',
            'started_at': (now - timezone.timedelta(hours=4)).isoformat(),
            'completed_at': now.isoformat(),
            'actual_labor_hours': '4.00',
            'work_performed': 'Completed actuator overhaul and ops check.',
        }
        response = self.client.post('/api/maintenance-execution/records/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.work_order.refresh_from_db()
        self.assertEqual(self.work_order.actual_hours, Decimal('4.00'))
        self.assertEqual(self.work_order.actual_completion_date, now.date())

    def test_search_and_filters_execution(self):
        self.auth_as(self.admin_token)
        response_search = self.client.get(f'/api/maintenance-execution/records/?search={self.work_order.work_order_number}')
        self.assertEqual(response_search.status_code, status.HTTP_200_OK)
        results = response_search.data.get('results', response_search.data)
        self.assertTrue(len(results) >= 1)

        response_filter = self.client.get('/api/maintenance-execution/records/?status=IN_PROGRESS')
        self.assertEqual(response_filter.status_code, status.HTTP_200_OK)
        for r in response_filter.data.get('results', response_filter.data):
            self.assertEqual(r['status'], 'IN_PROGRESS')


class MaintenanceDocumentationAPITests(BaseExecutionTestCase):
    """
    Tests for MaintenanceDocumentation API: sign-offs, regulatory certifications, and permissions.
    """
    def test_unauthenticated_request_rejected(self):
        self.unauth()
        response = self.client.get('/api/maintenance-execution/documentation/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_create_and_delete_documentation(self):
        self.auth_as(self.admin_token)
        payload = {
            'execution': self.sample_execution.id,
            'document_type': 'RELEASE_TO_SERVICE',
            'document_number': 'CRS-2026-0099',
            'title': 'Certificate of Release to Service - Bay 2',
            'issuing_authority': 'FAA & DGCA Quality Assurance',
            'sign_off_status': 'DRAFT',
            'remarks': 'Pending flight line functional check.',
        }
        response = self.client.post('/api/maintenance-execution/documentation/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc_id = response.data['id']

        # Delete
        del_resp = self.client.delete(f'/api/maintenance-execution/documentation/{doc_id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_safety_officer_can_create_and_sign_off_document(self):
        self.auth_as(self.safety_token)
        payload = {
            'execution': self.sample_execution.id,
            'document_type': 'RELEASE_TO_SERVICE',
            'document_number': 'CRS-2026-SAFE-01',
            'title': 'CRS Sign-off',
            'issuing_authority': 'FlightFix Quality Assurance',
            'sign_off_status': 'SIGNED',
            'signed_off_by': self.safety_user.id,
            'signed_off_at': timezone.now().isoformat(),
            'remarks': 'All AMM procedures verified compliant.',
        }
        response = self.client.post('/api/maintenance-execution/documentation/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['signed_off_by_username'], self.safety_user.username)
        self.assertEqual(response.data['sign_off_status'], 'SIGNED')

    def test_signed_off_without_certifier_rejected_by_api(self):
        self.auth_as(self.safety_token)
        payload = {
            'execution': self.sample_execution.id,
            'document_type': 'RELEASE_TO_SERVICE',
            'document_number': 'CRS-2026-FAIL',
            'title': 'Uncertified Signoff',
            'issuing_authority': 'DGCA',
            'sign_off_status': 'SIGNED',
            'signed_off_by': None,
        }
        response = self.client.post('/api/maintenance-execution/documentation/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('signed_off_by', response.data)

    def test_field_technician_can_view_assigned_documentation(self):
        # Create documentation under sample_execution (assigned to tech_user_1)
        MaintenanceDocumentation.objects.create(
            execution=self.sample_execution,
            document_type=DocumentType.TASK_CHECKLIST,
            document_number='CHK-2026-TECH-01',
            title='Checklist Review',
            issuing_authority='Engineering Ops',
            sign_off_status=SignOffStatus.DRAFT,
        )
        self.auth_as(self.tech_token_1)
        response = self.client.get('/api/maintenance-execution/documentation/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertTrue(any(d['document_number'] == 'CHK-2026-TECH-01' for d in results))

        # Tech 2 (not assigned to this execution) should NOT see it
        self.auth_as(self.tech_token_2)
        response_tech2 = self.client.get('/api/maintenance-execution/documentation/')
        self.assertEqual(response_tech2.status_code, status.HTTP_200_OK)
        results_tech2 = response_tech2.data.get('results', response_tech2.data)
        self.assertFalse(any(d['document_number'] == 'CHK-2026-TECH-01' for d in results_tech2))

"""
Unit and integration tests for FlightFix Work Order Management module.
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
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

User = get_user_model()


class BaseWorkOrderTestCase(APITestCase):
    """
    Common setup providing pre-configured users with different roles, tokens, aircraft, and schedules.
    """
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='wo_admin',
            email='admin@flightfix.com',
            password='Password123!',
            first_name='Admin',
            last_name='Boss',
            role=User.Role.ADMIN,
        )
        self.safety_user = User.objects.create_user(
            username='wo_safety',
            email='safety@flightfix.com',
            password='Password123!',
            first_name='Safety',
            last_name='Lead',
            role=User.Role.SAFETY_OFFICER,
        )
        self.contracts_user = User.objects.create_user(
            username='wo_contracts',
            email='contracts@flightfix.com',
            password='Password123!',
            first_name='Contracts',
            last_name='Lead',
            role=User.Role.CONTRACTS_MANAGER,
        )
        self.tech_user_1 = User.objects.create_user(
            username='wo_tech_1',
            email='tech1@flightfix.com',
            password='Password123!',
            first_name='Field',
            last_name='Tech One',
            role=User.Role.FIELD_TECHNICIAN,
        )
        self.tech_user_2 = User.objects.create_user(
            username='wo_tech_2',
            email='tech2@flightfix.com',
            password='Password123!',
            first_name='Field',
            last_name='Tech Two',
            role=User.Role.FIELD_TECHNICIAN,
        )

        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        self.safety_token = str(RefreshToken.for_user(self.safety_user).access_token)
        self.contracts_token = str(RefreshToken.for_user(self.contracts_user).access_token)
        self.tech_token_1 = str(RefreshToken.for_user(self.tech_user_1).access_token)
        self.tech_token_2 = str(RefreshToken.for_user(self.tech_user_2).access_token)

        self.aircraft_1 = Aircraft.objects.create(
            registration_number='VT-WO001',
            aircraft_type='Commercial Jet',
            model='Boeing 737-800',
            manufacturer='Boeing',
            serial_number='MSN-WO-01',
            status=AircraftStatus.ACTIVE,
        )
        self.aircraft_2 = Aircraft.objects.create(
            registration_number='VT-WO002',
            aircraft_type='Regional Jet',
            model='Airbus A220',
            manufacturer='Airbus',
            serial_number='MSN-WO-02',
            status=AircraftStatus.MAINTENANCE,
        )

        self.schedule_1 = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Hydraulic System 500-hour Inspection',
            maintenance_type=MaintenanceType.INSPECTION,
            priority=MaintenancePriority.HIGH,
            planned_date='2026-12-01',
            due_date='2026-12-05',
            status=MaintenanceStatus.PLANNED,
            created_by=self.admin_user,
        )

        self.url = '/api/work-orders/'

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def unauth(self):
        self.client.credentials()


class WorkOrderAuthenticationCRUDTests(BaseWorkOrderTestCase):
    """
    Tests for authentication requirements and full CRUD operations.
    """
    def setUp(self):
        super().setUp()
        self.valid_payload = {
            'work_order_number': 'WO-2026-0001',
            'aircraft': self.aircraft_1.id,
            'maintenance_schedule': self.schedule_1.id,
            'title': 'Landing Gear Actuator Replacement',
            'description': 'Replace starboard main gear hydraulic actuator seal and test extension mechanism.',
            'work_order_type': WorkOrderType.CORRECTIVE,
            'priority': WorkOrderPriority.HIGH,
            'status': WorkOrderStatus.OPEN,
            'assigned_to': self.tech_user_1.id,
            'planned_start_date': '2026-12-01',
            'planned_completion_date': '2026-12-03',
            'estimated_hours': '12.50',
            'notes': 'Test under hydraulic rig pressure.',
        }

    def test_unauthenticated_access_list_rejected(self):
        self.unauth()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_access_create_rejected(self):
        self.unauth()
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_work_order_admin(self):
        self.auth(self.admin_token)
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['work_order_number'], 'WO-2026-0001')
        self.assertEqual(response.data['created_by'], self.admin_user.id)
        self.assertEqual(response.data['created_by_username'], 'wo_admin')
        self.assertTrue(WorkOrder.objects.filter(work_order_number='WO-2026-0001').exists())

    def test_create_work_order_safety_officer(self):
        self.auth(self.safety_token)
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['created_by'], self.safety_user.id)
        self.assertEqual(response.data['created_by_username'], 'wo_safety')

    def test_retrieve_work_order(self):
        wo = WorkOrder.objects.create(
            work_order_number='WO-2026-0001',
            aircraft=self.aircraft_1,
            title='Avionics Check',
            description='Test weather radar.',
            created_by=self.admin_user,
        )
        self.auth(self.admin_token)
        response = self.client.get(f'{self.url}{wo.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['work_order_number'], 'WO-2026-0001')
        self.assertEqual(response.data['aircraft_registration'], 'VT-WO001')

    def test_update_work_order_put(self):
        wo = WorkOrder.objects.create(
            work_order_number='WO-2026-0001',
            aircraft=self.aircraft_1,
            title='Old Title',
            description='Initial scope.',
            created_by=self.admin_user,
        )
        self.auth(self.admin_token)
        put_payload = self.valid_payload.copy()
        put_payload['title'] = 'Updated Full Scope Title'
        put_payload['status'] = WorkOrderStatus.IN_PROGRESS
        response = self.client.put(f'{self.url}{wo.id}/', put_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        wo.refresh_from_db()
        self.assertEqual(wo.title, 'Updated Full Scope Title')
        self.assertEqual(wo.status, WorkOrderStatus.IN_PROGRESS)

    def test_partial_update_work_order_patch(self):
        wo = WorkOrder.objects.create(
            work_order_number='WO-2026-0001',
            aircraft=self.aircraft_1,
            title='Brake Inspection',
            description='Check brake discs.',
            created_by=self.admin_user,
        )
        self.auth(self.admin_token)
        patch_payload = {
            'status': WorkOrderStatus.COMPLETED,
            'actual_hours': '8.25',
            'findings': 'Brake pads worn within tolerance.',
            'corrective_action': 'Cleaned assemblies and torqued bolts.',
        }
        response = self.client.patch(f'{self.url}{wo.id}/', patch_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        wo.refresh_from_db()
        self.assertEqual(wo.status, WorkOrderStatus.COMPLETED)
        self.assertEqual(wo.actual_hours, Decimal('8.25'))
        self.assertEqual(wo.findings, 'Brake pads worn within tolerance.')

    def test_delete_work_order_admin(self):
        wo = WorkOrder.objects.create(
            work_order_number='WO-2026-0001',
            aircraft=self.aircraft_1,
            title='Cancel Me',
            description='To be deleted.',
            created_by=self.admin_user,
        )
        self.auth(self.admin_token)
        response = self.client.delete(f'{self.url}{wo.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(WorkOrder.objects.filter(id=wo.id).exists())

    def test_created_by_automatic_assignment(self):
        self.auth(self.admin_token)
        # Attempt to pass a different created_by in the payload
        payload = self.valid_payload.copy()
        payload['created_by'] = self.tech_user_1.id
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # created_by must be set to the requesting user (admin_user), ignoring payload override
        self.assertEqual(response.data['created_by'], self.admin_user.id)


class WorkOrderPermissionTests(BaseWorkOrderTestCase):
    """
    Tests enforcing role-based permissions across ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER, and FIELD_TECHNICIAN.
    """
    def setUp(self):
        super().setUp()
        self.sample_wo = WorkOrder.objects.create(
            work_order_number='WO-2026-PERM',
            aircraft=self.aircraft_1,
            title='Engine Diagnostic',
            description='Check sensor telemetry.',
            assigned_to=self.tech_user_1,
            created_by=self.admin_user,
        )
        self.sample_payload = {
            'work_order_number': 'WO-2026-NEW',
            'aircraft': self.aircraft_1.id,
            'title': 'New Safety Order',
            'description': 'Mandatory safety bulletin inspection.',
        }

    def test_admin_full_crud(self):
        self.auth(self.admin_token)
        # Create
        res_post = self.client.post(self.url, self.sample_payload, format='json')
        self.assertEqual(res_post.status_code, status.HTTP_201_CREATED)
        created_id = res_post.data['id']
        # Read
        res_get = self.client.get(f'{self.url}{created_id}/')
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        # Update
        res_patch = self.client.patch(f'{self.url}{created_id}/', {'status': WorkOrderStatus.IN_PROGRESS}, format='json')
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        # Delete
        res_del = self.client.delete(f'{self.url}{created_id}/')
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)

    def test_safety_officer_can_create_and_update(self):
        self.auth(self.safety_token)
        res_post = self.client.post(self.url, self.sample_payload, format='json')
        self.assertEqual(res_post.status_code, status.HTTP_201_CREATED)
        created_id = res_post.data['id']
        res_patch = self.client.patch(f'{self.url}{created_id}/', {'priority': WorkOrderPriority.CRITICAL}, format='json')
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)

    def test_safety_officer_cannot_delete(self):
        self.auth(self.safety_token)
        response = self.client.delete(f'{self.url}{self.sample_wo.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(WorkOrder.objects.filter(id=self.sample_wo.id).exists())

    def test_contracts_manager_can_get(self):
        self.auth(self.contracts_token)
        res_list = self.client.get(self.url)
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        res_detail = self.client.get(f'{self.url}{self.sample_wo.id}/')
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)

    def test_contracts_manager_cannot_create(self):
        self.auth(self.contracts_token)
        response = self.client.post(self.url, self.sample_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_contracts_manager_cannot_update(self):
        self.auth(self.contracts_token)
        response = self.client.patch(f'{self.url}{self.sample_wo.id}/', {'status': WorkOrderStatus.CANCELLED}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_contracts_manager_cannot_delete(self):
        self.auth(self.contracts_token)
        response = self.client.delete(f'{self.url}{self.sample_wo.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_field_technician_can_get(self):
        self.auth(self.tech_token_1)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_field_technician_cannot_create(self):
        self.auth(self.tech_token_1)
        response = self.client.post(self.url, self.sample_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_field_technician_cannot_update(self):
        self.auth(self.tech_token_1)
        response = self.client.patch(f'{self.url}{self.sample_wo.id}/', {'status': WorkOrderStatus.COMPLETED}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_field_technician_cannot_delete(self):
        self.auth(self.tech_token_1)
        response = self.client.delete(f'{self.url}{self.sample_wo.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_technician_sees_only_assigned_work_orders_list(self):
        wo_tech_1 = WorkOrder.objects.create(
            work_order_number='WO-TECH-01',
            aircraft=self.aircraft_1,
            title='Assigned to Tech 1',
            description='Desc',
            assigned_to=self.tech_user_1,
            created_by=self.admin_user,
        )
        wo_tech_2 = WorkOrder.objects.create(
            work_order_number='WO-TECH-02',
            aircraft=self.aircraft_2,
            title='Assigned to Tech 2',
            description='Desc',
            assigned_to=self.tech_user_2,
            created_by=self.admin_user,
        )
        wo_unassigned = WorkOrder.objects.create(
            work_order_number='WO-UNASSIGNED',
            aircraft=self.aircraft_1,
            title='Unassigned WO',
            description='Desc',
            created_by=self.admin_user,
        )

        self.auth(self.tech_token_1)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = [item['id'] for item in response.data['results']]
        self.assertIn(wo_tech_1.id, returned_ids)
        self.assertNotIn(wo_tech_2.id, returned_ids)
        self.assertNotIn(wo_unassigned.id, returned_ids)

    def test_technician_cannot_retrieve_unassigned_work_order(self):
        wo_other = WorkOrder.objects.create(
            work_order_number='WO-OTHER',
            aircraft=self.aircraft_1,
            title='Other Tech Order',
            description='Desc',
            assigned_to=self.tech_user_2,
            created_by=self.admin_user,
        )
        self.auth(self.tech_token_1)
        response = self.client.get(f'{self.url}{wo_other.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class WorkOrderValidationTests(BaseWorkOrderTestCase):
    """
    Tests enforcing field validations, unique constraints, and date integrity.
    """
    def setUp(self):
        super().setUp()
        self.auth(self.admin_token)
        self.base_payload = {
            'work_order_number': 'WO-2026-VAL',
            'aircraft': self.aircraft_1.id,
            'title': 'Validation Check',
            'description': 'Valid description.',
        }

    def test_duplicate_work_order_number(self):
        WorkOrder.objects.create(
            work_order_number='WO-2026-VAL',
            aircraft=self.aircraft_1,
            title='Existing Order',
            description='Desc',
            created_by=self.admin_user,
        )
        response = self.client.post(self.url, self.base_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('work_order_number', response.data)

    def test_invalid_status(self):
        payload = self.base_payload.copy()
        payload['status'] = 'NOT_A_VALID_STATUS'
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    def test_invalid_priority(self):
        payload = self.base_payload.copy()
        payload['priority'] = 'SUPER_URGENT'
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('priority', response.data)

    def test_invalid_work_order_type(self):
        payload = self.base_payload.copy()
        payload['work_order_type'] = 'UNSCHEDULED_COSMETIC'
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('work_order_type', response.data)

    def test_negative_estimated_hours(self):
        payload = self.base_payload.copy()
        payload['estimated_hours'] = '-5.00'
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estimated_hours', response.data)

    def test_negative_actual_hours(self):
        payload = self.base_payload.copy()
        payload['actual_hours'] = '-2.50'
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('actual_hours', response.data)

    def test_invalid_planned_dates(self):
        payload = self.base_payload.copy()
        payload['planned_start_date'] = '2026-12-10'
        payload['planned_completion_date'] = '2026-12-05'  # before start
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('planned_completion_date', response.data)

    def test_invalid_actual_dates(self):
        payload = self.base_payload.copy()
        payload['actual_start_date'] = '2026-12-15'
        payload['actual_completion_date'] = '2026-12-12'  # before start
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('actual_completion_date', response.data)

    def test_invalid_aircraft(self):
        payload = self.base_payload.copy()
        payload['aircraft'] = 999999
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('aircraft', response.data)

    def test_invalid_assigned_user(self):
        payload = self.base_payload.copy()
        payload['assigned_to'] = 999999
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('assigned_to', response.data)

    def test_missing_required_fields(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('work_order_number', response.data)
        self.assertIn('aircraft', response.data)
        self.assertIn('title', response.data)
        self.assertIn('description', response.data)


class WorkOrderRelationshipTests(BaseWorkOrderTestCase):
    """
    Tests checking model relationships and readable serializer representations.
    """
    def test_relationships_and_display_fields(self):
        wo = WorkOrder.objects.create(
            work_order_number='WO-REL-001',
            aircraft=self.aircraft_1,
            maintenance_schedule=self.schedule_1,
            title='Hydraulic Pump Overhaul',
            description='Overhaul main pump.',
            work_order_type=WorkOrderType.PREVENTIVE,
            priority=WorkOrderPriority.CRITICAL,
            status=WorkOrderStatus.ASSIGNED,
            assigned_to=self.tech_user_1,
            created_by=self.admin_user,
        )
        self.auth(self.admin_token)
        response = self.client.get(f'{self.url}{wo.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['aircraft_registration'], 'VT-WO001')
        self.assertEqual(response.data['aircraft_model'], 'Boeing 737-800')
        self.assertEqual(response.data['maintenance_schedule_title'], 'Hydraulic System 500-hour Inspection')
        self.assertEqual(response.data['assigned_to_username'], 'wo_tech_1')
        self.assertEqual(response.data['created_by_username'], 'wo_admin')
        self.assertEqual(response.data['priority_display'], 'Critical')
        self.assertEqual(response.data['status_display'], 'Assigned')
        self.assertEqual(response.data['work_order_type_display'], 'Preventive')


class WorkOrderSearchFilterPaginationTests(BaseWorkOrderTestCase):
    """
    Tests covering text search, query parameters, and pagination.
    """
    def setUp(self):
        super().setUp()
        self.auth(self.admin_token)
        self.wo_1 = WorkOrder.objects.create(
            work_order_number='WO-SEARCH-01',
            aircraft=self.aircraft_1,
            maintenance_schedule=self.schedule_1,
            title='Turbofan Fan Blade Lubrication',
            description='Apply aero-grade lubricant to fan blade roots.',
            findings='Minor dust buildup.',
            corrective_action='Cleaned and relubricated.',
            work_order_type=WorkOrderType.PREVENTIVE,
            priority=WorkOrderPriority.LOW,
            status=WorkOrderStatus.OPEN,
            assigned_to=self.tech_user_1,
            planned_start_date='2026-12-01',
            planned_completion_date='2026-12-02',
            created_by=self.admin_user,
        )
        self.wo_2 = WorkOrder.objects.create(
            work_order_number='WO-SEARCH-02',
            aircraft=self.aircraft_2,
            title='Avionics Transponder Replacement',
            description='Replace Mode S transponder unit.',
            findings='Intermittent squawk transmission failure.',
            corrective_action='Installed replacement LRU.',
            work_order_type=WorkOrderType.CORRECTIVE,
            priority=WorkOrderPriority.CRITICAL,
            status=WorkOrderStatus.IN_PROGRESS,
            assigned_to=self.tech_user_2,
            planned_start_date='2026-12-05',
            planned_completion_date='2026-12-06',
            created_by=self.admin_user,
        )

    def test_search_by_work_order_number(self):
        response = self.client.get(f'{self.url}?search=WO-SEARCH-01')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.wo_1.id)

    def test_search_by_title(self):
        response = self.client.get(f'{self.url}?search=Transponder')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.wo_2.id)

    def test_search_by_aircraft(self):
        response = self.client.get(f'{self.url}?search=VT-WO001')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.wo_1.id)

    def test_filter_by_status(self):
        response = self.client.get(f'{self.url}?status=IN_PROGRESS')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.wo_2.id)

    def test_filter_by_priority(self):
        response = self.client.get(f'{self.url}?priority=CRITICAL')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.wo_2.id)

    def test_filter_by_work_order_type(self):
        response = self.client.get(f'{self.url}?work_order_type=PREVENTIVE')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.wo_1.id)

    def test_filter_by_aircraft(self):
        response = self.client.get(f'{self.url}?aircraft={self.aircraft_1.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.wo_1.id)

    def test_filter_by_assigned_to(self):
        response = self.client.get(f'{self.url}?assigned_to={self.tech_user_2.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.wo_2.id)

    def test_filter_by_maintenance_schedule(self):
        response = self.client.get(f'{self.url}?maintenance_schedule={self.schedule_1.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.wo_1.id)

    def test_pagination(self):
        response = self.client.get(f'{self.url}?page_size=1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIsNotNone(response.data['next'])

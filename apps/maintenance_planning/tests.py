"""
Unit and integration tests for FlightFix Maintenance Planning & Scheduling module.
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.aircraft.models import Aircraft, AircraftStatus
from apps.maintenance_planning.models import (
    MaintenanceSchedule,
    MaintenanceTask,
    MaintenanceType,
    MaintenancePriority,
    MaintenanceStatus,
    TaskStatus,
)

User = get_user_model()


class BaseMaintenanceTestCase(APITestCase):
    """
    Common setup providing pre-configured users with different roles, JWT tokens, and aircraft.
    """
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='maint_admin',
            email='admin@flightfix.com',
            password='Password123!',
            first_name='Admin',
            last_name='Boss',
            role=User.Role.ADMIN,
        )
        self.safety_user = User.objects.create_user(
            username='maint_safety',
            email='safety@flightfix.com',
            password='Password123!',
            first_name='Safety',
            last_name='Inspector',
            role=User.Role.SAFETY_OFFICER,
        )
        self.contracts_user = User.objects.create_user(
            username='maint_contracts',
            email='contracts@flightfix.com',
            password='Password123!',
            first_name='Contracts',
            last_name='Lead',
            role=User.Role.CONTRACTS_MANAGER,
        )
        self.tech_user_1 = User.objects.create_user(
            username='maint_tech_1',
            email='tech1@flightfix.com',
            password='Password123!',
            first_name='Field',
            last_name='Tech One',
            role=User.Role.FIELD_TECHNICIAN,
        )
        self.tech_user_2 = User.objects.create_user(
            username='maint_tech_2',
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
            registration_number='VT-MNT01',
            aircraft_type='Commercial Jet',
            model='Boeing 737-800',
            manufacturer='Boeing',
            serial_number='MSN-99001',
            status=AircraftStatus.ACTIVE,
        )
        self.aircraft_2 = Aircraft.objects.create(
            registration_number='VT-MNT02',
            aircraft_type='Regional Jet',
            model='Airbus A220',
            manufacturer='Airbus',
            serial_number='MSN-99002',
            status=AircraftStatus.MAINTENANCE,
        )

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def unauth(self):
        self.client.credentials()


class MaintenanceScheduleAPITests(BaseMaintenanceTestCase):
    """
    Tests for MaintenanceSchedule CRUD, validations, and role permissions.
    """
    def setUp(self):
        super().setUp()
        self.schedules_url = '/api/maintenance/schedules/'
        self.valid_payload = {
            'aircraft': self.aircraft_1.id,
            'title': 'A-Check Periodic Inspection',
            'description': 'Regular 500 flight hour routine inspection of airframe and engines.',
            'maintenance_type': MaintenanceType.INSPECTION,
            'priority': MaintenancePriority.HIGH,
            'planned_date': '2026-12-01',
            'due_date': '2026-12-05',
            'status': MaintenanceStatus.PLANNED,
            'assigned_to': self.tech_user_1.id,
            'notes': 'Coordinate with Bay 3 ground crew.',
        }

    def test_schedule_creation_admin(self):
        self.auth(self.admin_token)
        response = self.client.post(self.schedules_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'A-Check Periodic Inspection')
        self.assertEqual(response.data['aircraft_registration'], 'VT-MNT01')
        self.assertEqual(response.data['created_by'], self.admin_user.id)
        self.assertEqual(response.data['created_by_username'], 'maint_admin')
        self.assertTrue(MaintenanceSchedule.objects.filter(title='A-Check Periodic Inspection').exists())

    def test_schedule_creation_safety_officer(self):
        self.auth(self.safety_token)
        response = self.client.post(self.schedules_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['created_by'], self.safety_user.id)

    def test_schedule_creation_contracts_manager_forbidden(self):
        self.auth(self.contracts_token)
        response = self.client.post(self.schedules_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_schedule_creation_technician_forbidden(self):
        self.auth(self.tech_token_1)
        response = self.client.post(self.schedules_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_schedule_creation_unauthenticated(self):
        self.unauth()
        response = self.client.post(self.schedules_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_schedule_creation_invalid_dates(self):
        self.auth(self.admin_token)
        payload = self.valid_payload.copy()
        payload['planned_date'] = '2026-12-10'
        payload['due_date'] = '2026-12-05'  # due_date is before planned_date
        response = self.client.post(self.schedules_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('due_date', response.data)

    def test_schedule_creation_invalid_priority(self):
        self.auth(self.admin_token)
        payload = self.valid_payload.copy()
        payload['priority'] = 'SUPER_URGENT'
        response = self.client.post(self.schedules_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('priority', response.data)

    def test_schedule_creation_invalid_type(self):
        self.auth(self.admin_token)
        payload = self.valid_payload.copy()
        payload['maintenance_type'] = 'DECORATION'
        response = self.client.post(self.schedules_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('maintenance_type', response.data)

    def test_schedule_creation_invalid_status(self):
        self.auth(self.admin_token)
        payload = self.valid_payload.copy()
        payload['status'] = 'FINISHED'
        response = self.client.post(self.schedules_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    def test_schedule_creation_nonexistent_aircraft(self):
        self.auth(self.admin_token)
        payload = self.valid_payload.copy()
        payload['aircraft'] = 999999
        response = self.client.post(self.schedules_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('aircraft', response.data)

    def test_schedule_creation_with_assigned_user(self):
        self.auth(self.admin_token)
        response = self.client.post(self.schedules_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['assigned_to'], self.tech_user_1.id)
        self.assertEqual(response.data['assigned_to_username'], 'maint_tech_1')

    def test_schedule_list_admin_and_safety_officer(self):
        MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Check A',
            planned_date='2026-12-01',
            due_date='2026-12-05',
            created_by=self.admin_user,
        )
        self.auth(self.safety_token)
        response = self.client.get(self.schedules_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_schedule_list_contracts_manager(self):
        MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Check A',
            planned_date='2026-12-01',
            due_date='2026-12-05',
            created_by=self.admin_user,
        )
        self.auth(self.contracts_token)
        response = self.client.get(self.schedules_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_schedule_list_technician_sees_only_assigned(self):
        sched_1 = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Tech 1 Task',
            planned_date='2026-12-01',
            due_date='2026-12-05',
            assigned_to=self.tech_user_1,
            created_by=self.admin_user,
        )
        sched_2 = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_2,
            title='Tech 2 Task',
            planned_date='2026-12-01',
            due_date='2026-12-05',
            assigned_to=self.tech_user_2,
            created_by=self.admin_user,
        )
        sched_unassigned = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Unassigned Task',
            planned_date='2026-12-01',
            due_date='2026-12-05',
            created_by=self.admin_user,
        )

        # Tech 1 requests list
        self.auth(self.tech_token_1)
        response = self.client.get(self.schedules_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], sched_1.id)

    def test_schedule_detail_with_nested_tasks(self):
        sched = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Engine C-Check',
            planned_date='2026-12-01',
            due_date='2026-12-10',
            created_by=self.admin_user,
        )
        MaintenanceTask.objects.create(
            schedule=sched,
            task_name='Borescope Inspection',
            task_order=1,
            status=TaskStatus.IN_PROGRESS,
            estimated_hours=Decimal('4.50'),
        )
        MaintenanceTask.objects.create(
            schedule=sched,
            task_name='Filter Replacement',
            task_order=2,
            status=TaskStatus.PENDING,
            estimated_hours=Decimal('2.00'),
        )

        self.auth(self.admin_token)
        response = self.client.get(f'{self.schedules_url}{sched.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tasks', response.data)
        self.assertEqual(len(response.data['tasks']), 2)
        self.assertEqual(response.data['tasks'][0]['task_name'], 'Borescope Inspection')

    def test_schedule_detail_technician_assigned_success(self):
        sched = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Assigned Tech Task',
            planned_date='2026-12-01',
            due_date='2026-12-05',
            assigned_to=self.tech_user_1,
            created_by=self.admin_user,
        )
        self.auth(self.tech_token_1)
        response = self.client.get(f'{self.schedules_url}{sched.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], sched.id)

    def test_schedule_detail_technician_unassigned_forbidden(self):
        sched = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Other Tech Task',
            planned_date='2026-12-01',
            due_date='2026-12-05',
            assigned_to=self.tech_user_2,
            created_by=self.admin_user,
        )
        self.auth(self.tech_token_1)
        response = self.client.get(f'{self.schedules_url}{sched.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_schedule_update_admin(self):
        sched = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Routine Check',
            planned_date='2026-12-01',
            due_date='2026-12-05',
            created_by=self.admin_user,
        )
        self.auth(self.admin_token)
        patch_payload = {'status': MaintenanceStatus.IN_PROGRESS, 'priority': MaintenancePriority.CRITICAL}
        response = self.client.patch(f'{self.schedules_url}{sched.id}/', patch_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sched.refresh_from_db()
        self.assertEqual(sched.status, MaintenanceStatus.IN_PROGRESS)
        self.assertEqual(sched.priority, MaintenancePriority.CRITICAL)

    def test_schedule_update_safety_officer(self):
        sched = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Routine Check',
            planned_date='2026-12-01',
            due_date='2026-12-05',
            created_by=self.admin_user,
        )
        self.auth(self.safety_token)
        patch_payload = {'status': MaintenanceStatus.COMPLETED}
        response = self.client.patch(f'{self.schedules_url}{sched.id}/', patch_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sched.refresh_from_db()
        self.assertEqual(sched.status, MaintenanceStatus.COMPLETED)

    def test_schedule_update_technician_forbidden(self):
        sched = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Routine Check',
            planned_date='2026-12-01',
            due_date='2026-12-05',
            assigned_to=self.tech_user_1,
            created_by=self.admin_user,
        )
        self.auth(self.tech_token_1)
        response = self.client.patch(f'{self.schedules_url}{sched.id}/', {'status': MaintenanceStatus.COMPLETED}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_schedule_delete_admin(self):
        sched = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Cancelled Event',
            planned_date='2026-12-01',
            due_date='2026-12-05',
            created_by=self.admin_user,
        )
        self.auth(self.admin_token)
        response = self.client.delete(f'{self.schedules_url}{sched.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MaintenanceSchedule.objects.filter(id=sched.id).exists())

    def test_schedule_delete_safety_officer_forbidden(self):
        sched = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Protected Event',
            planned_date='2026-12-01',
            due_date='2026-12-05',
            created_by=self.admin_user,
        )
        self.auth(self.safety_token)
        response = self.client.delete(f'{self.schedules_url}{sched.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(MaintenanceSchedule.objects.filter(id=sched.id).exists())

    def test_schedule_delete_contracts_manager_forbidden(self):
        sched = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Protected Event',
            planned_date='2026-12-01',
            due_date='2026-12-05',
            created_by=self.admin_user,
        )
        self.auth(self.contracts_token)
        response = self.client.delete(f'{self.schedules_url}{sched.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MaintenanceTaskAPITests(BaseMaintenanceTestCase):
    """
    Tests for MaintenanceTask CRUD, validations, and role permissions.
    """
    def setUp(self):
        super().setUp()
        self.tasks_url = '/api/maintenance/tasks/'
        self.schedule_1 = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Annual Overhaul',
            planned_date='2026-12-01',
            due_date='2026-12-15',
            assigned_to=self.tech_user_1,
            created_by=self.admin_user,
        )
        self.schedule_2 = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_2,
            title='Hydraulic Repair',
            planned_date='2026-12-02',
            due_date='2026-12-08',
            assigned_to=self.tech_user_2,
            created_by=self.admin_user,
        )

        self.valid_task_payload = {
            'schedule': self.schedule_1.id,
            'task_name': 'Inspect Main Landing Gear Actuators',
            'description': 'Check for hydraulic fluid leakage and micro-cracks.',
            'task_order': 1,
            'status': TaskStatus.PENDING,
            'estimated_hours': '3.50',
            'notes': 'Use torch and magnifying scope.',
        }

    def test_task_creation_admin(self):
        self.auth(self.admin_token)
        response = self.client.post(self.tasks_url, self.valid_task_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['task_name'], 'Inspect Main Landing Gear Actuators')
        self.assertEqual(response.data['schedule'], self.schedule_1.id)
        self.assertTrue(MaintenanceTask.objects.filter(task_name='Inspect Main Landing Gear Actuators').exists())

    def test_task_creation_safety_officer(self):
        self.auth(self.safety_token)
        response = self.client.post(self.tasks_url, self.valid_task_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_task_creation_technician_forbidden(self):
        self.auth(self.tech_token_1)
        response = self.client.post(self.tasks_url, self.valid_task_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_creation_invalid_schedule(self):
        self.auth(self.admin_token)
        payload = self.valid_task_payload.copy()
        payload['schedule'] = 999999
        response = self.client.post(self.tasks_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('schedule', response.data)

    def test_task_creation_negative_estimated_hours(self):
        self.auth(self.admin_token)
        payload = self.valid_task_payload.copy()
        payload['estimated_hours'] = '-3.00'
        response = self.client.post(self.tasks_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estimated_hours', response.data)

    def test_task_creation_invalid_status(self):
        self.auth(self.admin_token)
        payload = self.valid_task_payload.copy()
        payload['status'] = 'NOT_A_STATUS'
        response = self.client.post(self.tasks_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    def test_task_list_technician_sees_only_assigned(self):
        task_1 = MaintenanceTask.objects.create(
            schedule=self.schedule_1,
            task_name='Task for Tech 1 Schedule',
            task_order=1,
        )
        task_2 = MaintenanceTask.objects.create(
            schedule=self.schedule_2,
            task_name='Task for Tech 2 Schedule',
            task_order=1,
        )

        self.auth(self.tech_token_1)
        response = self.client.get(self.tasks_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], task_1.id)

    def test_task_update_admin(self):
        task = MaintenanceTask.objects.create(
            schedule=self.schedule_1,
            task_name='Initial Task',
            task_order=1,
            status=TaskStatus.PENDING,
        )
        self.auth(self.admin_token)
        patch_payload = {'status': TaskStatus.COMPLETED}
        response = self.client.patch(f'{self.tasks_url}{task.id}/', patch_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(task.completed_at)

    def test_task_update_safety_officer(self):
        task = MaintenanceTask.objects.create(
            schedule=self.schedule_1,
            task_name='Initial Task',
            task_order=1,
            status=TaskStatus.PENDING,
        )
        self.auth(self.safety_token)
        patch_payload = {'status': TaskStatus.IN_PROGRESS}
        response = self.client.patch(f'{self.tasks_url}{task.id}/', patch_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)

    def test_task_delete_admin(self):
        task = MaintenanceTask.objects.create(
            schedule=self.schedule_1,
            task_name='Deletable Task',
            task_order=1,
        )
        self.auth(self.admin_token)
        response = self.client.delete(f'{self.tasks_url}{task.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MaintenanceTask.objects.filter(id=task.id).exists())

    def test_task_delete_safety_officer_forbidden(self):
        task = MaintenanceTask.objects.create(
            schedule=self.schedule_1,
            task_name='Protected Task',
            task_order=1,
        )
        self.auth(self.safety_token)
        response = self.client.delete(f'{self.tasks_url}{task.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(MaintenanceTask.objects.filter(id=task.id).exists())


class MaintenanceFilterSearchPaginationTests(BaseMaintenanceTestCase):
    """
    Tests for search, query filters, and pagination.
    """
    def setUp(self):
        super().setUp()
        self.sched_1 = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_1,
            title='Turbine Blade Boroscope Inspection',
            description='Detailed inspection of high pressure turbine blades.',
            maintenance_type=MaintenanceType.INSPECTION,
            priority=MaintenancePriority.CRITICAL,
            planned_date='2026-12-01',
            due_date='2026-12-04',
            status=MaintenanceStatus.IN_PROGRESS,
            assigned_to=self.tech_user_1,
            created_by=self.admin_user,
        )
        self.sched_2 = MaintenanceSchedule.objects.create(
            aircraft=self.aircraft_2,
            title='Avionics Software Calibration',
            description='Navigation subsystem firmware upgrade.',
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.LOW,
            planned_date='2026-12-10',
            due_date='2026-12-15',
            status=MaintenanceStatus.PLANNED,
            assigned_to=self.tech_user_2,
            created_by=self.admin_user,
        )

        self.task_1 = MaintenanceTask.objects.create(
            schedule=self.sched_1,
            task_name='Hydraulic System Pressure Bleed',
            task_order=1,
            status=TaskStatus.PENDING,
        )
        self.task_2 = MaintenanceTask.objects.create(
            schedule=self.sched_1,
            task_name='Borescope Video Recording',
            task_order=2,
            status=TaskStatus.IN_PROGRESS,
        )

    def test_schedule_search(self):
        self.auth(self.admin_token)
        response = self.client.get('/api/maintenance/schedules/?search=Turbine')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.sched_1.id)

    def test_schedule_filter_by_status(self):
        self.auth(self.admin_token)
        response = self.client.get('/api/maintenance/schedules/?status=IN_PROGRESS')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.sched_1.id)

    def test_schedule_filter_by_priority(self):
        self.auth(self.admin_token)
        response = self.client.get('/api/maintenance/schedules/?priority=CRITICAL')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.sched_1.id)

    def test_schedule_filter_by_maintenance_type(self):
        self.auth(self.admin_token)
        response = self.client.get('/api/maintenance/schedules/?maintenance_type=PREVENTIVE')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.sched_2.id)

    def test_schedule_filter_by_aircraft(self):
        self.auth(self.admin_token)
        response = self.client.get(f'/api/maintenance/schedules/?aircraft={self.aircraft_1.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.sched_1.id)

    def test_schedule_filter_by_assigned_to(self):
        self.auth(self.admin_token)
        response = self.client.get(f'/api/maintenance/schedules/?assigned_to={self.tech_user_2.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.sched_2.id)

    def test_schedule_filter_by_dates(self):
        self.auth(self.admin_token)
        response = self.client.get('/api/maintenance/schedules/?planned_date=2026-12-01')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.sched_1.id)

    def test_task_search(self):
        self.auth(self.admin_token)
        response = self.client.get('/api/maintenance/tasks/?search=Hydraulic')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.task_1.id)

    def test_task_filter_by_status(self):
        self.auth(self.admin_token)
        response = self.client.get('/api/maintenance/tasks/?status=PENDING')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.task_1.id)

    def test_task_filter_by_schedule(self):
        self.auth(self.admin_token)
        response = self.client.get(f'/api/maintenance/tasks/?schedule={self.sched_1.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 2)

    def test_pagination(self):
        self.auth(self.admin_token)
        response = self.client.get('/api/maintenance/schedules/?page_size=1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIsNotNone(response.data['next'])

"""
Unit and integration tests for FlightFix Aircraft and Equipment Management (Epic P05-E04).
"""

from datetime import date
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.aircraft.models import Aircraft, AircraftStatus, Equipment, EquipmentStatus, EquipmentType

User = get_user_model()


class BaseAircraftTestCase(APITestCase):
    """
    Common setup providing pre-configured users with different roles and JWT tokens.
    """
    def setUp(self):
        # Create users for all roles
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@flightfix.com',
            password='Password123!',
            first_name='Admin',
            last_name='User',
            role=User.Role.ADMIN,
        )
        self.safety_user = User.objects.create_user(
            username='safety_user',
            email='safety@flightfix.com',
            password='Password123!',
            first_name='Safety',
            last_name='Officer',
            role=User.Role.SAFETY_OFFICER,
        )
        self.contracts_user = User.objects.create_user(
            username='contracts_user',
            email='contracts@flightfix.com',
            password='Password123!',
            first_name='Contracts',
            last_name='Manager',
            role=User.Role.CONTRACTS_MANAGER,
        )
        self.tech_user = User.objects.create_user(
            username='tech_user',
            email='tech@flightfix.com',
            password='Password123!',
            first_name='Field',
            last_name='Technician',
            role=User.Role.FIELD_TECHNICIAN,
        )

        # Generate JWT tokens
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        self.safety_token = str(RefreshToken.for_user(self.safety_user).access_token)
        self.contracts_token = str(RefreshToken.for_user(self.contracts_user).access_token)
        self.tech_token = str(RefreshToken.for_user(self.tech_user).access_token)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def unauth(self):
        self.client.credentials()


class AircraftAPITests(BaseAircraftTestCase):
    """
    Tests for Aircraft CRUD, validation, and permissions.
    """
    def setUp(self):
        super().setUp()
        self.aircraft_url = '/api/aircraft/'
        self.valid_aircraft_payload = {
            'registration_number': 'VT-FF101',
            'aircraft_type': 'Commercial Jet',
            'model': 'Boeing 737-800',
            'manufacturer': 'Boeing',
            'serial_number': 'MSN-30101',
            'status': AircraftStatus.ACTIVE,
            'manufacture_date': '2018-05-15',
            'service_entry_date': '2018-08-20',
            'notes': 'Operating on domestic trunk routes.',
        }

    def test_aircraft_creation_admin(self):
        self.auth(self.admin_token)
        response = self.client.post(self.aircraft_url, self.valid_aircraft_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['registration_number'], 'VT-FF101')
        self.assertEqual(response.data['manufacturer'], 'Boeing')
        self.assertTrue(Aircraft.objects.filter(registration_number='VT-FF101').exists())

    def test_aircraft_creation_safety_officer(self):
        self.auth(self.safety_token)
        response = self.client.post(self.aircraft_url, self.valid_aircraft_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['registration_number'], 'VT-FF101')

    def test_aircraft_creation_contracts_manager_forbidden(self):
        self.auth(self.contracts_token)
        response = self.client.post(self.aircraft_url, self.valid_aircraft_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_aircraft_creation_technician_forbidden(self):
        self.auth(self.tech_token)
        response = self.client.post(self.aircraft_url, self.valid_aircraft_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_aircraft_list_authenticated(self):
        Aircraft.objects.create(**self.valid_aircraft_payload)
        self.auth(self.tech_token)
        response = self.client.get(self.aircraft_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 1)

    def test_aircraft_detail_authenticated(self):
        aircraft = Aircraft.objects.create(**self.valid_aircraft_payload)
        self.auth(self.contracts_token)
        response = self.client.get(f'{self.aircraft_url}{aircraft.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], aircraft.id)
        self.assertEqual(response.data['registration_number'], 'VT-FF101')
        self.assertIn('equipment', response.data)

    def test_aircraft_update_admin(self):
        aircraft = Aircraft.objects.create(**self.valid_aircraft_payload)
        self.auth(self.admin_token)
        patch_payload = {'status': AircraftStatus.MAINTENANCE, 'notes': 'Scheduled C-Check.'}
        response = self.client.patch(f'{self.aircraft_url}{aircraft.id}/', patch_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        aircraft.refresh_from_db()
        self.assertEqual(aircraft.status, AircraftStatus.MAINTENANCE)
        self.assertEqual(aircraft.notes, 'Scheduled C-Check.')

    def test_aircraft_update_safety_officer(self):
        aircraft = Aircraft.objects.create(**self.valid_aircraft_payload)
        self.auth(self.safety_token)
        patch_payload = {'status': AircraftStatus.GROUNDED}
        response = self.client.patch(f'{self.aircraft_url}{aircraft.id}/', patch_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        aircraft.refresh_from_db()
        self.assertEqual(aircraft.status, AircraftStatus.GROUNDED)

    def test_aircraft_update_technician_forbidden(self):
        aircraft = Aircraft.objects.create(**self.valid_aircraft_payload)
        self.auth(self.tech_token)
        response = self.client.patch(f'{self.aircraft_url}{aircraft.id}/', {'status': AircraftStatus.GROUNDED}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_aircraft_delete_admin(self):
        aircraft = Aircraft.objects.create(**self.valid_aircraft_payload)
        self.auth(self.admin_token)
        response = self.client.delete(f'{self.aircraft_url}{aircraft.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Aircraft.objects.filter(id=aircraft.id).exists())

    def test_aircraft_delete_safety_officer_forbidden(self):
        aircraft = Aircraft.objects.create(**self.valid_aircraft_payload)
        self.auth(self.safety_token)
        response = self.client.delete(f'{self.aircraft_url}{aircraft.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Aircraft.objects.filter(id=aircraft.id).exists())

    def test_aircraft_delete_technician_forbidden(self):
        aircraft = Aircraft.objects.create(**self.valid_aircraft_payload)
        self.auth(self.tech_token)
        response = self.client.delete(f'{self.aircraft_url}{aircraft.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_registration_number(self):
        Aircraft.objects.create(**self.valid_aircraft_payload)
        self.auth(self.admin_token)
        duplicate_payload = self.valid_aircraft_payload.copy()
        duplicate_payload['serial_number'] = 'MSN-DIFFERENT'
        response = self.client.post(self.aircraft_url, duplicate_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('registration_number', response.data)

    def test_duplicate_serial_number(self):
        Aircraft.objects.create(**self.valid_aircraft_payload)
        self.auth(self.admin_token)
        duplicate_payload = self.valid_aircraft_payload.copy()
        duplicate_payload['registration_number'] = 'VT-DIFF'
        response = self.client.post(self.aircraft_url, duplicate_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('serial_number', response.data)

    def test_invalid_aircraft_dates(self):
        self.auth(self.admin_token)
        invalid_payload = self.valid_aircraft_payload.copy()
        invalid_payload['manufacture_date'] = '2020-01-01'
        invalid_payload['service_entry_date'] = '2019-01-01'  # Before manufacture!
        response = self.client.post(self.aircraft_url, invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('service_entry_date', response.data)

    def test_invalid_aircraft_status(self):
        self.auth(self.admin_token)
        invalid_payload = self.valid_aircraft_payload.copy()
        invalid_payload['status'] = 'INVALID_STATUS'
        response = self.client.post(self.aircraft_url, invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    def test_unauthenticated_aircraft_endpoints(self):
        self.unauth()
        response_list = self.client.get(self.aircraft_url)
        self.assertEqual(response_list.status_code, status.HTTP_401_UNAUTHORIZED)

        response_post = self.client.post(self.aircraft_url, self.valid_aircraft_payload, format='json')
        self.assertEqual(response_post.status_code, status.HTTP_401_UNAUTHORIZED)


class EquipmentAPITests(BaseAircraftTestCase):
    """
    Tests for Equipment CRUD, relationships, validation, and permissions.
    """
    def setUp(self):
        super().setUp()
        self.equipment_url = '/api/equipment/'
        self.aircraft = Aircraft.objects.create(
            registration_number='VT-EQ100',
            aircraft_type='Commercial Jet',
            model='Airbus A320neo',
            manufacturer='Airbus',
            serial_number='MSN-8801',
            status=AircraftStatus.ACTIVE,
        )
        self.valid_equipment_payload = {
            'equipment_code': 'EQ-ENG-501',
            'name': 'LEAP-1A Turbofan Engine',
            'equipment_type': EquipmentType.ENGINE,
            'manufacturer': 'CFM International',
            'serial_number': 'SN-LEAP-909',
            'status': EquipmentStatus.OPERATIONAL,
            'aircraft': self.aircraft.id,
            'location': 'Wing Position 1',
            'notes': 'Overhauled in Q3.',
        }

    def test_equipment_creation_admin(self):
        self.auth(self.admin_token)
        response = self.client.post(self.equipment_url, self.valid_equipment_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['equipment_code'], 'EQ-ENG-501')
        self.assertEqual(response.data['aircraft'], self.aircraft.id)
        self.assertTrue(Equipment.objects.filter(equipment_code='EQ-ENG-501').exists())

    def test_equipment_creation_safety_officer(self):
        self.auth(self.safety_token)
        response = self.client.post(self.equipment_url, self.valid_equipment_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['equipment_code'], 'EQ-ENG-501')

    def test_equipment_creation_technician_forbidden(self):
        self.auth(self.tech_token)
        response = self.client.post(self.equipment_url, self.valid_equipment_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_equipment_list_authenticated(self):
        Equipment.objects.create(
            equipment_code='EQ-ENG-501',
            name='LEAP-1A Turbofan Engine',
            equipment_type=EquipmentType.ENGINE,
            manufacturer='CFM International',
            status=EquipmentStatus.OPERATIONAL,
            aircraft=self.aircraft,
        )
        self.auth(self.tech_token)
        response = self.client.get(self.equipment_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(response.data['count'], 1)

    def test_equipment_detail_authenticated(self):
        equipment = Equipment.objects.create(
            equipment_code='EQ-ENG-501',
            name='LEAP-1A Turbofan Engine',
            equipment_type=EquipmentType.ENGINE,
            manufacturer='CFM International',
            status=EquipmentStatus.OPERATIONAL,
            aircraft=self.aircraft,
        )
        self.auth(self.contracts_token)
        response = self.client.get(f'{self.equipment_url}{equipment.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['equipment_code'], 'EQ-ENG-501')
        self.assertEqual(response.data['aircraft_registration'], 'VT-EQ100')

    def test_equipment_update_admin(self):
        equipment = Equipment.objects.create(
            equipment_code='EQ-ENG-501',
            name='LEAP-1A Turbofan Engine',
            equipment_type=EquipmentType.ENGINE,
            manufacturer='CFM International',
            status=EquipmentStatus.OPERATIONAL,
            aircraft=self.aircraft,
        )
        self.auth(self.admin_token)
        patch_payload = {'status': EquipmentStatus.UNDER_MAINTENANCE, 'location': 'Hangar 2 Test Bay'}
        response = self.client.patch(f'{self.equipment_url}{equipment.id}/', patch_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        equipment.refresh_from_db()
        self.assertEqual(equipment.status, EquipmentStatus.UNDER_MAINTENANCE)
        self.assertEqual(equipment.location, 'Hangar 2 Test Bay')

    def test_equipment_update_safety_officer(self):
        equipment = Equipment.objects.create(
            equipment_code='EQ-ENG-501',
            name='LEAP-1A Turbofan Engine',
            equipment_type=EquipmentType.ENGINE,
            manufacturer='CFM International',
            status=EquipmentStatus.OPERATIONAL,
            aircraft=self.aircraft,
        )
        self.auth(self.safety_token)
        patch_payload = {'status': EquipmentStatus.IN_STORAGE, 'aircraft': None}
        response = self.client.patch(f'{self.equipment_url}{equipment.id}/', patch_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        equipment.refresh_from_db()
        self.assertEqual(equipment.status, EquipmentStatus.IN_STORAGE)
        self.assertIsNone(equipment.aircraft)

    def test_equipment_update_contracts_manager_forbidden(self):
        equipment = Equipment.objects.create(
            equipment_code='EQ-ENG-501',
            name='LEAP-1A Turbofan Engine',
            equipment_type=EquipmentType.ENGINE,
            manufacturer='CFM International',
            status=EquipmentStatus.OPERATIONAL,
            aircraft=self.aircraft,
        )
        self.auth(self.contracts_token)
        response = self.client.patch(f'{self.equipment_url}{equipment.id}/', {'status': EquipmentStatus.DECOMMISSIONED}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_equipment_delete_admin(self):
        equipment = Equipment.objects.create(
            equipment_code='EQ-ENG-501',
            name='LEAP-1A Turbofan Engine',
            equipment_type=EquipmentType.ENGINE,
            manufacturer='CFM International',
            status=EquipmentStatus.OPERATIONAL,
            aircraft=self.aircraft,
        )
        self.auth(self.admin_token)
        response = self.client.delete(f'{self.equipment_url}{equipment.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Equipment.objects.filter(id=equipment.id).exists())

    def test_equipment_delete_safety_officer_forbidden(self):
        equipment = Equipment.objects.create(
            equipment_code='EQ-ENG-501',
            name='LEAP-1A Turbofan Engine',
            equipment_type=EquipmentType.ENGINE,
            manufacturer='CFM International',
            status=EquipmentStatus.OPERATIONAL,
            aircraft=self.aircraft,
        )
        self.auth(self.safety_token)
        response = self.client.delete(f'{self.equipment_url}{equipment.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Equipment.objects.filter(id=equipment.id).exists())

    def test_duplicate_equipment_code(self):
        Equipment.objects.create(
            equipment_code='EQ-ENG-501',
            name='LEAP-1A Turbofan Engine',
            equipment_type=EquipmentType.ENGINE,
            manufacturer='CFM International',
            status=EquipmentStatus.OPERATIONAL,
        )
        self.auth(self.admin_token)
        response = self.client.post(self.equipment_url, self.valid_equipment_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('equipment_code', response.data)

    def test_invalid_equipment_type(self):
        self.auth(self.admin_token)
        invalid_payload = self.valid_equipment_payload.copy()
        invalid_payload['equipment_type'] = 'WARP_DRIVE'
        response = self.client.post(self.equipment_url, invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('equipment_type', response.data)

    def test_unauthenticated_equipment_endpoints(self):
        self.unauth()
        response_list = self.client.get(self.equipment_url)
        self.assertEqual(response_list.status_code, status.HTTP_401_UNAUTHORIZED)

        response_post = self.client.post(self.equipment_url, self.valid_equipment_payload, format='json')
        self.assertEqual(response_post.status_code, status.HTTP_401_UNAUTHORIZED)


class AircraftFilterSearchTests(BaseAircraftTestCase):
    """
    Tests for search and query parameter filters.
    """
    def setUp(self):
        super().setUp()
        self.aircraft_boeing = Aircraft.objects.create(
            registration_number='VT-BOE01',
            aircraft_type='Commercial Jet',
            model='Boeing 777-300ER',
            manufacturer='Boeing',
            serial_number='MSN-77701',
            status=AircraftStatus.ACTIVE,
        )
        self.aircraft_airbus = Aircraft.objects.create(
            registration_number='VT-AIR02',
            aircraft_type='Regional Jet',
            model='Airbus A220-300',
            manufacturer='Airbus',
            serial_number='MSN-22002',
            status=AircraftStatus.MAINTENANCE,
        )

        self.equipment_engine = Equipment.objects.create(
            equipment_code='EQ-ENG-901',
            name='GE90 Turbofan Engine',
            equipment_type=EquipmentType.ENGINE,
            manufacturer='General Electric',
            status=EquipmentStatus.OPERATIONAL,
            aircraft=self.aircraft_boeing,
        )
        self.equipment_radar = Equipment.objects.create(
            equipment_code='EQ-AVN-202',
            name='Weather Radar System',
            equipment_type=EquipmentType.AVIONICS,
            manufacturer='Honeywell',
            status=EquipmentStatus.UNDER_MAINTENANCE,
            aircraft=self.aircraft_airbus,
        )

    def test_aircraft_search(self):
        self.auth(self.admin_token)
        response = self.client.get('/api/aircraft/?search=boeing')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['registration_number'], 'VT-BOE01')

    def test_aircraft_filter_status(self):
        self.auth(self.admin_token)
        response = self.client.get('/api/aircraft/?status=MAINTENANCE')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['registration_number'], 'VT-AIR02')

    def test_aircraft_filter_manufacturer(self):
        self.auth(self.admin_token)
        response = self.client.get('/api/aircraft/?manufacturer=Airbus')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['registration_number'], 'VT-AIR02')

    def test_equipment_search(self):
        self.auth(self.admin_token)
        response = self.client.get('/api/equipment/?search=GE90')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['equipment_code'], 'EQ-ENG-901')

    def test_equipment_filter_status(self):
        self.auth(self.admin_token)
        response = self.client.get('/api/equipment/?status=UNDER_MAINTENANCE')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['equipment_code'], 'EQ-AVN-202')

    def test_equipment_filter_type(self):
        self.auth(self.admin_token)
        response = self.client.get('/api/equipment/?equipment_type=AVIONICS')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['equipment_code'], 'EQ-AVN-202')

    def test_equipment_filter_by_aircraft(self):
        self.auth(self.admin_token)
        response = self.client.get(f'/api/equipment/?aircraft={self.aircraft_boeing.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['equipment_code'], 'EQ-ENG-901')

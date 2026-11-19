"""
Unit and integration tests for FlightFix User Management and Authentication.
"""

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.permissions import (
    IsAdmin,
    IsAdminOrSafetyOfficer,
    IsContractsManager,
    IsFieldTechnician,
    IsSafetyOfficer,
)

User = get_user_model()


class UserRegistrationTests(APITestCase):
    """
    Tests for POST /api/auth/register/
    """
    def setUp(self):
        self.register_url = '/api/auth/register/'
        self.valid_payload = {
            'username': 'tech_sarah',
            'email': 'sarah@flightfix.com',
            'password': 'SecurePassword123!',
            'first_name': 'Sarah',
            'last_name': 'Connor',
            'phone': '+1-555-0199',
            'role': User.Role.FIELD_TECHNICIAN,
        }

    def test_successful_registration(self):
        response = self.client.post(self.register_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'success')
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['username'], 'tech_sarah')
        self.assertEqual(response.data['user']['email'], 'sarah@flightfix.com')
        self.assertEqual(response.data['role'], User.Role.FIELD_TECHNICIAN)

        # Verify password is encrypted and not plain-text
        user = User.objects.get(username='tech_sarah')
        self.assertNotEqual(user.password, 'SecurePassword123!')
        self.assertTrue(user.check_password('SecurePassword123!'))

    def test_duplicate_email(self):
        self.client.post(self.register_url, self.valid_payload, format='json')
        duplicate_payload = self.valid_payload.copy()
        duplicate_payload['username'] = 'tech_another'

        response = self.client.post(self.register_url, duplicate_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_duplicate_username(self):
        self.client.post(self.register_url, self.valid_payload, format='json')
        duplicate_payload = self.valid_payload.copy()
        duplicate_payload['email'] = 'different@flightfix.com'

        response = self.client.post(self.register_url, duplicate_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_invalid_email(self):
        payload = self.valid_payload.copy()
        payload['email'] = 'not-a-valid-email'

        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_password_too_short(self):
        payload = self.valid_payload.copy()
        payload['password'] = 'short'

        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_invalid_phone_format(self):
        payload = self.valid_payload.copy()
        payload['phone'] = 'invalid_phone_number'

        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', response.data)

    def test_invalid_role(self):
        payload = self.valid_payload.copy()
        payload['role'] = 'INVALID_ROLE'

        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('role', response.data)

    def test_missing_required_fields(self):
        payload = {
            'username': 'incomplete_user',
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('password', response.data)
        self.assertIn('first_name', response.data)
        self.assertIn('last_name', response.data)


class UserLoginTests(APITestCase):
    """
    Tests for POST /api/auth/login/
    """
    def setUp(self):
        self.login_url = '/api/auth/login/'
        self.password = 'SecurePassword123!'
        self.user = User.objects.create_user(
            username='safety_alex',
            email='alex@flightfix.com',
            password=self.password,
            first_name='Alex',
            last_name='Vance',
            phone='+1-555-0144',
            role=User.Role.SAFETY_OFFICER,
        )

    def test_successful_login_with_username(self):
        payload = {
            'username': 'safety_alex',
            'password': self.password,
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['role'], User.Role.SAFETY_OFFICER)
        self.assertEqual(response.data['user']['username'], 'safety_alex')

    def test_successful_login_with_email(self):
        payload = {
            'username': 'alex@flightfix.com',
            'password': self.password,
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], 'alex@flightfix.com')

    def test_invalid_login_wrong_password(self):
        payload = {
            'username': 'safety_alex',
            'password': 'WrongPassword999!',
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_login_nonexistent_user(self):
        payload = {
            'username': 'nonexistent_user',
            'password': self.password,
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()

        payload = {
            'username': 'safety_alex',
            'password': self.password,
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CurrentUserProfileTests(APITestCase):
    """
    Tests for GET /api/auth/me/
    """
    def setUp(self):
        self.me_url = '/api/auth/me/'
        self.user = User.objects.create_user(
            username='contracts_claire',
            email='claire@flightfix.com',
            password='SecurePassword123!',
            first_name='Claire',
            last_name='Redfield',
            role=User.Role.CONTRACTS_MANAGER,
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_authenticated_me(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'contracts_claire')
        self.assertEqual(response.data['email'], 'claire@flightfix.com')
        self.assertEqual(response.data['role'], User.Role.CONTRACTS_MANAGER)
        self.assertEqual(response.data['first_name'], 'Claire')
        self.assertEqual(response.data['last_name'], 'Redfield')

    def test_unauthenticated_me(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class JWTRefreshTests(APITestCase):
    """
    Tests for POST /api/auth/refresh/
    """
    def setUp(self):
        self.refresh_url = '/api/auth/refresh/'
        self.user = User.objects.create_user(
            username='admin_boss',
            email='boss@flightfix.com',
            password='SecurePassword123!',
            role=User.Role.ADMIN,
        )
        self.refresh = RefreshToken.for_user(self.user)

    def test_jwt_refresh_success(self):
        payload = {'refresh': str(self.refresh)}
        response = self.client.post(self.refresh_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_jwt_refresh_invalid(self):
        payload = {'refresh': 'corrupted_invalid_refresh_token'}
        response = self.client.post(self.refresh_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RolePermissionTests(TestCase):
    """
    Tests for role-based permission classes.
    """
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create_user(
            username='perm_admin',
            email='admin@flightfix.com',
            password='Password123!',
            role=User.Role.ADMIN,
        )
        self.safety_user = User.objects.create_user(
            username='perm_safety',
            email='safety@flightfix.com',
            password='Password123!',
            role=User.Role.SAFETY_OFFICER,
        )
        self.contracts_user = User.objects.create_user(
            username='perm_contracts',
            email='contracts@flightfix.com',
            password='Password123!',
            role=User.Role.CONTRACTS_MANAGER,
        )
        self.technician_user = User.objects.create_user(
            username='perm_tech',
            email='tech@flightfix.com',
            password='Password123!',
            role=User.Role.FIELD_TECHNICIAN,
        )
        self.superuser = User.objects.create_superuser(
            username='perm_super',
            email='super@flightfix.com',
            password='Password123!',
        )

    def _build_request(self, user):
        request = self.factory.get('/')
        request.user = user
        return request

    def test_is_admin_permission(self):
        perm = IsAdmin()
        self.assertTrue(perm.has_permission(self._build_request(self.admin_user), None))
        self.assertFalse(perm.has_permission(self._build_request(self.safety_user), None))
        self.assertFalse(perm.has_permission(self._build_request(self.technician_user), None))
        self.assertTrue(perm.has_permission(self._build_request(self.superuser), None))

    def test_is_safety_officer_permission(self):
        perm = IsSafetyOfficer()
        self.assertTrue(perm.has_permission(self._build_request(self.safety_user), None))
        self.assertFalse(perm.has_permission(self._build_request(self.admin_user), None))
        self.assertFalse(perm.has_permission(self._build_request(self.technician_user), None))
        self.assertTrue(perm.has_permission(self._build_request(self.superuser), None))

    def test_is_contracts_manager_permission(self):
        perm = IsContractsManager()
        self.assertTrue(perm.has_permission(self._build_request(self.contracts_user), None))
        self.assertFalse(perm.has_permission(self._build_request(self.admin_user), None))
        self.assertFalse(perm.has_permission(self._build_request(self.technician_user), None))
        self.assertTrue(perm.has_permission(self._build_request(self.superuser), None))

    def test_is_field_technician_permission(self):
        perm = IsFieldTechnician()
        self.assertTrue(perm.has_permission(self._build_request(self.technician_user), None))
        self.assertFalse(perm.has_permission(self._build_request(self.contracts_user), None))
        self.assertFalse(perm.has_permission(self._build_request(self.admin_user), None))
        self.assertTrue(perm.has_permission(self._build_request(self.superuser), None))

    def test_is_admin_or_safety_officer_permission(self):
        perm = IsAdminOrSafetyOfficer()
        self.assertTrue(perm.has_permission(self._build_request(self.admin_user), None))
        self.assertTrue(perm.has_permission(self._build_request(self.safety_user), None))
        self.assertFalse(perm.has_permission(self._build_request(self.contracts_user), None))
        self.assertFalse(perm.has_permission(self._build_request(self.technician_user), None))
        self.assertTrue(perm.has_permission(self._build_request(self.superuser), None))

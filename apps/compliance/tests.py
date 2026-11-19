"""
Unit and integration tests for FlightFix Airworthiness & Regulatory Compliance module.
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.aircraft.models import Aircraft, AircraftStatus
from apps.work_orders.models import (
    WorkOrder,
    WorkOrderType,
    WorkOrderPriority,
    WorkOrderStatus,
)
from apps.compliance.models import (
    ComplianceRequirement,
    ComplianceRecord,
    RequirementStatus,
    RequirementPriority,
    RegulationType,
    VerificationStatus,
)

User = get_user_model()


class BaseComplianceTestCase(APITestCase):
    """
    Common setup for compliance module testing across all 4 roles.
    """
    def setUp(self):
        # 1. Setup Users for all 4 roles
        self.admin_user = User.objects.create_user(
            username='comp_admin',
            email='comp_admin@flightfix.com',
            password='Password123!',
            first_name='Admin',
            last_name='Officer',
            role=User.Role.ADMIN,
        )
        self.safety_user = User.objects.create_user(
            username='comp_safety',
            email='comp_safety@flightfix.com',
            password='Password123!',
            first_name='Safety',
            last_name='Lead',
            role=User.Role.SAFETY_OFFICER,
        )
        self.contracts_user = User.objects.create_user(
            username='comp_contracts',
            email='comp_contracts@flightfix.com',
            password='Password123!',
            first_name='Contracts',
            last_name='Manager',
            role=User.Role.CONTRACTS_MANAGER,
        )
        self.tech_user_1 = User.objects.create_user(
            username='comp_tech_1',
            email='comp_tech1@flightfix.com',
            password='Password123!',
            first_name='Technician',
            last_name='One',
            role=User.Role.FIELD_TECHNICIAN,
        )
        self.tech_user_2 = User.objects.create_user(
            username='comp_tech_2',
            email='comp_tech2@flightfix.com',
            password='Password123!',
            first_name='Technician',
            last_name='Two',
            role=User.Role.FIELD_TECHNICIAN,
        )

        # 2. Setup JWT Tokens
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        self.safety_token = str(RefreshToken.for_user(self.safety_user).access_token)
        self.contracts_token = str(RefreshToken.for_user(self.contracts_user).access_token)
        self.tech_token_1 = str(RefreshToken.for_user(self.tech_user_1).access_token)
        self.tech_token_2 = str(RefreshToken.for_user(self.tech_user_2).access_token)

        # 3. Aircraft prerequisites
        self.aircraft_1 = Aircraft.objects.create(
            registration_number='VT-CMP-101',
            aircraft_type='Commercial Jet',
            model='Boeing 737-800',
            manufacturer='Boeing',
            serial_number='MSN-CMP-101',
            status=AircraftStatus.ACTIVE,
        )
        self.aircraft_2 = Aircraft.objects.create(
            registration_number='VT-CMP-202',
            aircraft_type='Commercial Jet',
            model='Airbus A321neo',
            manufacturer='Airbus',
            serial_number='MSN-CMP-202',
            status=AircraftStatus.ACTIVE,
        )

        # 4. WorkOrder linking tech_user_1 to aircraft_1
        self.work_order_1 = WorkOrder.objects.create(
            work_order_number='WO-COMP-2026-001',
            aircraft=self.aircraft_1,
            title='Perform AD Wing Spar NDT Inspection',
            description='Mandatory FAA AD compliance.',
            work_order_type=WorkOrderType.INSPECTION,
            priority=WorkOrderPriority.CRITICAL,
            status=WorkOrderStatus.IN_PROGRESS,
            assigned_to=self.tech_user_1,
            created_by=self.admin_user,
            planned_start_date=timezone.now().date(),
            planned_completion_date=timezone.now().date() + timezone.timedelta(days=3),
        )

        # 5. Sample ComplianceRequirement on aircraft_1
        self.today = timezone.now().date()
        self.sample_requirement = ComplianceRequirement.objects.create(
            requirement_code='AD-2026-FAA-01',
            title='Wing Spar Ultrasonic Inspection',
            description='Mandatory repetitive eddy-current and ultrasonic inspection of rear wing spar.',
            regulation_type=RegulationType.AIRWORTHINESS_DIRECTIVE,
            issuing_authority='Federal Aviation Administration (FAA)',
            aircraft=self.aircraft_1,
            effective_date=self.today - timezone.timedelta(days=10),
            due_date=self.today + timezone.timedelta(days=30),
            status=RequirementStatus.IN_PROGRESS,
            priority=RequirementPriority.CRITICAL,
            assigned_to=self.safety_user,
            created_by=self.admin_user,
        )

        # 6. Sample ComplianceRecord
        self.sample_record = ComplianceRecord.objects.create(
            requirement=self.sample_requirement,
            aircraft=self.aircraft_1,
            verification_status=VerificationStatus.PENDING,
            evidence_reference='LOGBOOK-ENTRY-2026-042',
            findings='Awaiting NDT probe calibration.',
            remarks='Testing scheduled for Hangar Bay 1.',
        )

    def auth_as(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def unauth(self):
        self.client.credentials()


class ComplianceModelTests(BaseComplianceTestCase):
    """
    Tests for ComplianceRequirement and ComplianceRecord model validations and lifecycle logic.
    """
    def test_requirement_code_normalized_uppercase(self):
        req = ComplianceRequirement.objects.create(
            requirement_code='  sb-boeing-737-57-01  ',
            title='Rudder Actuator Lubrication',
            description='Service bulletin lubrication interval reduction.',
            regulation_type=RegulationType.SERVICE_BULLETIN,
            issuing_authority='Boeing Commercial Airplanes',
            aircraft=self.aircraft_1,
            effective_date=self.today,
            due_date=self.today + timezone.timedelta(days=60),
            created_by=self.admin_user,
        )
        self.assertEqual(req.requirement_code, 'SB-BOEING-737-57-01')

    def test_duplicate_requirement_code_rejected(self):
        with self.assertRaises(ValidationError):
            dup = ComplianceRequirement(
                requirement_code='ad-2026-faa-01',  # same code lowercase
                title='Duplicate AD',
                description='Duplicate test',
                regulation_type=RegulationType.AIRWORTHINESS_DIRECTIVE,
                issuing_authority='FAA',
                aircraft=self.aircraft_1,
                effective_date=self.today,
                due_date=self.today + timezone.timedelta(days=10),
                created_by=self.admin_user,
            )
            dup.save()

    def test_due_date_prior_to_effective_date_rejected(self):
        with self.assertRaises(ValidationError):
            invalid_dates = ComplianceRequirement(
                requirement_code='AD-FAIL-DATES',
                title='Invalid Dates AD',
                description='Due date before effective date',
                regulation_type=RegulationType.AIRWORTHINESS_DIRECTIVE,
                issuing_authority='FAA',
                aircraft=self.aircraft_1,
                effective_date=self.today,
                due_date=self.today - timezone.timedelta(days=5),  # 5 days prior
                created_by=self.admin_user,
            )
            invalid_dates.save()

    def test_expired_status_automatically_identified(self):
        req_expired = ComplianceRequirement.objects.create(
            requirement_code='AD-TEST-EXPIRED',
            title='Lapsed Inspection AD',
            description='Inspection window has passed',
            regulation_type=RegulationType.AIRWORTHINESS_DIRECTIVE,
            issuing_authority='DGCA',
            aircraft=self.aircraft_1,
            effective_date=self.today - timezone.timedelta(days=60),
            due_date=self.today - timezone.timedelta(days=5),  # lapsed 5 days ago
            status=RequirementStatus.OPEN,
            created_by=self.admin_user,
        )
        # Status should automatically become EXPIRED
        self.assertEqual(req_expired.status, RequirementStatus.EXPIRED)

    def test_record_auto_aligns_aircraft_with_requirement(self):
        record = ComplianceRecord(
            requirement=self.sample_requirement,
            evidence_reference='REF-AUTO-AIRCRAFT',
            verification_status=VerificationStatus.PENDING,
        )
        record.save()
        self.assertEqual(record.aircraft, self.sample_requirement.aircraft)

    def test_mismatched_record_aircraft_rejected(self):
        with self.assertRaises(ValidationError):
            mismatch_record = ComplianceRecord(
                requirement=self.sample_requirement,
                aircraft=self.aircraft_2,  # different aircraft than requirement.aircraft_1
                evidence_reference='REF-MISMATCH',
                verification_status=VerificationStatus.PENDING,
            )
            mismatch_record.save()

    def test_verified_record_without_verifier_rejected(self):
        with self.assertRaises(ValidationError):
            rec = ComplianceRecord(
                requirement=self.sample_requirement,
                aircraft=self.aircraft_1,
                evidence_reference='REF-FAIL-VERIFY',
                verification_status=VerificationStatus.VERIFIED,
                verified_by=None,  # missing required certifier
            )
            rec.save()

    def test_verified_record_transitions_requirement_to_compliant(self):
        self.assertEqual(self.sample_requirement.status, RequirementStatus.IN_PROGRESS)
        ComplianceRecord.objects.create(
            requirement=self.sample_requirement,
            aircraft=self.aircraft_1,
            evidence_reference='CRS-2026-FINAL-VERIFY',
            verification_status=VerificationStatus.VERIFIED,
            verified_by=self.safety_user,
            verified_at=timezone.now(),
        )
        self.sample_requirement.refresh_from_db()
        self.assertEqual(self.sample_requirement.status, RequirementStatus.COMPLIANT)


class ComplianceRequirementAPITests(BaseComplianceTestCase):
    """
    Tests for ComplianceRequirement REST API endpoints: RBAC, CRUD, search, filter, pagination.
    """
    def test_unauthenticated_request_rejected(self):
        self.unauth()
        response = self.client.get('/api/compliance/requirements/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_create_requirement(self):
        self.auth_as(self.admin_token)
        payload = {
            'requirement_code': 'AD-2026-FAA-02',
            'title': 'Engine Pylon Fitting Bolt Torque',
            'description': 'Mandatory torque verification on forward engine pylon pins.',
            'regulation_type': 'AIRWORTHINESS_DIRECTIVE',
            'issuing_authority': 'FAA',
            'aircraft': self.aircraft_1.id,
            'effective_date': str(self.today),
            'due_date': str(self.today + timezone.timedelta(days=45)),
            'priority': 'HIGH',
            'status': 'OPEN',
        }
        response = self.client.post('/api/compliance/requirements/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['requirement_code'], 'AD-2026-FAA-02')
        self.assertEqual(response.data['created_by_username'], self.admin_user.username)

    def test_safety_officer_can_create_and_update_requirement(self):
        self.auth_as(self.safety_token)
        payload = {
            'requirement_code': 'SB-A321-27-0099',
            'title': 'Elevator Servo Actuator Mod',
            'description': 'Software update on flight control secondary computers.',
            'regulation_type': 'SERVICE_BULLETIN',
            'issuing_authority': 'Airbus',
            'aircraft': self.aircraft_2.id,
            'effective_date': str(self.today),
            'due_date': str(self.today + timezone.timedelta(days=90)),
            'priority': 'MEDIUM',
            'status': 'OPEN',
        }
        create_resp = self.client.post('/api/compliance/requirements/', payload, format='json')
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        req_id = create_resp.data['id']

        # Update
        patch_resp = self.client.patch(
            f'/api/compliance/requirements/{req_id}/',
            {'priority': 'HIGH', 'notes': 'Elevated priority after review.'},
            format='json'
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)

        # Delete must be forbidden (403)
        del_resp = self.client.delete(f'/api/compliance/requirements/{req_id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_contracts_manager_read_only(self):
        self.auth_as(self.contracts_token)
        list_resp = self.client.get('/api/compliance/requirements/')
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)

        detail_resp = self.client.get(f'/api/compliance/requirements/{self.sample_requirement.id}/')
        self.assertEqual(detail_resp.status_code, status.HTTP_200_OK)

        # POST / PUT / PATCH / DELETE forbidden
        post_resp = self.client.post('/api/compliance/requirements/', {'requirement_code': 'FAIL'}, format='json')
        self.assertEqual(post_resp.status_code, status.HTTP_403_FORBIDDEN)

        del_resp = self.client.delete(f'/api/compliance/requirements/{self.sample_requirement.id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_field_technician_can_view_relevant_requirements_only(self):
        # tech_user_1 is assigned to work_order_1 on aircraft_1 -> Can view sample_requirement
        self.auth_as(self.tech_token_1)
        resp_tech1 = self.client.get(f'/api/compliance/requirements/{self.sample_requirement.id}/')
        self.assertEqual(resp_tech1.status_code, status.HTTP_200_OK)

        # tech_user_2 has no work on aircraft_1 -> Cannot view in list or detail
        self.auth_as(self.tech_token_2)
        resp_tech2_list = self.client.get('/api/compliance/requirements/')
        self.assertEqual(resp_tech2_list.status_code, status.HTTP_200_OK)
        results = resp_tech2_list.data.get('results', resp_tech2_list.data)
        self.assertFalse(any(r['id'] == self.sample_requirement.id for r in results))

        resp_tech2_detail = self.client.get(f'/api/compliance/requirements/{self.sample_requirement.id}/')
        self.assertIn(resp_tech2_detail.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_admin_can_delete_requirement(self):
        self.auth_as(self.admin_token)
        req = ComplianceRequirement.objects.create(
            requirement_code='AD-TO-DELETE',
            title='Delete Me',
            description='Test',
            regulation_type=RegulationType.OTHER,
            issuing_authority='QA',
            aircraft=self.aircraft_1,
            effective_date=self.today,
            due_date=self.today + timezone.timedelta(days=10),
            created_by=self.admin_user,
        )
        response = self.client.delete(f'/api/compliance/requirements/{req.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_due_date_prior_to_effective_date_api_rejected(self):
        self.auth_as(self.admin_token)
        payload = {
            'requirement_code': 'AD-FAIL-API-DATES',
            'title': 'Invalid Date Range',
            'description': 'Dates are backwards',
            'regulation_type': 'INTERNAL_POLICY',
            'issuing_authority': 'Internal QA',
            'aircraft': self.aircraft_1.id,
            'effective_date': str(self.today),
            'due_date': str(self.today - timezone.timedelta(days=1)),
        }
        response = self.client.post('/api/compliance/requirements/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('due_date', response.data)

    def test_search_and_filtering_requirements(self):
        self.auth_as(self.admin_token)
        # Search
        resp_search = self.client.get(f'/api/compliance/requirements/?search={self.sample_requirement.requirement_code}')
        self.assertEqual(resp_search.status_code, status.HTTP_200_OK)
        results = resp_search.data.get('results', resp_search.data)
        self.assertTrue(len(results) >= 1)

        # Filter by aircraft
        resp_aircraft = self.client.get(f'/api/compliance/requirements/?aircraft={self.aircraft_1.id}')
        self.assertEqual(resp_aircraft.status_code, status.HTTP_200_OK)
        for r in resp_aircraft.data.get('results', resp_aircraft.data):
            self.assertEqual(r['aircraft'], self.aircraft_1.id)

        # Filter by priority
        resp_prio = self.client.get('/api/compliance/requirements/?priority=CRITICAL')
        self.assertEqual(resp_prio.status_code, status.HTTP_200_OK)
        for r in resp_prio.data.get('results', resp_prio.data):
            self.assertEqual(r['priority'], 'CRITICAL')


class ComplianceRecordAPITests(BaseComplianceTestCase):
    """
    Tests for ComplianceRecord REST API endpoints: verification, evidence, certifier checks, and role permissions.
    """
    def test_unauthenticated_record_rejected(self):
        self.unauth()
        response = self.client.get('/api/compliance/records/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_create_compliance_record(self):
        self.auth_as(self.admin_token)
        payload = {
            'requirement': self.sample_requirement.id,
            'verification_status': 'PENDING',
            'evidence_reference': 'NDT-REPORT-2026-88',
            'findings': 'Ultrasonic baseline established.',
            'remarks': 'Probe scan normal.',
        }
        response = self.client.post('/api/compliance/records/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['requirement_code'], self.sample_requirement.requirement_code)

    def test_safety_officer_can_verify_compliance_record(self):
        self.auth_as(self.safety_token)
        payload = {
            'requirement': self.sample_requirement.id,
            'verification_status': 'VERIFIED',
            'verified_by': self.safety_user.id,
            'verified_at': timezone.now().isoformat(),
            'evidence_reference': 'CRS-2026-CERT-01',
            'findings': 'No cracks or corrosion found in rear spar web.',
            'remarks': 'Complies in full with AD-2026-FAA-01 paragraph (g).',
        }
        response = self.client.post('/api/compliance/records/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['verification_status'], 'VERIFIED')
        self.assertEqual(response.data['verified_by_username'], self.safety_user.username)

        # Ensure requirement transitioned to COMPLIANT
        self.sample_requirement.refresh_from_db()
        self.assertEqual(self.sample_requirement.status, RequirementStatus.COMPLIANT)

    def test_failed_verification_record_stores_findings_and_corrective_action(self):
        self.auth_as(self.safety_token)
        payload = {
            'requirement': self.sample_requirement.id,
            'verification_status': 'FAILED',
            'evidence_reference': 'QA-AUDIT-FAILED-01',
            'findings': 'Micro-fissure detected at station 242.0.',
            'corrective_action': 'Engineering order EO-737-57-09 required before flight.',
        }
        response = self.client.post('/api/compliance/records/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['verification_status'], 'FAILED')
        self.assertEqual(response.data['findings'], 'Micro-fissure detected at station 242.0.')

    def test_verified_record_without_verifier_api_rejected(self):
        self.auth_as(self.admin_token)
        payload = {
            'requirement': self.sample_requirement.id,
            'verification_status': 'VERIFIED',
            'verified_by': None,
            'evidence_reference': 'REF-NO-VERIFIER',
        }
        response = self.client.post('/api/compliance/records/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('verified_by', response.data)

    def test_field_technician_can_view_assigned_compliance_record(self):
        self.auth_as(self.tech_token_1)
        response = self.client.get(f'/api/compliance/records/{self.sample_record.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Tech cannot delete (403)
        del_resp = self.client.delete(f'/api/compliance/records/{self.sample_record.id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_403_FORBIDDEN)

        # Tech 2 (not assigned) cannot view
        self.auth_as(self.tech_token_2)
        resp_tech2 = self.client.get(f'/api/compliance/records/{self.sample_record.id}/')
        self.assertIn(resp_tech2.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_filter_records_by_status_and_aircraft(self):
        self.auth_as(self.admin_token)
        resp = self.client.get(f'/api/compliance/records/?aircraft={self.aircraft_1.id}&verification_status=PENDING')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        self.assertTrue(len(results) >= 1)
        for r in results:
            self.assertEqual(r['verification_status'], 'PENDING')
            self.assertEqual(r['aircraft'], self.aircraft_1.id)

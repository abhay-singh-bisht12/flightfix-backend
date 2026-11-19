"""
Unit and integration tests for FlightFix Spare Parts Inventory module.
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.inventory.models import (
    SparePart,
    InventoryTransaction,
    StockStatus,
    PartCategory,
    TransactionType,
)

User = get_user_model()


class BaseInventoryTestCase(APITestCase):
    """
    Common setup providing pre-configured users with different roles, JWT tokens, and sample parts.
    """
    def setUp(self):
        # 1. Setup Users for all 4 roles
        self.admin_user = User.objects.create_user(
            username='inv_admin',
            email='inv_admin@flightfix.com',
            password='Password123!',
            first_name='Admin',
            last_name='User',
            role=User.Role.ADMIN,
        )
        self.safety_user = User.objects.create_user(
            username='inv_safety',
            email='inv_safety@flightfix.com',
            password='Password123!',
            first_name='Safety',
            last_name='Officer',
            role=User.Role.SAFETY_OFFICER,
        )
        self.contracts_user = User.objects.create_user(
            username='inv_contracts',
            email='inv_contracts@flightfix.com',
            password='Password123!',
            first_name='Contracts',
            last_name='Manager',
            role=User.Role.CONTRACTS_MANAGER,
        )
        self.tech_user = User.objects.create_user(
            username='inv_tech',
            email='inv_tech@flightfix.com',
            password='Password123!',
            first_name='Field',
            last_name='Technician',
            role=User.Role.FIELD_TECHNICIAN,
        )

        # 2. Setup JWT Tokens
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        self.safety_token = str(RefreshToken.for_user(self.safety_user).access_token)
        self.contracts_token = str(RefreshToken.for_user(self.contracts_user).access_token)
        self.tech_token = str(RefreshToken.for_user(self.tech_user).access_token)

        # 3. Create Sample Spare Part
        self.sample_part = SparePart.objects.create(
            part_number='PN-HYD-5001',
            name='Hydraulic Actuator Seal Kit',
            description='High pressure fluorocarbon seal set.',
            category=PartCategory.HYDRAULICS,
            manufacturer='Parker Aerospace',
            manufacturer_part_number='PK-5001-A',
            quantity_in_stock=20,
            minimum_stock_level=5,
            unit_price=Decimal('150.00'),
            location='Hangar-1 / Bin-H12',
            supplier='Aero Supply Co.',
        )

    def auth_as(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def unauth(self):
        self.client.credentials()


class SparePartModelTests(BaseInventoryTestCase):
    """
    Tests for SparePart model validation and business logic.
    """
    def test_part_number_normalized_uppercase(self):
        part = SparePart.objects.create(
            part_number='  pn-avionics-101  ',
            name='VHF Radio Transceiver',
            category=PartCategory.AVIONICS,
            manufacturer='Rockwell Collins',
            quantity_in_stock=10,
            minimum_stock_level=2,
            unit_price=Decimal('4500.00'),
            location='Hangar-2 / Bin-A01',
        )
        self.assertEqual(part.part_number, 'PN-AVIONICS-101')

    def test_unique_part_number_validation(self):
        with self.assertRaises(ValidationError):
            part_duplicate = SparePart(
                part_number='pn-hyd-5001',  # same number in lowercase
                name='Duplicate Part',
                category=PartCategory.HYDRAULICS,
                manufacturer='Parker',
                quantity_in_stock=5,
                minimum_stock_level=1,
                unit_price=Decimal('50.00'),
                location='Bin-B1',
            )
            part_duplicate.save()

    def test_negative_quantity_in_stock_rejected(self):
        with self.assertRaises(ValidationError):
            part = SparePart(
                part_number='PN-TEST-NEG-QTY',
                name='Test Part',
                category=PartCategory.OTHER,
                manufacturer='Test Mfg',
                quantity_in_stock=-5,
                minimum_stock_level=0,
                unit_price=Decimal('10.00'),
                location='Bin-T1',
            )
            part.save()

    def test_negative_minimum_stock_level_rejected(self):
        with self.assertRaises(ValidationError):
            part = SparePart(
                part_number='PN-TEST-NEG-MIN',
                name='Test Part',
                category=PartCategory.OTHER,
                manufacturer='Test Mfg',
                quantity_in_stock=10,
                minimum_stock_level=-2,
                unit_price=Decimal('10.00'),
                location='Bin-T2',
            )
            part.save()

    def test_negative_unit_price_rejected(self):
        with self.assertRaises(ValidationError):
            part = SparePart(
                part_number='PN-TEST-NEG-PRICE',
                name='Test Part',
                category=PartCategory.OTHER,
                manufacturer='Test Mfg',
                quantity_in_stock=10,
                minimum_stock_level=2,
                unit_price=Decimal('-15.00'),
                location='Bin-T3',
            )
            part.save()

    def test_stock_status_out_of_stock_calculated(self):
        part = SparePart.objects.create(
            part_number='PN-TEST-OUT',
            name='Zero Stock Part',
            category=PartCategory.OTHER,
            manufacturer='Test Mfg',
            quantity_in_stock=0,
            minimum_stock_level=5,
            unit_price=Decimal('25.00'),
            location='Bin-T4',
        )
        self.assertEqual(part.status, StockStatus.OUT_OF_STOCK)

    def test_stock_status_low_stock_calculated(self):
        part = SparePart.objects.create(
            part_number='PN-TEST-LOW',
            name='Low Stock Part',
            category=PartCategory.OTHER,
            manufacturer='Test Mfg',
            quantity_in_stock=4,
            minimum_stock_level=5,
            unit_price=Decimal('25.00'),
            location='Bin-T5',
        )
        self.assertEqual(part.status, StockStatus.LOW_STOCK)

    def test_stock_status_in_stock_calculated(self):
        part = SparePart.objects.create(
            part_number='PN-TEST-INSTOCK',
            name='In Stock Part',
            category=PartCategory.OTHER,
            manufacturer='Test Mfg',
            quantity_in_stock=10,
            minimum_stock_level=5,
            unit_price=Decimal('25.00'),
            location='Bin-T6',
        )
        self.assertEqual(part.status, StockStatus.IN_STOCK)

    def test_discontinued_status_preserved(self):
        part = SparePart.objects.create(
            part_number='PN-TEST-DISC',
            name='Discontinued Part',
            category=PartCategory.OTHER,
            manufacturer='Test Mfg',
            quantity_in_stock=100,
            minimum_stock_level=5,
            unit_price=Decimal('25.00'),
            location='Bin-T7',
            status=StockStatus.DISCONTINUED,
        )
        # Re-save with 0 quantity - should remain DISCONTINUED
        part.quantity_in_stock = 0
        part.save()
        self.assertEqual(part.status, StockStatus.DISCONTINUED)


class InventoryTransactionModelTests(BaseInventoryTestCase):
    """
    Tests for InventoryTransaction model and stock updating logic.
    """
    def test_receipt_transaction_increases_stock(self):
        initial_stock = self.sample_part.quantity_in_stock  # 20
        InventoryTransaction.objects.create(
            spare_part=self.sample_part,
            transaction_type=TransactionType.RECEIPT,
            quantity=15,
            reference='PO-2026-901',
            performed_by=self.admin_user,
        )
        self.sample_part.refresh_from_db()
        self.assertEqual(self.sample_part.quantity_in_stock, initial_stock + 15)
        self.assertEqual(self.sample_part.status, StockStatus.IN_STOCK)

    def test_issue_transaction_decreases_stock(self):
        initial_stock = self.sample_part.quantity_in_stock  # 20
        InventoryTransaction.objects.create(
            spare_part=self.sample_part,
            transaction_type=TransactionType.ISSUE,
            quantity=8,
            reference='WO-2026-0044',
            performed_by=self.admin_user,
        )
        self.sample_part.refresh_from_db()
        self.assertEqual(self.sample_part.quantity_in_stock, initial_stock - 8)
        self.assertEqual(self.sample_part.status, StockStatus.IN_STOCK)

    def test_return_transaction_increases_stock(self):
        initial_stock = self.sample_part.quantity_in_stock  # 20
        InventoryTransaction.objects.create(
            spare_part=self.sample_part,
            transaction_type=TransactionType.RETURN,
            quantity=3,
            reference='WO-2026-0044-RET',
            performed_by=self.admin_user,
        )
        self.sample_part.refresh_from_db()
        self.assertEqual(self.sample_part.quantity_in_stock, initial_stock + 3)

    def test_adjustment_transaction_sets_stock(self):
        InventoryTransaction.objects.create(
            spare_part=self.sample_part,
            transaction_type=TransactionType.ADJUSTMENT,
            quantity=50,
            reference='AUDIT-2026-Q4',
            performed_by=self.admin_user,
        )
        self.sample_part.refresh_from_db()
        self.assertEqual(self.sample_part.quantity_in_stock, 50)
        self.assertEqual(self.sample_part.status, StockStatus.IN_STOCK)

    def test_issue_exceeding_stock_raises_validation_error(self):
        current_stock = self.sample_part.quantity_in_stock  # 20
        with self.assertRaises(ValidationError):
            InventoryTransaction.objects.create(
                spare_part=self.sample_part,
                transaction_type=TransactionType.ISSUE,
                quantity=current_stock + 5,  # 25 > 20
                reference='WO-EXCESS',
                performed_by=self.admin_user,
            )
        # Ensure stock remained unchanged
        self.sample_part.refresh_from_db()
        self.assertEqual(self.sample_part.quantity_in_stock, current_stock)

    def test_zero_quantity_transaction_rejected(self):
        with self.assertRaises(ValidationError):
            InventoryTransaction.objects.create(
                spare_part=self.sample_part,
                transaction_type=TransactionType.RECEIPT,
                quantity=0,
                reference='PO-INVALID',
                performed_by=self.admin_user,
            )

    def test_transaction_updates_stock_status_to_out_of_stock(self):
        # Issue all remaining stock (20)
        InventoryTransaction.objects.create(
            spare_part=self.sample_part,
            transaction_type=TransactionType.ISSUE,
            quantity=20,
            reference='WO-DEPLETE',
            performed_by=self.admin_user,
        )
        self.sample_part.refresh_from_db()
        self.assertEqual(self.sample_part.quantity_in_stock, 0)
        self.assertEqual(self.sample_part.status, StockStatus.OUT_OF_STOCK)

    def test_transaction_updates_stock_status_to_low_stock(self):
        # Issue 16, leaving 4 (which is <= minimum_stock_level of 5)
        InventoryTransaction.objects.create(
            spare_part=self.sample_part,
            transaction_type=TransactionType.ISSUE,
            quantity=16,
            reference='WO-LOW-STOCK',
            performed_by=self.admin_user,
        )
        self.sample_part.refresh_from_db()
        self.assertEqual(self.sample_part.quantity_in_stock, 4)
        self.assertEqual(self.sample_part.status, StockStatus.LOW_STOCK)


class SparePartAPITests(BaseInventoryTestCase):
    """
    Tests for SparePart REST API endpoints: CRUD, search, filter, pagination, and permissions.
    """
    def test_unauthenticated_request_rejected(self):
        self.unauth()
        response = self.client.get('/api/inventory/parts/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_create_spare_part(self):
        self.auth_as(self.admin_token)
        payload = {
            'part_number': 'PN-ENG-TURBO-01',
            'name': 'Turbine Blade Assembly',
            'description': 'Stage 1 high-pressure turbine blade.',
            'category': 'ENGINE',
            'manufacturer': 'GE Aviation',
            'quantity_in_stock': 12,
            'minimum_stock_level': 4,
            'unit_price': '8500.00',
            'location': 'Warehouse-A / Shelf-02',
            'supplier': 'Global Aero Parts',
        }
        response = self.client.post('/api/inventory/parts/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['part_number'], 'PN-ENG-TURBO-01')
        self.assertEqual(response.data['status'], 'IN_STOCK')

    def test_safety_officer_can_create_spare_part(self):
        self.auth_as(self.safety_token)
        payload = {
            'part_number': 'PN-SAFE-EXT-01',
            'name': 'Halon Fire Extinguisher Bottle',
            'category': 'CABIN',
            'manufacturer': 'Kidde Aerospace',
            'quantity_in_stock': 8,
            'minimum_stock_level': 2,
            'unit_price': '650.00',
            'location': 'Hangar Safety Cage',
        }
        response = self.client.post('/api/inventory/parts/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_contracts_manager_cannot_create_spare_part(self):
        self.auth_as(self.contracts_token)
        payload = {
            'part_number': 'PN-FAIL-CONTRACTS',
            'name': 'Forbidden Part',
            'category': 'OTHER',
            'manufacturer': 'Test Mfg',
            'quantity_in_stock': 5,
            'minimum_stock_level': 1,
            'unit_price': '100.00',
            'location': 'Bin-X',
        }
        response = self.client.post('/api/inventory/parts/', payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_field_technician_cannot_create_spare_part(self):
        self.auth_as(self.tech_token)
        payload = {
            'part_number': 'PN-FAIL-TECH',
            'name': 'Forbidden Part',
            'category': 'OTHER',
            'manufacturer': 'Test Mfg',
            'quantity_in_stock': 5,
            'minimum_stock_level': 1,
            'unit_price': '100.00',
            'location': 'Bin-X',
        }
        response = self.client.post('/api/inventory/parts/', payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_spare_part(self):
        self.auth_as(self.admin_token)
        payload = {'location': 'Hangar-3 / Bay-C10', 'unit_price': '175.00'}
        response = self.client.patch(f'/api/inventory/parts/{self.sample_part.id}/', payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sample_part.refresh_from_db()
        self.assertEqual(self.sample_part.location, 'Hangar-3 / Bay-C10')
        self.assertEqual(self.sample_part.unit_price, Decimal('175.00'))

    def test_safety_officer_can_update_spare_part(self):
        self.auth_as(self.safety_token)
        payload = {'description': 'Updated safety specifications'}
        response = self.client.patch(f'/api/inventory/parts/{self.sample_part.id}/', payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_contracts_manager_cannot_update_spare_part(self):
        self.auth_as(self.contracts_token)
        response = self.client.patch(f'/api/inventory/parts/{self.sample_part.id}/', {'name': 'New Name'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_field_technician_cannot_update_spare_part(self):
        self.auth_as(self.tech_token)
        response = self.client.patch(f'/api/inventory/parts/{self.sample_part.id}/', {'name': 'New Name'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_spare_part(self):
        self.auth_as(self.admin_token)
        part = SparePart.objects.create(
            part_number='PN-DELETE-ME',
            name='Part to Delete',
            category=PartCategory.OTHER,
            manufacturer='Test Mfg',
            quantity_in_stock=1,
            minimum_stock_level=0,
            unit_price=Decimal('10.00'),
            location='Bin-Del',
        )
        response = self.client.delete(f'/api/inventory/parts/{part.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SparePart.objects.filter(id=part.id).exists())

    def test_safety_officer_cannot_delete_spare_part(self):
        self.auth_as(self.safety_token)
        response = self.client.delete(f'/api/inventory/parts/{self.sample_part.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_contracts_manager_can_list_and_retrieve(self):
        self.auth_as(self.contracts_token)
        list_resp = self.client.get('/api/inventory/parts/')
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)

        detail_resp = self.client.get(f'/api/inventory/parts/{self.sample_part.id}/')
        self.assertEqual(detail_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_resp.data['part_number'], self.sample_part.part_number)

    def test_field_technician_can_list_and_retrieve(self):
        self.auth_as(self.tech_token)
        list_resp = self.client.get('/api/inventory/parts/')
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)

        detail_resp = self.client.get(f'/api/inventory/parts/{self.sample_part.id}/')
        self.assertEqual(detail_resp.status_code, status.HTTP_200_OK)

    def test_create_part_negative_quantity_rejected_by_api(self):
        self.auth_as(self.admin_token)
        payload = {
            'part_number': 'PN-NEG-QTY-API',
            'name': 'Negative Quantity Part',
            'category': 'HARDWARE',
            'manufacturer': 'Fastener Corp',
            'quantity_in_stock': -10,
            'minimum_stock_level': 5,
            'unit_price': '2.50',
            'location': 'Bin-Neg',
        }
        response = self.client.post('/api/inventory/parts/', payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('quantity_in_stock', response.data)

    def test_create_part_negative_price_rejected_by_api(self):
        self.auth_as(self.admin_token)
        payload = {
            'part_number': 'PN-NEG-PRICE-API',
            'name': 'Negative Price Part',
            'category': 'HARDWARE',
            'manufacturer': 'Fastener Corp',
            'quantity_in_stock': 10,
            'minimum_stock_level': 5,
            'unit_price': '-25.00',
            'location': 'Bin-Price',
        }
        response = self.client.post('/api/inventory/parts/', payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('unit_price', response.data)

    def test_create_duplicate_part_number_rejected_by_api(self):
        self.auth_as(self.admin_token)
        payload = {
            'part_number': self.sample_part.part_number.lower(),  # test uppercase normalization check
            'name': 'Duplicate Test Part',
            'category': 'HYDRAULICS',
            'manufacturer': 'Parker',
            'quantity_in_stock': 5,
            'minimum_stock_level': 2,
            'unit_price': '100.00',
            'location': 'Bin-Dup',
        }
        response = self.client.post('/api/inventory/parts/', payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('part_number', response.data)

    def test_search_spare_parts(self):
        self.auth_as(self.admin_token)
        SparePart.objects.create(
            part_number='PN-AV-SEARCH-99',
            name='Weather Radar Antenna Array',
            category=PartCategory.AVIONICS,
            manufacturer='Honeywell Aerospace',
            quantity_in_stock=3,
            minimum_stock_level=1,
            unit_price=Decimal('18000.00'),
            location='Avionics Hangar Bay',
        )
        response = self.client.get('/api/inventory/parts/?search=Radar')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertTrue(any(p['part_number'] == 'PN-AV-SEARCH-99' for p in results))

    def test_filter_by_status(self):
        self.auth_as(self.admin_token)
        response = self.client.get('/api/inventory/parts/?status=IN_STOCK')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        for part in results:
            self.assertEqual(part['status'], 'IN_STOCK')

    def test_filter_by_category(self):
        self.auth_as(self.admin_token)
        response = self.client.get(f'/api/inventory/parts/?category={PartCategory.HYDRAULICS}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        for part in results:
            self.assertEqual(part['category'], PartCategory.HYDRAULICS)

    def test_filter_by_low_stock(self):
        self.auth_as(self.admin_token)
        low_part = SparePart.objects.create(
            part_number='PN-LOW-FILTER-01',
            name='O-Ring Seal Ring',
            category=PartCategory.HARDWARE,
            manufacturer='Standard Aero',
            quantity_in_stock=2,
            minimum_stock_level=10,
            unit_price=Decimal('5.00'),
            location='Bin-OR1',
        )
        response = self.client.get('/api/inventory/parts/?low_stock=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        part_numbers = [p['part_number'] for p in results]
        self.assertIn(low_part.part_number, part_numbers)

    def test_pagination_format(self):
        self.auth_as(self.admin_token)
        response = self.client.get('/api/inventory/parts/?page=1&page_size=5')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)


class InventoryTransactionAPITests(BaseInventoryTestCase):
    """
    Tests for InventoryTransaction REST API endpoints: receipts, issues, adjustments, returns, validation, and permissions.
    """
    def test_unauthenticated_transaction_rejected(self):
        self.unauth()
        response = self.client.get('/api/inventory/transactions/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_create_receipt_transaction(self):
        self.auth_as(self.admin_token)
        initial_stock = self.sample_part.quantity_in_stock  # 20
        payload = {
            'spare_part': self.sample_part.id,
            'transaction_type': 'RECEIPT',
            'quantity': 10,
            'reference': 'PO-RECEIPT-01',
            'notes': 'Received batch from supplier.',
        }
        response = self.client.post('/api/inventory/transactions/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.sample_part.refresh_from_db()
        self.assertEqual(self.sample_part.quantity_in_stock, initial_stock + 10)
        self.assertEqual(response.data['performed_by_username'], self.admin_user.username)

    def test_admin_can_create_issue_transaction(self):
        self.auth_as(self.admin_token)
        initial_stock = self.sample_part.quantity_in_stock  # 20
        payload = {
            'spare_part': self.sample_part.id,
            'transaction_type': 'ISSUE',
            'quantity': 5,
            'reference': 'WO-ISSUE-01',
            'notes': 'Issued for A-Check work order.',
        }
        response = self.client.post('/api/inventory/transactions/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.sample_part.refresh_from_db()
        self.assertEqual(self.sample_part.quantity_in_stock, initial_stock - 5)

    def test_admin_can_create_return_transaction(self):
        self.auth_as(self.admin_token)
        initial_stock = self.sample_part.quantity_in_stock  # 20
        payload = {
            'spare_part': self.sample_part.id,
            'transaction_type': 'RETURN',
            'quantity': 2,
            'reference': 'WO-RETURN-01',
            'notes': 'Unused parts returned from hangar.',
        }
        response = self.client.post('/api/inventory/transactions/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.sample_part.refresh_from_db()
        self.assertEqual(self.sample_part.quantity_in_stock, initial_stock + 2)

    def test_admin_can_create_adjustment_transaction(self):
        self.auth_as(self.admin_token)
        payload = {
            'spare_part': self.sample_part.id,
            'transaction_type': 'ADJUSTMENT',
            'quantity': 45,
            'reference': 'AUDIT-ADJ-01',
            'notes': 'Physical count reconciliation.',
        }
        response = self.client.post('/api/inventory/transactions/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.sample_part.refresh_from_db()
        self.assertEqual(self.sample_part.quantity_in_stock, 45)

    def test_safety_officer_can_create_transaction(self):
        self.auth_as(self.safety_token)
        payload = {
            'spare_part': self.sample_part.id,
            'transaction_type': 'RECEIPT',
            'quantity': 5,
            'reference': 'SAFETY-INSPECT-01',
        }
        response = self.client.post('/api/inventory/transactions/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['performed_by_username'], self.safety_user.username)

    def test_contracts_manager_cannot_create_transaction(self):
        self.auth_as(self.contracts_token)
        payload = {
            'spare_part': self.sample_part.id,
            'transaction_type': 'RECEIPT',
            'quantity': 5,
            'reference': 'PO-CONTRACTS',
        }
        response = self.client.post('/api/inventory/transactions/', payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_field_technician_cannot_create_transaction(self):
        self.auth_as(self.tech_token)
        payload = {
            'spare_part': self.sample_part.id,
            'transaction_type': 'ISSUE',
            'quantity': 1,
            'reference': 'TECH-ISSUE',
        }
        response = self.client.post('/api/inventory/transactions/', payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_issue_exceeding_stock_rejected_by_api(self):
        self.auth_as(self.admin_token)
        current_stock = self.sample_part.quantity_in_stock  # 20
        payload = {
            'spare_part': self.sample_part.id,
            'transaction_type': 'ISSUE',
            'quantity': current_stock + 10,  # 30 > 20
            'reference': 'WO-EXCEED-API',
        }
        response = self.client.post('/api/inventory/transactions/', payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('quantity', response.data)
        # Ensure stock was not altered
        self.sample_part.refresh_from_db()
        self.assertEqual(self.sample_part.quantity_in_stock, current_stock)

    def test_zero_or_negative_quantity_transaction_rejected_by_api(self):
        self.auth_as(self.admin_token)
        payload = {
            'spare_part': self.sample_part.id,
            'transaction_type': 'RECEIPT',
            'quantity': 0,
            'reference': 'INVALID-QTY',
        }
        response = self.client.post('/api/inventory/transactions/', payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('quantity', response.data)

    def test_filter_transactions_by_spare_part(self):
        self.auth_as(self.admin_token)
        # Create a transaction for sample_part
        InventoryTransaction.objects.create(
            spare_part=self.sample_part,
            transaction_type=TransactionType.RECEIPT,
            quantity=10,
            reference='TX-FILTER-PART',
            performed_by=self.admin_user,
        )
        response = self.client.get(f'/api/inventory/transactions/?spare_part={self.sample_part.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertTrue(len(results) >= 1)
        self.assertEqual(results[0]['spare_part'], self.sample_part.id)

    def test_filter_transactions_by_type(self):
        self.auth_as(self.admin_token)
        InventoryTransaction.objects.create(
            spare_part=self.sample_part,
            transaction_type=TransactionType.RETURN,
            quantity=1,
            reference='TX-FILTER-TYPE',
            performed_by=self.admin_user,
        )
        response = self.client.get('/api/inventory/transactions/?transaction_type=RETURN')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        for tx in results:
            self.assertEqual(tx['transaction_type'], 'RETURN')

    def test_admin_can_delete_transaction(self):
        self.auth_as(self.admin_token)
        tx = InventoryTransaction.objects.create(
            spare_part=self.sample_part,
            transaction_type=TransactionType.RECEIPT,
            quantity=5,
            reference='TX-TO-DELETE',
            performed_by=self.admin_user,
        )
        response = self.client.delete(f'/api/inventory/transactions/{tx.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_safety_officer_cannot_delete_transaction(self):
        self.auth_as(self.safety_token)
        tx = InventoryTransaction.objects.create(
            spare_part=self.sample_part,
            transaction_type=TransactionType.RECEIPT,
            quantity=5,
            reference='TX-SAFETY-NODELETE',
            performed_by=self.safety_user,
        )
        response = self.client.delete(f'/api/inventory/transactions/{tx.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
